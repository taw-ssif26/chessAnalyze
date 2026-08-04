from pydantic import BaseModel, Field
from typing import List, Optional

class ImportPGNRequest(BaseModel):
    pgn: str

class ImportFENRequest(BaseModel):
    fen: str

class SavePositionRequest(BaseModel):
    fen: str
    notes: Optional[str] = None

class MoveAnalysisSchema(BaseModel):
    move_number: int
    san: str
    uci: str
    fen: str
    evaluation_before: str
    evaluation_after: str
    best_move: str
    principal_variation: List[str]
    move_quality: str
    ai_explanation: Optional[str] = None

class AnalysisResponseSchema(BaseModel):
    id: int
    game_id: int
    engine_depth: int
    white_accuracy: Optional[float] = None
    black_accuracy: Optional[float] = None
    moves: List[MoveAnalysisSchema]
