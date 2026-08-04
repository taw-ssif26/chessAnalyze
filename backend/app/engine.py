import os
import shutil
import chess
import chess.engine
from typing import Dict, Any, List, Tuple

# Simple Opening Theory DB for matching early book moves
OPENING_THEORY_SAN = {
    "e4 e5": ("King's Pawn Game", "C20"),
    "e4 c5": ("Sicilian Defense", "B20"),
    "e4 e6": ("French Defense", "C00"),
    "e4 c6": ("Caro-Kann Defense", "B10"),
    "e4 d6": ("Pirc Defense", "B07"),
    "e4 Nf6": ("Alekhine's Defense", "B02"),
    "e4 g6": ("Modern Defense", "B06"),
    "d4 d5": ("Queen's Pawn Game", "D00"),
    "d4 Nf6": ("Indian Defense", "A45"),
    "d4 f5": ("Dutch Defense", "A80"),
    "Nf3 d5": ("Reti Opening", "A09"),
    "c4 e5": ("English Opening", "A20"),
    "c4 c5": ("English Opening, Symmetrical", "A30"),
    "e4 e5 Nf3 Nc6 Bb5": ("Ruy Lopez", "C60"),
    "e4 e5 Nf3 Nc6 Bc4": ("Italian Game", "C50"),
    "e4 e5 Nf3 Nc6 d4": ("Scotch Game", "C44"),
    "d4 Nf6 c4 e6 Nf3 d5": ("Queen's Gambit Declined", "D30"),
    "d4 Nf6 c4 g6 Nc3 Bg7": ("King's Indian Defense", "E61"),
    "d4 d5 c4 e6": ("Queen's Gambit Declined", "D30"),
    "d4 d5 c4 c6": ("Slav Defense", "D10"),
    "d4 d5 c4 dxc4": ("Queen's Gambit Accepted", "D20"),
}

def detect_opening(moves_san: List[str]) -> Tuple[str, str]:
    """Matches the early game moves sequence against standard openings."""
    for length in range(min(len(moves_san), 6), 0, -1):
        sub_seq = " ".join(moves_san[:length])
        if sub_seq in OPENING_THEORY_SAN:
            return OPENING_THEORY_SAN[sub_seq]
    return ("Custom Setup", "A00")

class StockfishManager:
    def __init__(self):
        self.executable_path = shutil.which("stockfish") or "/usr/games/stockfish" or "/usr/bin/stockfish"
        if not os.path.exists(self.executable_path):
            raise FileNotFoundError("Stockfish executable not found. Verify your system path installation.")

    def analyze_position(self, fen: str, depth: int = 15) -> Dict[str, Any]:
        """Runs evaluation and parses score using absolute metrics."""
        board = chess.Board(fen)
        if board.is_game_over():
            result = board.result()
            return {
                "evaluation": "Mate" if "#" in result else "0.0",
                "best_move": "None",
                "pv": [],
                "score_raw": 0,
                "is_mate": False,
                "pov_score": None
            }

        with chess.engine.SimpleEngine.popen_uci(self.executable_path) as engine:
            engine.configure({"Hash": 16, "Threads": 1})
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            
            score = info["score"]
            is_mate = score.is_mate()
            
            # Normalize to White's POV for standard database storage
            score_white = score.white()
            if is_mate:
                mate_val = score_white.mate()
                eval_str = f"M{mate_val}"
                score_raw = (10000 - abs(mate_val)) if mate_val > 0 else (-10000 + abs(mate_val))
            else:
                score_val = score_white.score() / 100.0
                eval_str = f"{'+' if score_val > 0 else ''}{score_val:.2f}"
                score_raw = score_white.score()

            pv_moves = []
            if "pv" in info:
                pv_moves = [board.san(move) for move in info["pv"][:4]]

            best_move = info["pv"][0].uci() if "pv" in info else "None"

            return {
                "evaluation": eval_str,
                "best_move": best_move,
                "pv": pv_moves,
                "score_raw": score_raw,
                "is_mate": is_mate,
                "pov_score": score
            }

    @staticmethod
    def get_score_for_color(pov_score: chess.engine.PovScore, color: chess.Color) -> float:
        """Converts PovScore to a standard float relative to the active player's side."""
        score_color = pov_score.white() if color == chess.WHITE else pov_score.black()
        if score_color.is_mate():
            mate_moves = score_color.mate()
            if mate_moves > 0:
                return 10000.0 - mate_moves
            else:
                return -10000.0 + abs(mate_moves)
        else:
            return float(score_color.score(default=0))

    def classify_move(
        self, 
        board_before: chess.Board, 
        move: chess.Move, 
        score_before_pov: chess.engine.PovScore, 
        score_after_pov: chess.engine.PovScore
    ) -> str:
        """Classifies move quality using absolute Centipawn Loss (CPL) and forced rules."""
        if board_before.legal_moves.count() == 1:
            return "Forced"

        moving_color = board_before.turn
        before_score = self.get_score_for_color(score_before_pov, moving_color)
        after_score = self.get_score_for_color(score_after_pov, moving_color)

        # CPL reflects the drop in evaluation for the side making the move
        cpl = before_score - after_score

        # Check for sacrifice patterns (potential Brilliant move)
        is_sac = False
        if board_before.is_capture(move):
            captured_piece = board_before.piece_at(move.to_square)
            moved_piece = board_before.piece_at(move.from_square)
            if captured_piece and moved_piece and moved_piece.piece_type > captured_piece.piece_type:
                is_sac = True

        if cpl <= 0 and is_sac:
            return "Brilliant"
        elif cpl <= 10:
            return "Best"
        elif cpl <= 35:
            return "Excellent"
        elif cpl <= 60:
            return "Good"
        elif cpl <= 150:
            return "Inaccuracy"
        elif cpl <= 300:
            return "Mistake"
        else:
            return "Blunder"

    @staticmethod
    def detect_tactics(board_before: chess.Board, move: chess.Move) -> List[str]:
        """Heuristic-based scanning of the position to find active tactical patterns."""
        tactics = []
        board = board_before.copy()
        moving_color = board.turn
        opponent_color = not moving_color
        
        if board.is_capture(move):
            tactics.append("Capture")

        board.push(move)
        
        if board.is_check():
            tactics.append("Check")

        # Fork detection
        attacks = board.attacks(move.to_square)
        valuable_pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        targets = []
        for sq in attacks:
            piece = board.piece_at(sq)
            if piece and piece.color == opponent_color and piece.piece_type in valuable_pieces:
                targets.append(piece.piece_type)
        if len(targets) >= 2:
            tactics.append("Fork")

        # Pin detection
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece and piece.color == opponent_color:
                if board.is_pinned(opponent_color, sq):
                    tactics.append("Pin")
                    break

        # Hanging Piece detection
        dest_attacks = board.attacks(move.to_square)
        for sq in dest_attacks:
            p = board.piece_at(sq)
            if p and p.color == opponent_color:
                defenders = board.attackers(opponent_color, sq)
                if len(defenders) == 0:
                    tactics.append("Attacked Hanging Piece")
                    break

        return list(set(tactics))
