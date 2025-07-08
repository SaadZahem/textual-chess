from collections import Counter
from collections.abc import Hashable

import chess


class BetterBoard(chess.Board):
    """
    Same as the superclass but implements incremental transposition counter
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transpositions: Counter[Hashable] = Counter()
    
    def push(self, move: chess.Move):
        super().push(move)
        if self.is_irreversible(move):
            self.transpositions.clear()
        
        if not self.has_legal_en_passant():
            self.transpositions.update((self._transposition_key(), ))
    
    def pop(self):
        move = super().pop()
        self.transpositions[self._transposition_key()] -= 1
        return move
    
    def can_claim_threefold_repetition(self) -> bool:
        transposition_key = self._transposition_key()
        
        # Threefold repetition occurred.
        if self.transpositions[transposition_key] >= 3:
            return True

        # The next legal move is a threefold repetition.
        for move in self.generate_legal_moves():
            super().push(move)
            try:
                if self.transpositions[self._transposition_key()] >= 2:
                    return True
            finally:
                super().pop()

        return False
    
    def outcome(self, *, claim_draw: bool = True) -> chess.Outcome | None:
        return super().outcome(claim_draw=claim_draw)
