import chess
import chess.pgn
import io
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import get_db, Base, engine
from app.models import Game, Analysis, MoveAnalysis
from app.schemas import ImportPGNRequest
from app.engine import StockfishManager, detect_opening
from app.llm import LLMExplainer

Base.metadata.drop_all(bind=engine) # Optional: Wipe existing legacy schema to apply updates
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Chess Analyzer API")

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
    pgn_io = io.StringIO(payload.pgn)
    parsed_game = chess.pgn.read_game(pgn_io)
    
    if not parsed_game:
        raise HTTPException(status_code=400, detail="Invalid PGN string format.")

    game_record = Game(
        white_player=parsed_game.headers.get("White", "White"),
        black_player=parsed_game.headers.get("Black", "Black"),
        event=parsed_game.headers.get("Event", "Casual Match"),
        result=parsed_game.headers.get("Result", "*"),
        opening=parsed_game.headers.get("Opening", "Unknown"),
        eco=parsed_game.headers.get("ECO", ""),
        pgn=payload.pgn
    )
    db.add(game_record)
    db.commit()
    db.refresh(game_record)

    analysis_record = Analysis(game_id=game_record.id, engine_depth=12)
    db.add(analysis_record)
    db.commit()
    db.refresh(analysis_record)

    board = parsed_game.board()
    move_number = 1
    played_moves_san = []
    
    # Warm up initial engine position
    current_eval_data = engine_manager.analyze_position(board.fen(), depth=11)

    for move in parsed_game.mainline_moves():
        fen_before = board.fen()
        eval_before_data = current_eval_data
        
        san_move = board.san(move)
        played_moves_san.append(san_move)
        
        # Determine opening label
        opening_name, eco_code = detect_opening(played_moves_san)
        if opening_name != "Custom Setup":
            game_record.opening = opening_name
            game_record.eco = eco_code

        board.push(move)
        fen_after = board.fen()
        
        eval_after_data = engine_manager.analyze_position(fen_after, depth=11)
        current_eval_data = eval_after_data
        
        board_before_temp = chess.Board(fen_before)
        tactics = engine_manager.detect_tactics(board_before_temp, move)
        
        quality = engine_manager.classify_move(
            board_before_temp, 
            move, 
            eval_before_data["pov_score"], 
            eval_after_data["pov_score"]
        )

        if len(played_moves_san) <= 8 and opening_name != "Custom Setup":
            if quality in ["Best", "Excellent", "Good"]:
                quality = "Book"

        best_move_san = "None"
        if eval_before_data["best_move"] != "None":
            try:
                best_move_san = board_before_temp.san(chess.Move.from_uci(eval_before_data["best_move"]))
            except Exception:
                best_move_san = eval_before_data["best_move"]

        # Note: ai_explanation is intentionally left None here to ensure instant PGN imports
        move_analysis = MoveAnalysis(
            analysis_id=analysis_record.id,
            move_number=move_number,
            san=san_move,
            uci=move.uci(),
            fen=fen_after,
            evaluation_before=eval_before_data["evaluation"],
            evaluation_after=eval_after_data["evaluation"],
            best_move=best_move_san,
            principal_variation=eval_before_data["pv"],
            move_quality=quality,
            tactics_detected=tactics,
            ai_explanation=None 
        )
        db.add(move_analysis)
        move_number += 1
        
    db.commit()

    return {
        "game_id": game_record.id,
        "analysis_id": analysis_record.id,
        "status": "Game parsed and analyzed successfully"
    }

@app.post("/api/move/{move_id}/explain")
def explain_move(move_id: int, db: Session = Depends(get_db)):
    """Lazy-loaded dynamic explanation generator. Returns cached or computes on-demand."""
    move = db.query(MoveAnalysis).filter(MoveAnalysis.id == move_id).first()
    if not move:
        raise HTTPException(status_code=404, detail="Move record not found.")

    if move.ai_explanation:
        return {"explanation": move.ai_explanation}

    # Fetch position before to feed LLM
    fen_before = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    if move.move_number > 1:
        prev_move = db.query(MoveAnalysis).filter(
            MoveAnalysis.analysis_id == move.analysis_id,
            MoveAnalysis.move_number == move.move_number - 1
        ).first()
        if prev_move:
            fen_before = prev_move.fen

    payload_llm = {
        "played_move": move.san,
        "best_move": move.best_move,
        "evaluation_before": move.evaluation_before,
        "evaluation_after": move.evaluation_after,
        "classification": move.move_quality,
        "principal_variation": move.principal_variation or [],
        "position": fen_before,
        "tactics_detected": move.tactics_detected or [],
        "is_forced": move.move_quality == "Forced"
    }

    ai_text = llm_explainer.explain_move(payload_llm)
    
    # Save cache
    move.ai_explanation = ai_text
    db.commit()

    return {"explanation": ai_text}

@app.get("/api/analysis/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis record not found.")
    moves = db.query(MoveAnalysis).filter(MoveAnalysis.analysis_id == analysis_id).order_by(MoveAnalysis.id).all()
    return {
        "id": analysis.id,
        "game_id": analysis.game_id,
        "moves": [
            {
                "id": m.id,  # Essential DB key for on-demand calls
                "move_number": m.move_number,
                "san": m.san,
                "uci": m.uci,
                "fen": m.fen,
                "evaluation_before": m.evaluation_before,
                "evaluation_after": m.evaluation_after,
                "best_move": m.best_move,
                "principal_variation": m.principal_variation,
                "move_quality": m.move_quality,
                "tactics_detected": m.tactics_detected,
                "ai_explanation": m.ai_explanation
            }
            for m in moves
        ]
    }
