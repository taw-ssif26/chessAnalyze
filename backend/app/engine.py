import os
import shutil
import chess
import chess.engine
from typing import Dict, Any, List, Tuple

class StockfishManager:
    def __init__(self):
        # Fallbacks to handle typical OS installations
        self.executable_path = shutil.which("stockfish") or "/usr/games/stockfish" or "/usr/bin/stockfish"
        if not os.path.exists(self.executable_path):
            raise FileNotFoundError(f"Stockfish executable not found at paths. Check installation.")

    def analyze_position(self, fen: str, depth: int = 15) -> Dict[str, Any]:
        """Runs Stockfish engine evaluation on a given FEN string."""
        board = chess.Board(fen)
        
        # Guard clause for terminal positions
        if board.is_game_over():
            result = board.result()
            return {
                "evaluation": "Mate" if "#" in result else "0.0",
                "best_move": "None",
                "pv": [],
                "score_raw": 0,
                "is_mate": False
            }

        with chess.engine.SimpleEngine.popen_uci(self.executable_path) as engine:
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            
            score = info["score"].relative
            is_mate = score.is_mate()
            
            if is_mate:
                eval_str = f"M{score.mate()}"
                score_raw = 10000 if score.mate() > 0 else -10000
            else:
                score_val = score.score() / 100.0  # Convert centipawns to normal units
                eval_str = f"{'+' if score_val > 0 else ''}{score_val:.2f}"
                score_raw = score.score()

            # Retrieve principal variation
            pv_moves = []
            if "pv" in info:
                # Get up to 4 moves of principal variation
                pv_moves = [board.san(move) for move in info["pv"][:4]]

            best_move = info["pv"][0].uci() if "pv" in info else "None"

            return {
                "evaluation": eval_str,
                "best_move": best_move,
                "pv": pv_moves,
                "score_raw": score_raw,
                "is_mate": is_mate
            }

    @staticmethod
    def classify_move(score_before: float, score_after: float, is_mate_before: bool, is_mate_after: bool) -> str:
        """Classifies the quality of a move using Centipawn Loss (CPL)."""
        # Perspective is relative to active side
        # A positive difference means evaluation got worse for the player moving
        diff = score_before - score_after
        
        if is_mate_before and not is_mate_after:
            return "Blunder"  # Let go of forced checkmate
        
        if diff >= 2.0:
            return "Blunder"
        elif diff >= 1.0:
            return "Mistake"
        elif diff >= 0.5:
            return "Inaccuracy"
        elif diff >= 0.1:
            return "Good"
        elif diff >= -0.1:
            return "Excellent"
        else:
            return "Brilliant"

    @staticmethod
    def detect_tactics(board_before: chess.Board, move: chess.Move) -> List[str]:
        """Performs simple, robust heuristics to identify tactical features of a move."""
        tactics = []
        board = board_before.copy()
        
        # Check if the square was occupied (Capture)
        if board.is_capture(move):
            tactics.append("Capture")
            
        board.push(move)
        
        if board.is_check():
            tactics.append("Check")
            
        # Detect basic forks (piece attacking multiple valuable targets)
        # Evaluated post-move
        valuable_pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        attacks = board.attacks(move.to_square)
        target_count = 0
        for sq in attacks:
            piece = board.piece_at(sq)
            if piece and piece.color != board.turn and piece.piece_type in valuable_pieces:
                target_count += 1
        if target_count >= 2:
            tactics.append("Fork Opportunity")
            
        return tactics
