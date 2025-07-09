from operator import truediv
import chess

from rich.console import Console
import rich.repr
from rich.segment import Segment
from rich.style import Style
from rich.text import Text

from textual import on
from textual.app import ComposeResult
from textual.containers import (
    Grid,
    Horizontal,
    HorizontalGroup,
    ScrollableContainer,
    Vertical,
    VerticalScroll,
)
from textual.events import Key
from textual.geometry import Size
from textual.message import Message
from textual.reactive import Reactive, reactive, var
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widgets import Footer, Header, Static

from textual_chess.bot import get_bot_by_type
from textual_chess.chessboard import (
    BoardMessage,
    CaptureMade,
    ChessBoard,
    MoveMade,
    TookBack,
)
from textual_chess.chessplayer import ChessPlayer
from textual_chess.dialog import ChessOptionsDialog, ChessOptions
from textual_chess.utils import strip_text


class MovesList(ScrollView):
    game_over = var(False)
    ply = var(0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.virtual_size = Size(20, 1)
        self.moves_list = []

    def render_line(self, y: int) -> Strip:
        _, scroll_y = self.scroll_offset
        
        y += scroll_y
        n = y // 2 + 1
        
        if y % 2:
            return Strip.blank(cell_length=20)
        
        moves = self.moves_list
        m1, m2 = '', ''
        
        try:
            m1, m2 = moves[y], moves[y+1]
        except IndexError:
            if y+1 == len(moves):
                m1 = moves[y]
                m2 = ".." if not self.game_over else ""
            elif y == len(moves):
                m1 = ".." if not self.game_over else ""
                m2 = ""
        
        if m1 or m2:
            return self.make_strip(n, m1, m2)
        else:
            return Strip.blank(cell_length=20)
    
    def make_strip(self, n: int, m1: str, m2: str) -> Strip:
        return strip_text(''.join([
            f"{n:>2}. ",
            self.make_link(m1, 2 * n - 1),
            ' ',
            self.make_link(m2, 2 * n),
        ]))
    
    def make_link(self, move: str, ply: int) -> str:
        if move == '..':
            return f"[dim]{move.ljust(7)}[/]"
        if not move:
            return ' ' * 7

        if ply == self.ply:
            tag = "[bold underline]"
            endtag = ''
        elif self.ply == 0 and ply == len(self.moves_list):
            tag = "[bold]"
            endtag = ''
        else:
            # Make a clickable link
            tag = f"[dim][@click=click({ply})]"
            endtag = "[/]"
        
        move = move.ljust(8).replace(' ', '[/]', 1)
        return tag + move + endtag
    
    def action_click(self, ply: int):
        self.ply = ply
        self.post_message(self.Click(self.moves_list[ply - 1], ply, self.game_over))
        self.refresh()
    
    def validate_ply(self, ply: int) -> int:
        if ply == len(self.moves_list):
            return 0
        
        return ply

    def update_moves(self, board: chess.Board, game_over: bool):
        moves = list(board.move_stack)
        san_moves = []
        temp_board = chess.Board()
        for move in moves:
            san_moves.append(temp_board.san_and_push(move))
        
        self.game_over = game_over
        self.moves_list = san_moves
        self.virtual_size = Size(20, len(san_moves) + 2 & ~1)
        self.scroll_end(animate=False)
        self.ply = 0
        self.refresh()
    
    @rich.repr.auto
    class Click(Message):
        def __init__(self, move: str, ply: int, game_over: bool):
            super().__init__()
            self.move = move
            self.ply = ply
            self.game_over = game_over
        
        def __rich_repr__(self):
            yield "move", self.move
            yield "ply", self.ply
            yield "game_over", self.game_over


class InfoPanel(Static):
    def __init__(self, white_player: 'ChessPlayer', black_player: 'ChessPlayer', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.white_player = white_player
        self.black_player = black_player

    def compose(self) -> ComposeResult:
        yield self.black_player
        self.moves_list = MovesList()
        yield self.moves_list
        yield self.white_player

    def update_moves(self, board: chess.Board, game_over: bool = False):
        self.moves_list.update_moves(board, game_over)


class MessageBox(Static):
    message = reactive("Placeholder")

    def render(self) -> str:
        return f"[blink]{self.message}[/]"


class ChessScreen(Screen):
    message = reactive("Placeholder for messages", always_update=True)

    BINDINGS = [
        ("f1", "show_options", "Options"),
    ]

    def __init__(self, bot_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot_type = bot_type
        self.bot = get_bot_by_type(bot_type)

        if self.bot:
            black_player = self.bot.as_player('black')
        else:
            black_player = ChessPlayer(name="Opponent", color="black", is_bot=False)
        white_player = ChessPlayer(name="You", color="white", is_bot=False)

        self.info_panel = InfoPanel(
            white_player=white_player,
            black_player=black_player,
        )
        self.chessboard = ChessBoard(bot=self.bot)
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(classes="chess-container"):
            yield self.chessboard
            yield self.info_panel
            yield MessageBox(classes="span2 center-content message").data_bind(self.__class__.message)  # type: ignore
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ChessBoard).focus()

    async def on_move_made(self, message: MoveMade):
        self.info_panel.update_moves(message.board, message.game_over)

    async def on_capture_made(self, message: CaptureMade):
        capture = message.capture
        self.adjust_material_advantage(capture)
        await self.on_move_made(message)
    
    async def on_took_back(self, message: TookBack):
        self.info_panel.update_moves(message.board)
        if message.board.is_capture(message.move):
            assert message.capture is not None
            self.adjust_material_advantage(message.capture, took_back=True)
    
    def adjust_material_advantage(self, capture: chess.Piece, *, took_back: bool = False):
        black_player = self.info_panel.black_player
        white_player = self.info_panel.white_player
        material_values = {
            'p': 1,
            'n': 3,
            'b': 3,
            'r': 5,
            'q': 9,
        }
        material_value = material_values.get(capture.symbol().lower(), 0)
        
        # material counter is biased towards white meaning that
        # -3 is an advantage for black and +3 is an advantage for white
        if capture.color == chess.WHITE:
            material_value *= -1
            capturing_player = black_player
        else:
            capturing_player = white_player
        
        symbol = capture.unicode_symbol(invert_color=not capture.color)

        if not took_back:
            white_player.advantage += material_value
            black_player.advantage -= material_value
            capturing_player.material += symbol
        else:
            white_player.advantage -= material_value
            black_player.advantage += material_value
            capturing_player.material = capturing_player.material.replace(symbol, '', 1)
    

    def on_board_message(self, message: BoardMessage):
        self.message = message.message
    
    # When the user presses F1, show the options dialog
    def action_show_options(self) -> None:
        self.app.push_screen(ChessOptionsDialog(), callback=self.check_option)

    def check_option(self, option: ChessOptions | None):
        if option is None:
            return
        
        if option == ChessOptions.CopyFEN:
            self.app.copy_to_clipboard(self.chessboard.board.fen())
            self.app.notify("FEN copied to clipboard")
        
        if option == ChessOptions.Return:
            self.app.pop_screen()
        
        if option == ChessOptions.FlipBoard:
            self.chessboard.flip_board()
        
        if option == ChessOptions.Takeback:
            self.chessboard.takeback()
        
        if option == ChessOptions.Draw:
            if self.chessboard.claim_draw():
                pass
        
        if option == ChessOptions.Resign:
            pass
    
    @on(MovesList.Click)
    def navigate_to_move(self, message: MovesList.Click):
        self.chessboard.ply = message.ply