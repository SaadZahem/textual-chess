import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# fmt: off
PAWN_TABLE = [
#    a   b   c   d    e    f   g   h
     0,  5,  5, -10, -10,  5,  5,  0,   # 8th rank
     0, 10, -5,  0,   0,  -5, 10,  0,   # 7th rank
     0, 10, 10, 20,  20,  10, 10,  0,   # 6th rank
     5, 20, 20, 30,  30,  20, 20,  5,   # 5th rank
    10, 20, 20, 30,  30,  20, 20, 10,   # 4th rank
    50, 50, 50, 50,  50,  50, 50, 50,   # 3rd rank
    90, 90, 90, 90,  90,  90, 90, 90,   # 2nd rank
     0,  0,  0,  0,   0,   0,  0,  0,   # 1st rank
]
# fmt: on


def evaluate_board(board: chess.Board) -> int:
    value = 0
    for square, piece in board.piece_map().items():
        piece_value = PIECE_VALUES[piece.piece_type]
        if piece.piece_type == chess.PAWN:
            table = PAWN_TABLE
            idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
            piece_value += table[idx]
        value += piece_value if piece.color == chess.WHITE else -piece_value
    return value


def minimax(
    board: chess.Board, depth: int, alpha: float, beta: float, maximizing: bool
) -> tuple[float, chess.Move | None]:
    """
    Minimax algorithm with alpha-beta pruning.
    Returns the best move and its evaluation.
    """
    if depth == 0 or board.is_game_over():
        return evaluate_board(board), None
    best_move = None
    if maximizing:
        max_eval = -float("inf")
        for move in board.legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float("inf")
        for move in board.legal_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move
