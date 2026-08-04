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
from app.llm import LLMExplainer
llm_explainer = LLMExplainer()

@app.post("/api/import-pgn")
def import_pgn(payload: ImportPGNRequest, db: Session = Depends(get_db)):
    pgn_io = io.StringIO(payload.pgn)
    parsed_game = chess.pgn.read_game(pgn_io)
    
    if not parsed_game:
        raise HTTPException(status_code=400, detail="Invalid PGN format.")

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
    
    # 1. Warm evaluation of starting state
    current_eval_data = engine_manager.analyze_position(board.fen(), depth=12)

    for move in parsed_game.mainline_moves():
        fen_before = board.fen()
        eval_before_data = current_eval_data # Evaluate from position *before* move occurs
        
        san_move = board.san(move)
        played_moves_san.append(san_move)
        
        # Determine opening label
        opening_name, eco_code = detect_opening(played_moves_san)
        if opening_name != "Custom Setup":
            game_record.opening = opening_name
            game_record.eco = eco_code

        # 2. Make transition
        board.push(move)
        fen_after = board.fen()
        
        # 3. Analyze the new position (after move)
        eval_after_data = engine_manager.analyze_position(fen_after, depth=12)
        current_eval_data = eval_after_data # Shift state for next iteration
        
        # Parse tactics & verify metrics
        board_before_temp = chess.Board(fen_before)
        tactics = engine_manager.detect_tactics(board_before_temp, move)
        
        quality = engine_manager.classify_move(
            board_before_temp, 
            move, 
            eval_before_data["pov_score"], 
            eval_after_data["pov_score"]
        )

        # Force book moves for standard theory transitions
        if len(played_moves_san) <= 8 and opening_name != "Custom Setup":
            if quality in ["Best", "Excellent", "Good"]:
                quality = "Book"

        # Safe conversion of best move coordinates to readable SAN string
        best_move_san = "None"
        if eval_before_data["best_move"] != "None":
            try:
                best_move_san = board_before_temp.san(chess.Move.from_uci(eval_before_data["best_move"]))
            except Exception:
                best_move_san = eval_before_data["best_move"]

        # Run AI Explainer
        payload_llm = {
            "played_move": san_move,
            "best_move": best_move_san,
            "evaluation_before": eval_before_data["evaluation"],
            "evaluation_after": eval_after_data["evaluation"],
            "classification": quality,
            "principal_variation": eval_before_data["pv"],
            "position": fen_before,
            "tactics_detected": tactics,
            "is_forced": quality == "Forced"
        }
        
        ai_text = llm_explainer.explain_move(payload_llm)

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
