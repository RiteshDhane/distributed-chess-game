from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func

try:
    from backend.database import Base
except ImportError:
    from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(20), unique=True, nullable=False)
    white_player = Column(String(100), nullable=True)
    black_player = Column(String(100), nullable=True)
    status = Column(String(30), default="waiting")
    fen = Column(Text, nullable=False)
    winner = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Move(Base):
    __tablename__ = "moves"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String(20), nullable=False)
    player = Column(String(100), nullable=False)
    move_uci = Column(String(20), nullable=False)
    fen = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())