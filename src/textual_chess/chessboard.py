import asyncio
from collections import Counter
import string
import typing

import chess

from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive, var
from textual.timer import Timer
from textual.widgets import Static

from textual_chess.bot import Bot
from textual_chess.constants import (
    BLACK_PIECE_COLOR,
    CURSOR_BORDER_COLOR,
    DARK_SQUARE_COLOR,
    HIGHLIGHT_COLOR,
    HIGHLIGHT_COLOR_OUTLINE,
    KING_CHECK_COLOR,
    LIGHT_SQUARE_COLOR,
    PIECE_SYMBOLS,
    WHITE_PIECE_COLOR,
)


class MoveMade(Message):
    def __init__(self, board: chess.Board, move: chess.Move):
        super().__init__()
        self.board = board
        self.move = move

        # default value, changed to True by ChessBoard#on_move_made
        self.game_over = False

class CaptureMade(MoveMade):
    def __init__(self, board: chess.Board, move: chess.Move, capture: chess.Piece):
        super().__init__(board, move)
        self.capture = capture


class TookBack(Message):
    def __init__(self, board: chess.Board, move: chess.Move, capture: chess.Piece | None = None):
        super().__init__()
        self.board = board
        self.move = move
        self.capture = capture

class BoardMessage(Message):
    def __init__(self, message: str):
        super().__init__()
        self.message = message


class ChessboardMock(Static):
    def render(self) -> str:
        # Draw an empty chessboard (no pieces)
        board_lines = []
        title = " Chess TUI "
        board_width = 8 * 5
        board_lines.append("  ┌" + title.center(board_width, "─") + "┐")
        for y in range(7, -1, -1):
            line = " │"
            for x in range(8):
                bg = LIGHT_SQUARE_COLOR if (x + y) % 2 == 0 else DARK_SQUARE_COLOR
                line += f"[{bg}]     [/]"
            line += "│"
            board_lines.append(' ' + line)
            board_lines.append(str(y + 1) + line)
            board_lines.append(' ' + line)
        board_lines.append("  └" + ("─" * board_width) + "┘")
        files = ' ' * 3 + ''.join(char.center(5) for char in string.ascii_lowercase[:8])
        board_lines.append(files)
        return "\n".join(board_lines)


