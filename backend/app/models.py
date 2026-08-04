import datetime
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    avatar = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    games = relationship("Game", back_populates="user")
    saved_positions = relationship("SavedPosition", back_populates="user")

class Game(Base):
    __tablename__ = "games"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=True)
    white_player = Column(String, default="White")
    black_player = Column(String, default="Black")
    event = Column(String, nullable=True)
    result = Column(String, default="*")
    opening = Column(String, nullable=True)
    eco = Column(String, nullable=True)
    pgn = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="games")
    analyses = relationship("Analysis", back_populates="game", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    engine_depth = Column(Integer, default=15)
    white_accuracy = Column(Float, nullable=True)
    black_accuracy = Column(Float, nullable=True)
    average_centipawn_loss = Column(Float, nullable=True)
    overall_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    game = relationship("Game", back_populates="analyses")
    moves = relationship("MoveAnalysis", back_populates="analysis", cascade="all, delete-orphan")

class MoveAnalysis(Base):
    __tablename__ = "moves"
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    move_number = Column(Integer, nullable=False)
    san = Column(String, nullable=False)
    uci = Column(String, nullable=False)
    fen = Column(String, nullable=False)
    evaluation_before = Column(String, nullable=True)
    evaluation_after = Column(String, nullable=True)
    best_move = Column(String, nullable=True)
    principal_variation = Column(JSON, nullable=True)
    move_quality = Column(String, nullable=True)
    tactics_detected = Column(JSON, nullable=True)  # Saved from engine rules
    ai_explanation = Column(Text, nullable=True)      # Populated on-demand (lazy-loaded)

    analysis = relationship("Analysis", back_populates="moves")

class SavedPosition(Base):
    __tablename__ = "saved_positions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fen = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="saved_positions")
