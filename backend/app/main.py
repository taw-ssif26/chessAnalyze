import chess
import chess.pgn
import io
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db, Base, engine
from app.models import Game, Analysis, MoveAnalysis, SavedPosition
from app.schemas import ImportPGNRequest, ImportFENRequest, SavePositionRequest
from app.engine import StockfishManager
from app.llm import LLMExplainer

# Auto-generate DB schemas (Simplifies deployment setup for Postgres / SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Chess Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

engine_manager = StockfishManager()
llm_explainer = LLMExplainer()

@app.post("/api/import-pgn")
def import_pgn(payload: ImportPGNRequest, db: Session = Depends(get_db)):
    """Imports PGN string, parses individual moves, runs engine evaluation, and saves to database."""
    pgn_io = io.StringIO(payload.pgn)
    parsed_game = chess.pgn.read_game(pgn_io)
    
    if not parsed_game:
        raise HTTPException(status_code=400, detail="Invalid PGN string format provided.")

    # Save initial game metadata
    game_record = Game(
        white_player=parsed_game.headers.get("White", "White"),
        black_player=parsed_game.headers.get("Black", "Black"),
        event=parsed_game.headers.get("Event", "Casual Game"),
        result=parsed_game.headers.get("Result", "*"),
        opening=parsed_game.headers.get("Opening", "Unknown"),
        eco=parsed_game.headers.get("ECO", ""),
        pgn=payload.pgn
    )
    db.add(game_record)
    db.commit()
    db.refresh(game_record)

    # Initialize analysis tracking
    analysis_record = Analysis(
        game_id=game_record.id,
        engine_depth=12,  # Set light depth to ensure fast, free-tier compliance
    )
    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)

    board = parsed_game.board()
    move_number = 1
    
    for move in parsed_game.mainline_moves():
        fen_before = board.fen()
        
        # Analyze current position prior to move
        eval_before_data = engine_manager.analyze_position(fen_before, depth=12)
        
        # Capture SAN before pushing (board.san() requires the move to be legal on current board)
        san = board.san(move)

        # Make the actual move
        board.push(move)
        fen_after = board.fen()
        
        # Analyze outcome position
        eval_after_data = engine_manager.analyze_position(fen_after, depth=12)
        
        # Convert raw scores to comparable floats for standard sizing
        s_before = float(eval_before_data["score_raw"]) / 100.0
        s_after = float(eval_after_data["score_raw"]) / 100.0
        
        # Invert evaluation logic when it is black's perspective to ensure standard alignment
        if board.turn == chess.WHITE: 
            # This calculation represents the assessment right before black played
            # (where it was White's turn to move next)
            quality = engine_manager.classify_move(
                s_before, s_after, eval_before_data["is_mate"], eval_after_data["is_mate"]
            )
        else:
            # Move was played by White
            quality = engine_manager.classify_move(
                -s_before, -s_after, eval_before_data["is_mate"], eval_after_data["is_mate"]
            )

        # Retrieve structural explanation from LLM using factual constraints
        payload_llm = {
            "played_move": move.uci(),
            "best_move": eval_before_data["best_move"],
            "evaluation_before": eval_before_data["evaluation"],
            "evaluation_after": eval_after_data["evaluation"],
            "classification": quality,
            "principal_variation": eval_before_data["pv"],
            "position": fen_before
        }
        
        ai_text = llm_explainer.explain_move(payload_llm)

        move_analysis = MoveAnalysis(
            analysis_id=analysis_record.id,
            move_number=move_number,
            san=san,
            uci=move.uci(),
            fen=fen_after,
            evaluation_before=eval_before_data["evaluation"],
            evaluation_after=eval_after_data["evaluation"],
            best_move=eval_before_data["best_move"],
            principal_variation=eval_before_data["pv"],
            move_quality=quality,
            ai_explanation=ai_text
        )
        db.add(move_analysis)
        move_number += 1
        
    db.commit()

    return {
        "game_id": game_record.id,
        "analysis_id": analysis_record.id,
        "status": "Analysis completed successfully"
    }

@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis record not found.")
        
    moves = db.query(MoveAnalysis).filter(MoveAnalysis.analysis_id == analysis_id).order_by(MoveAnalysis.id).all()
    
    return {
        "id": analysis.id,
        "game_id": analysis.game_id,
        "engine_depth": analysis.engine_depth,
        "moves": [
            {
                "move_number": m.move_number,
                "san": m.san,
                "uci": m.uci,
                "fen": m.fen,
                "evaluation_before": m.evaluation_before,
                "evaluation_after": m.evaluation_after,
                "best_move": m.best_move,
                "principal_variation": m.principal_variation,
                "move_quality": m.move_quality,
                "ai_explanation": m.ai_explanation
            }
            for m in moves
        ]
    }