class ChessBoard(Static):
    can_focus = True
    cursor_x = var(0)
    cursor_y = var(7)
    selected: var[chess.Square | None] = var(None)  # The square that is currently selected
    message = var("")
    show_menu = False
    flipped = reactive(False)
    ply = var(0)

    BINDINGS = [
        Binding("a,b,c,d,e,f,g,h", "move_file", "File", show=True),
        Binding("1,2,3,4,5,6,7,8", "move_rank", "Rank", show=True),
        Binding("left,right,up,down", "move_cursor", "Move", show=True),
        Binding("enter/space", "select_move", "Select/Move", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, *args, bot: Bot | None, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self._board = chess.Board()
        self._alt_board = None
        self.bot_timer = None
        self.transpositions = Counter()
        self.game_over = False

        self.transpositions.update((self.board._transposition_key(), ))

    @property
    def board(self) -> chess.Board:
        if self.ply:
            assert self._alt_board is not None
            return self._alt_board
        else:
            return self._board
    
    @property
    def last_move(self) -> chess.Move | None:
        if self.board.move_stack:
            return self.board.peek()
        else:
            return None
    
    def validate_ply(self, ply: int) -> int:
        if ply == len(self._board.move_stack):
            return 0
        
        return ply
    
    def watch_ply(self, ply: int):
        if ply == 0:
            self._alt_board = None
            self.selected = None
            self.refresh()
            return

        try:
            should_recopy = ply > len(self._alt_board.move_stack)  # type: ignore
        except AttributeError:
            should_recopy = True

        if should_recopy:
            board = self._board.copy()
            n = len(board.move_stack) - ply
        else:
            board = self._alt_board
            assert board is not None
            n = len(board.move_stack) - ply
        
        for _ in range(n):
            board.pop()

        self._alt_board = board
        self.refresh()

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

        for y in range(7, -1, -1) if not self.flipped else range(8):
            lines = ['  │'] * 3
            lines[1] = f'{y+1} │'

            for x in range(8) if not self.flipped else range(7, -1, -1):
                square = chess.square(x, y)
                piece = self.board.piece_at(square)
                is_cursor = self.cursor_x == x and self.cursor_y == y

                # Last move highlight
                is_last_move = last_move and (
                    square == last_move.from_square or square == last_move.to_square
                )

                # Square background color
                bg = LIGHT_SQUARE_COLOR if (x + y + int(self.flipped)) % 2 == 0 else DARK_SQUARE_COLOR
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
                        f"[{color_tag}]{PIECE_SYMBOLS[piece.symbol()]}[/]"
                    )
                else:
                    symbol = " "
                
                # begin background color
                for i in range(3):
                    lines[i] += f'[{bg}]'

                # Top and bottom lines
                if is_cursor:
                    line = f"[{CURSOR_BORDER_COLOR}]+---+[/]"
                elif show_outline:
                    line = f"[{HIGHLIGHT_COLOR_OUTLINE}]+---+[/]"
                else:
                    line = ' ' * 5
                
                lines[0] += line
                lines[2] += line
                dot = "[b]·[/]"
                outline = f"[{HIGHLIGHT_COLOR_OUTLINE}]|[/]"
                cursor = f"[{CURSOR_BORDER_COLOR}]|[/]"

                # Middle line
                if is_cursor:
                    lines[1] += f"{cursor} {symbol if not show_dot else dot} {cursor}"
                elif show_dot:
                    lines[1] += f"  {dot}  "
                elif show_outline:
                    lines[1] += f"{outline} {symbol} {outline}"
                else:
                    lines[1] += f"  {symbol}  "
                
                # end background color
                for i in range(3):
                    lines[i] += '[/]'

            for line in lines:
                board_lines.append(line + '│')

        # Bottom border
        board_lines.append("  └" + ("─" * board_width) + "┘")

        # Add file letters at the bottom
        # When the board is flipped, the file letters are reversed
        files = string.ascii_lowercase[:8]
        loop = reversed if self.flipped else lambda x: x
        board_lines.append(' ' * 3 + ''.join(char.center(5) for char in loop(files)))
        return "\n".join(board_lines)

    async def on_key(self, event: events.Key) -> None:
        # File keys a-h
        if event.key in "abcdefgh":
            self.cursor_x = ord(event.key) - ord("a")

        # Rank keys 1-8
        elif event.key in "12345678":
            # Ranks are 1 (bottom) to 8 (top), y=0 is bottom, y=7 is top
            self.cursor_y = int(event.key) - 1
        
        # Fixes the up and down keys when the board is flipped
        if self.flipped:
            key = {
                'left': 'right',
                'right': 'left',
                'up': 'down',
                'down': 'up',
            }.get(event.key, event.key)
        else:
            key = event.key

        if key == "left":
            self.cursor_x = max(0, self.cursor_x - 1)
        elif key == "right":
            self.cursor_x = min(7, self.cursor_x + 1)
        elif key == "up":
            self.cursor_y = min(7, self.cursor_y + 1)
        elif key == "down":
            self.cursor_y = max(0, self.cursor_y - 1)
        
        elif event.key == "enter" or event.key == "space":
            await self.handle_square_selection()

        self.refresh()

    async def handle_square_selection(self):
        if self.game_over:
            return
        
        if self.ply:
            return

        square = chess.square(self.cursor_x, self.cursor_y)
        if self.selected is None:
            piece = self.board.piece_at(square)
            if piece and (
                self.bot and piece.color == self.board.turn == chess.WHITE
                or not self.bot and piece.color == self.board.turn
            ):
                self.selected = square
                self.post_message(BoardMessage(f"Selected {chess.square_name(square)}"))
            else:
                self.post_message(BoardMessage("Select your own piece."))
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
                    capture = self.get_capture(move)
                    self.post_message(CaptureMade(self.board, move, capture))
                else:
                    self.post_message(MoveMade(self.board, move))
                self.board.push(move)
                self.selected = None
                self.post_message(BoardMessage(""))

                if self.bot:
                    callback = lambda: self.run_worker(self.bot_move)
                    self.bot_timer = self.set_timer(1, callback)
            else:
                piece = self.board.piece_at(square)
                if piece and piece.color == self.board.turn:
                    self.selected = square
                    self.post_message(BoardMessage(f"Selected {chess.square_name(square)}"))
                else:
                    self.post_message(BoardMessage(
                        f"Invalid move: {chess.square_name(self.selected)} to {chess.square_name(square)}.")
                    )
                    self.selected = None
        
        if self.board.is_checkmate():
            self.post_message(BoardMessage("Checkmate!"))
        elif self.board.is_stalemate():
            self.post_message(BoardMessage("Stalemate!"))
        elif self.board.is_check():
            self.post_message(BoardMessage("Check!"))

        self.refresh()

    async def bot_move(self):
        if self.game_over:
            return

        if self.bot is None:
            return
        
        # Adresses the issue where the player can press back button
        # too quickly before the bot plays the move
        if self.ply:
            self.ply = 0
            await self.app.action_bell()

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
                self.post_message(BoardMessage(f"Bot played {self.board.san(move)}"))
                if self.board.is_capture(move):
                    capture = self.board.piece_at(move.to_square)
                    if capture:
                        self.post_message(CaptureMade(self.board, move, capture))
                else:
                    self.post_message(MoveMade(self.board, move))
                self.board.push(move)
            else:
                self.post_message(BoardMessage("Bot attempted illegal move."))
        
        # refresh is mandatory here
        self.refresh()

    def on_move_made(self, message: MoveMade):
        move = self.board.pop()
        if self.board.is_irreversible(move):
            self.transpositions.clear()
            claim_draw = False
        else:
            key = self.board._transposition_key()
            self.transpositions.update((key, ))
            claim_draw = self.transpositions.get(key, 0) >= 3
            # self.notify(f"Transposition: {key}")
        
        self.board.push(move)
        self.check_outcome(claim_draw=claim_draw)
        
        if self.game_over:
            message.game_over = True
            if claim_draw:
                self.notify("A draw was made")
    
    def on_capture_made(self, message: CaptureMade):
        self.transpositions.clear()
        self.check_outcome()
    
    def check_outcome(self, *, claim_draw: bool = False):
        outcome = self.board.outcome(claim_draw=claim_draw)
        if outcome:
            self.game_over = True
            self.post_message(BoardMessage(f"{outcome.result()}"))

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
        
        if self.flipped:
            board_x = 7 - board_x
            board_y = 7 - board_y

        self.cursor_x = board_x
        self.cursor_y = board_y
        await self.handle_square_selection()
        self.refresh()

    def flip_board(self) -> None:
        self.flipped = not self.flipped
        # No need to flip the actual board, just the UI
        # https://stackoverflow.com/questions/65661613/how-to-flip-a-chessboard-while-preserving-the-move-stack-in-python-chess
        # chess.BaseBoard.apply_transform(self.board, chess.flip_vertical)
        # chess.BaseBoard.apply_transform(self.board, chess.flip_horizontal)

    def get_capture(self, move: chess.Move) -> chess.Piece:
        capture = self.board.piece_at(move.to_square)
        if not capture:
            # En passant capture
            if self.board.turn == chess.WHITE:
                capture = self.board.piece_at(move.to_square - 8)
            else:
                capture = self.board.piece_at(move.to_square + 8)
        
        if not capture:
            raise ValueError("No capture was found")
        return capture

    def _takeback(self):
        move = self.board.pop()
        self.transpositions[self.board._transposition_key()] -= 1
        if self.board.is_capture(move):
            self.post_message(TookBack(self.board.copy(), move, self.get_capture(move)))
        else:
            self.post_message(TookBack(self.board.copy(), move))
        
        return move

    def takeback(self) -> bool:
        if self.game_over or self.board.is_game_over():
            self.app.notify("Cannot take back. Game is over", severity="error")
            return False

        if self.ply:
            self.ply = 0

        if self.board.turn == chess.WHITE:
            # Could be the first move
            if not self.board.move_stack:
                self.app.notify("No moves to take back", severity="error")
                return False
            
            # takes back black last move and continues to take back another move
            move = self._takeback()

            # When the bot is disabled, take back only one move at a time
            if not self.bot:
                self.selected = None
                self.post_message(BoardMessage(f"Took back {self.board.san(move)}"))
                self.refresh()
                return True
        elif self.bot:
            # ISSUE: If the player played a move then took it back so quickly
            # before the bot reacts could confuse the bot and so is the UI

            timer = typing.cast(Timer, self.bot_timer)
            timer.stop()
            self.bot_timer = None
        
        if self.board.turn == chess.BLACK:
            # If it is black's turn, there is at least one move in the stack
            move = self._takeback()
            
            self.selected = None
            self.post_message(BoardMessage(f"Took back {self.board.san(move)}"))
        
        self.refresh()
        return True
    
    def claim_draw(self) -> bool:
        if self.board.can_claim_draw():
            self.notify("Draw claimed")
            return True
        else:
            self.notify("Draw not claimed", severity="warning")
            return False
