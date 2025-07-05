from textual.widgets import Static
from textual.reactive import reactive
from textual import events
from textual.binding import Binding
from textual.geometry import Size
from textual.message import Message
import chess
from textual import work
import asyncio
from constants import (
    PIECE_SYMBOLS,
    LIGHT_SQUARE_COLOR,
    DARK_SQUARE_COLOR,
    WHITE_PIECE_COLOR,
    BLACK_PIECE_COLOR,
    CURSOR_BORDER_COLOR,
    HIGHLIGHT_COLOR,
    KING_CHECK_COLOR,
    HIGHLIGHT_COLOR_OUTLINE,
)
from bot import Bot
from typing import Callable


class MoveMade(Message):
    def __init__(self, board: chess.Board):
        super().__init__()
        self.board = board


class CaptureMade(MoveMade):
    def __init__(self, board: chess.Board, capture: chess.Piece):
        super().__init__(board)
        self.capture = capture


class ChessboardMock(Static):
    def render(self) -> str:
        # Draw an empty chessboard (no pieces)
        board_lines = []
        title = " Chess TUI "
        board_width = 8 * 5
        board_lines.append("  ┌" + title.center(board_width, "─") + "┐")
        for y in range(7, -1, -1):
            line1 = "  │"
            line2 = f"{y+1} │"
            line3 = "  │"
            for x in range(8):
                bg = LIGHT_SQUARE_COLOR if (x + y) % 2 == 0 else DARK_SQUARE_COLOR
                line1 += f"[ {bg} ]     [/]"
                line2 += f"[{bg}]     [/{bg}]"
                line3 += f"[{bg}]     [/{bg}]"
            line1 += "│"
            line2 += "│"
            line3 += "│"
            board_lines.append(line1)
            board_lines.append(line2)
            board_lines.append(line3)
        board_lines.append("  └" + ("─" * board_width) + "┘")
        files = "     a    b    c    d    e    f    g    h  "
        board_lines.append(files)
        return "\n".join(board_lines)


