#!/usr/bin/env python3
"""
Test script to verify threefold repetition detection
"""

import chess
from textual_chess.chess import BetterBoard

def test_threefold_repetition():
    """Test that threefold repetition is detected correctly."""
    board = BetterBoard()
    
    # Create a simple threefold repetition scenario
    # Move knights back and forth between the same squares
    moves = [
        "b1c3", "b8c6",  # Nc3 Nc6
        "c3b1", "c6b8",  # Nb1 Nb8
        "b1c3", "b8c6",  # Nc3 Nc6 (first repetition)
        "c3b1", "c6b8",  # Nb1 Nb8 (second repetition)
        "b1c3", "b8c6",  # Nc3 Nc6 (third repetition - should trigger draw)
    ]
    
    print("Testing threefold repetition detection...")
    print(f"Initial position: {board.fen()}")
    
    for i, move_uci in enumerate(moves):
        move = chess.Move.from_uci(move_uci)
        board.push(move)
        print(f"Move {i+1}: {board.san(move)} - FEN: {board.fen()}")
        
        # Check for threefold repetition
        if board.can_claim_threefold_repetition():
            print(f"✓ Threefold repetition detected after move {i+1}!")
            break
        else:
            print(f"  No threefold repetition yet")
    
    print(f"\nFinal game state:")
    print(f"Game over: {board.is_game_over()}")
    print(f"Can claim draw: {board.can_claim_draw()}")
    print(f"Outcome: {board.outcome()}")

def test_game_outcomes():
    """Test various game ending conditions."""
    print("\n" + "="*50)
    print("Testing game outcome detection...")
    
    # Test checkmate
    board = BetterBoard("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    print(f"Starting position: {board.fen()}")
    
    # Fool's mate
    moves = ["f2f3", "e7e6", "g2g4", "d8h4"]
    for move_uci in moves:
        move = chess.Move.from_uci(move_uci)
        board.push(move)
        print(f"Move: {board.san(move)}")
        
        if board.is_checkmate():
            print("✓ Checkmate detected!")
            break
        elif board.is_stalemate():
            print("✓ Stalemate detected!")
            break
        elif board.is_insufficient_material():
            print("✓ Insufficient material detected!")
            break
        elif board.can_claim_threefold_repetition():
            print("✓ Threefold repetition detected!")
            break
        elif board.can_claim_fifty_moves():
            print("✓ Fifty-move rule detected!")
            break

if __name__ == "__main__":
    test_threefold_repetition()
    test_game_outcomes() 