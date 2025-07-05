from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from rich.console import Console

from textual.widgets import Static, Header, Footer
from textual.containers import (
    HorizontalGroup,
    Vertical,
    ScrollableContainer,
    Horizontal,
    VerticalScroll,
    Grid,
)
from chessboard import ChessBoard, MoveMade, CaptureMade
from textual.app import ComposeResult
from textual.strip import Strip
from textual.geometry import Size
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.reactive import reactive, var, Reactive
import chess
from bot import get_bot_by_type
from chessplayer import ChessPlayer
from utils import strip_text


class MovesList(ScrollView):
    moves_list: Reactive[list[str]] = reactive(list)
    game_over = var(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.move_list = Static("", id="move-list")
        self.virtual_size = Size(20, 1)
        # self.mount(self.move_list)

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
            return strip_text(f"{n:>2}. [dim]{m1:<7} {m2:<7}[/]")
        else:
            return Strip.blank(cell_length=20)

    def update_moves(self, board: chess.Board):
        moves = list(board.move_stack)
        san_moves = []
        temp_board = chess.Board()
        for move in moves:
            san_moves.append(temp_board.san(move))
            temp_board.push(move)
        
        self.game_over = board.is_game_over()
        self.moves_list = san_moves
        self.virtual_size = Size(20, len(san_moves))
        self.scroll_end(animate=False)
        self.mutate_reactive(MovesList.moves_list)


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

    def update_moves(self, board: chess.Board):
        self.moves_list.update_moves(board)


class ChessScreen(Screen):
    material = reactive(0)
    message = reactive("")

    def __init__(self, bot_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot_type = bot_type
        self.bot = get_bot_by_type(bot_type)

        black_player = self.bot.as_player('black')
        white_player = ChessPlayer(name="You", color="white", is_bot=False)

        self.info_panel = InfoPanel(
            white_player=white_player,
            black_player=black_player,
        )
        self.chessboard = ChessBoard(bot=self.bot)
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(classes="chess-container", ):
            yield self.chessboard
            yield self.info_panel
            yield Static(f"[blink]{self.message}[/]", classes="span2 center-content")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(ChessBoard).focus()

    async def on_move_made(self, message: MoveMade):
        self.info_panel.update_moves(message.board)

    async def on_capture_made(self, message: CaptureMade):
        capture = message.capture
        color = 'white' if capture.color == chess.WHITE else 'black'
        players = self.query(ChessPlayer)
        assert len(players) == 2, "Expected 2 players"
        
        # black player was yielded first
        black_player, white_player = players
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
        
        white_player.advantage += material_value
        black_player.advantage -= material_value
        
        self.material += material_value
        
        for player in players:
            if player.color != color:
                player.material += capture.unicode_symbol(invert_color=not capture.color)
                break
        
        await self.on_move_made(message)