class ChessBoard(Static):
    can_focus = True
    board = reactive(chess.Board())
    cursor_x = reactive(0)
    cursor_y = reactive(7)
    selected = reactive(None)  # The square that is currently selected
    message = reactive("")
    last_move = reactive(None)  # Track the last move
    show_menu = False

    BINDINGS = [
        Binding("a,b,c,d,e,f,g,h", "move_file", "File", show=True),
        Binding("1,2,3,4,5,6,7,8", "move_rank", "Rank", show=True),
        Binding("left,right,up,down", "move_cursor", "Move", show=True),
        Binding("enter/space", "select_move", "Select/Move", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    # def on_move_made(self, callback: Callable[[chess.Board], None]):
    #     self.move_made_callback = callback

    def __init__(self, *args, bot: Bot, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_menu = False
        self.bot = bot

    def render(self) -> str:
        board_lines = []

        # Title
        title = " Chess TUI - Singleplayer vs Bot "
        board_width = 8 * 5  # 8 squares, each 5 chars wide
        board_lines.append("  ┌" + title.center(board_width, "─") + "┐")

        last_move = self.last_move
        king_in_check_square = None
        if self.board.is_check():
            king_square = self.board.king(self.board.turn)
            if king_square is not None:
                king_in_check_square = king_square

        # Collect legal moves for selected piece
        legal_moves = set()
        if self.selected is not None:
            for move in self.board.legal_moves:
                if move.from_square == self.selected:
                    legal_moves.add(move.to_square)

        for y in range(7, -1, -1):
            line1 = "  │"
            line2 = f"{y+1} │"
            line3 = "  │"

            for x in range(8):
                square = chess.square(x, y)
                piece = self.board.piece_at(square)
                is_cursor = self.cursor_x == x and self.cursor_y == y

                # Last move highlight
                is_last_move = last_move and (
                    square == last_move.from_square or square == last_move.to_square
                )

                # Square background color
                bg = LIGHT_SQUARE_COLOR if (x + y) % 2 == 0 else DARK_SQUARE_COLOR
                if king_in_check_square is not None and square == king_in_check_square:
                    bg = KING_CHECK_COLOR
                elif is_last_move:
                    bg = HIGHLIGHT_COLOR

                # Legal move indicators
                show_dot = (
                    self.selected is not None
                    and square in legal_moves
                    and piece is None
                )
                show_outline = (
                    self.selected is not None
                    and square in legal_moves
                    and piece is not None
                    and self.board.piece_at(self.selected)
                    and piece.color != self.board.piece_at(self.selected).color  # type: ignore[attr-defined]
                )

                # Piece symbol
                if piece:
                    color_tag = (
                        WHITE_PIECE_COLOR
                        if piece.color == chess.WHITE
                        else BLACK_PIECE_COLOR
                    )
                    symbol = (
                        f"[{color_tag}]{PIECE_SYMBOLS[piece.symbol()]}[/{color_tag}]"
                    )
                else:
                    symbol = " "

                # Top line
                if is_cursor:
                    line1 += f"[{CURSOR_BORDER_COLOR} {bg}]+---+[/]"
                elif show_outline:
                    line1 += f"[{HIGHLIGHT_COLOR_OUTLINE} {bg}]+---+[/]"
                else:
                    line1 += f"[ {bg} ]     [/ ]"

                # Middle line
                if is_cursor:
                    line2 += (
                        f"[{bg}][{CURSOR_BORDER_COLOR}]| [/]"
                        + (symbol if not show_dot else "[bold]·[/]")
                        + f"[{CURSOR_BORDER_COLOR}] |[/][/{bg}]"
                    )
                elif show_dot:
                    line2 += f"[{bg}]  [bold]·[/]  [/]"
                elif show_outline:
                    line2 += (
                        f"[{bg}][{HIGHLIGHT_COLOR_OUTLINE}]| [/]"
                        + symbol
                        + f"[{HIGHLIGHT_COLOR_OUTLINE}] |[/][/ ]"
                    )
                else:
                    line2 += f"[{bg}]  {symbol}  [/{bg}]"

                # Bottom line
                if is_cursor:
                    line3 += f"[{CURSOR_BORDER_COLOR} {bg}]+---+[/]"
                elif show_outline:
                    line3 += f"[{HIGHLIGHT_COLOR_OUTLINE} {bg}]+---+[/]"
                else:
                    line3 += f"[{bg}]     [/{bg}]"

            line1 += "│"
            line2 += "│"
            line3 += "│"
            board_lines.append(line1)
            board_lines.append(line2)
            board_lines.append(line3)

        # Bottom border
        board_lines.append("  └" + ("─" * board_width) + "┘")

        # Add file letters at the bottom
        files = "     a    b    c    d    e    f    g    h  "
        board_lines.append(files)

        if self.board.is_checkmate():
            board_lines.append("Checkmate!")
        elif self.board.is_stalemate():
            board_lines.append("Stalemate!")
        elif self.board.is_check():
            board_lines.append("Check!")

        board_lines.append(self.message)
        return "\n".join(board_lines)

    async def on_key(self, event: events.Key) -> None:
        if self.show_menu:
            if event.key == "r":
                self.message = "You resigned. Game over."
                self.show_menu = False
                self.refresh()
            elif event.key == "b":
                from app import HomeScreen

                self.app.mount(HomeScreen())
                self.remove()
            elif event.key == "escape":
                self.show_menu = False
                self.message = ""
                self.refresh()
            return

        if event.key == "f1":
            self.show_menu = True
            self.message = "F1 Menu: r = resign, b = back to home, esc = cancel"
            self.refresh()
            return

        # File keys a-h
        if event.key in "abcdefgh":
            self.cursor_x = ord(event.key) - ord("a")
        # Rank keys 1-8
        elif event.key in "12345678":
            # Ranks are 1 (bottom) to 8 (top), y=0 is bottom, y=7 is top
            self.cursor_y = int(event.key) - 1
        elif event.key == "left":
            self.cursor_x = max(0, self.cursor_x - 1)
        elif event.key == "right":
            self.cursor_x = min(7, self.cursor_x + 1)
        elif event.key == "up":
            self.cursor_y = min(7, self.cursor_y + 1)
        elif event.key == "down":
            self.cursor_y = max(0, self.cursor_y - 1)
        elif event.key == "enter" or event.key == "space":
            await self.handle_square_selection()

        self.refresh()

    async def handle_square_selection(self):
        if self.board.is_game_over():
            return

        square = chess.square(self.cursor_x, self.cursor_y)
        if self.selected is None:
            piece = self.board.piece_at(square)
            if piece and piece.color == self.board.turn:
                self.selected = square
                self.message = f"Selected {chess.square_name(square)}"
            else:
                self.message = "Select your own piece."
        else:
            piece = self.board.piece_at(self.selected)
            move = chess.Move(self.selected, square)
            # Handle promotion
            if piece and piece.piece_type == chess.PAWN:
                if chess.square_rank(square) == 7 and self.board.turn == chess.WHITE:
                    move = chess.Move(self.selected, square, promotion=chess.QUEEN)
                elif chess.square_rank(square) == 0 and self.board.turn == chess.BLACK:
                    move = chess.Move(self.selected, square, promotion=chess.QUEEN)
            if move in self.board.legal_moves:
                if self.board.is_capture(move):
                    capture = self.board.piece_at(move.to_square)
                    if capture:
                        self.post_message(CaptureMade(self.board, capture))
                else:
                    self.post_message(MoveMade(self.board))
                self.board.push(move)
                self.last_move = move  # Track last move
                self.selected = None
                self.message = ""
                # self.refresh()  # Show user's move immediately
                # self.app.refresh()  # Force screen refresh
                self.run_worker(self.bot_move)
            else:
                piece = self.board.piece_at(square)
                if piece and piece.color == self.board.turn:
                    self.selected = square
                    self.message = f"Selected {chess.square_name(square)}"
                else:
                    self.message = f"Invalid move: {chess.square_name(self.selected)} to {chess.square_name(square)}."
                    self.selected = None
        self.refresh()

    async def bot_move(self):
        await asyncio.sleep(1)  # 1 second delay
        if self.board.is_game_over():
            return
        
        move = self.bot.choose_move(self.board)
        if move:
            piece = self.board.piece_at(move.from_square)
            if piece and piece.piece_type == chess.PAWN:
                # Use the piece's color to determine promotion rank
                if (
                    piece.color == chess.WHITE
                    and chess.square_rank(move.to_square) == 7
                ):
                    move = chess.Move(
                        move.from_square, move.to_square, promotion=chess.QUEEN
                    )
                elif (
                    piece.color == chess.BLACK
                    and chess.square_rank(move.to_square) == 0
                ):
                    move = chess.Move(
                        move.from_square, move.to_square, promotion=chess.QUEEN
                    )
            if move in self.board.legal_moves:
                self.message = f"Bot played {self.board.san(move)}"
                if self.board.is_capture(move):
                    capture = self.board.piece_at(move.to_square)
                    if capture:
                        self.post_message(CaptureMade(self.board, capture))
                else:
                    self.post_message(MoveMade(self.board))
                self.board.push(move)
                self.last_move = move  # Track last move
            else:
                self.message = "Bot attempted illegal move."
        self.refresh()

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        # Calculate the board's top-left corner in widget coordinates
        # The board starts after the title border and left margin (2 chars)
        # The chessboard is rendered with a left margin and a border, so the top-left corner of the board
        # (in widget coordinates) is offset by 3 characters horizontally (2 for the left margin, 1 for the border)
        board_origin_x = 3  # Horizontal offset: 2 chars for margin + 1 char for border

        # Vertically, the board starts after the title and the top border, which are displayed together on one line
        # So offset by only 1 line
        board_origin_y = 1  # Vertical offset: 1 line for title+border

        # Each square on the board is rendered as 5 characters wide and 3 lines tall
        square_width = 5  # Width of each square in characters
        square_height = 3  # Height of each square in lines
        x = event.x - board_origin_x
        y = event.y - board_origin_y
        if x < 0 or y < 0:
            return
        board_x = x // square_width
        board_y = 7 - (y // square_height)
        if not (0 <= board_x < 8 and 0 <= board_y < 8):
            return
        self.cursor_x = board_x
        self.cursor_y = board_y
        await self.handle_square_selection()
        self.refresh()
