import chess
import random
from chessplayer import ChessPlayer
import re
from minimax import minimax


def get_bot_by_type(bot_type: str) -> 'Bot':
    if bot_type == 'random':
        return RandomBot()
    elif bot_type == 'greedy':
        return GreedyBot()
    elif bot_type == 'minimax':
        return MinimaxBot(depth=2)
    else:
        raise ValueError(f"Invalid bot type: {bot_type}")


class Bot:
    def choose_move(self, board: chess.Board) -> chess.Move | None:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__
    
    @property
    def bot_type(self):
        match = re.fullmatch(r'(.*?)(Bot)?$', self.name, re.I)
        if match:
            return match.group(1).lower()
        return self.name  # fallback if regex fails

    def as_player(self, color: str) -> 'ChessPlayer':
        return ChessPlayer(name=self.name, color=color, is_bot=True, bot_type=self.bot_type)


class RandomBot(Bot):
    def choose_move(self, board: chess.Board) -> chess.Move | None:
        moves = list(board.legal_moves)
        if not moves:
            return None
        return random.choice(moves)


class GreedyBot(Bot):
    PIECE_VALUES = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }

    def choose_move(self, board: chess.Board) -> chess.Move | None:
        best_value = -1
        best_moves = []
        moves = list(board.legal_moves)
        for move in moves:
            if board.is_capture(move):
                captured = board.piece_at(move.to_square)
                if captured:
                    value = self.PIECE_VALUES.get(captured.piece_type, 0)
                    if value > best_value:
                        best_value = value
                        best_moves = [move]
                    elif value == best_value:
                        best_moves.append(move)
        if best_moves:
            return random.choice(best_moves)
        if moves:
            return random.choice(moves)
        return None


class MinimaxBot(Bot):
    def __init__(self, depth=2):
        self.depth = depth

    def choose_move(self, board: chess.Board) -> chess.Move | None:
        _, move = minimax(board, self.depth, -float('inf'), float('inf'), board.turn == chess.WHITE)
        if move is None:
            moves = list(board.legal_moves)
            return random.choice(moves) if moves else None
        return move
