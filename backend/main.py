import random
import string
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

try:
    from backend import models
    from backend.database import engine, SessionLocal, Base
    from backend.schemas import UserCreate, RoomCreate, RoomJoin, MoveCreate
    from backend.chess_engine import ChessEngine
    from backend.connection_manager import ConnectionManager
except ImportError:
    import models
    from database import engine, SessionLocal, Base
    from schemas import UserCreate, RoomCreate, RoomJoin, MoveCreate
    from chess_engine import ChessEngine
    from connection_manager import ConnectionManager


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Distributed Chess Game")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_room_code():
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def clean_name(name: str):
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Player name is required")
    return name.strip()


@app.get("/api/health")
def health():
    return {"message": "Distributed Chess Game Backend Running"}


@app.post("/api/users")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    username = clean_name(data.username)

    user = db.query(models.User).filter(models.User.username == username).first()

    if user:
        return {
            "message": "Player already exists",
            "username": username
        }

    user = models.User(username=username)
    db.add(user)
    db.commit()

    return {
        "message": "Player created successfully",
        "username": username
    }


@app.post("/api/rooms/create")
async def create_room(data: RoomCreate, db: Session = Depends(get_db)):
    username = clean_name(data.username)

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        user = models.User(username=username)
        db.add(user)
        db.commit()

    room_code = generate_room_code()

    while db.query(models.Game).filter(models.Game.room_code == room_code).first():
        room_code = generate_room_code()

    chess_game = ChessEngine()

    game = models.Game(
        room_code=room_code,
        white_player=username,
        black_player=None,
        status="waiting",
        fen=chess_game.board.fen(),
        winner=None
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    return {
        "message": "Room created successfully",
        "room_code": game.room_code,
        "player_color": "white",
        "fen": game.fen,
        "status": game.status
    }


@app.post("/api/rooms/join")
async def join_room(data: RoomJoin, db: Session = Depends(get_db)):
    username = clean_name(data.username)
    room_code = data.room_code.strip().upper()

    if not room_code:
        raise HTTPException(status_code=400, detail="Room code is required")

    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Room not found. First create a room.")

    if game.white_player == username:
        return {
            "message": "Reconnected as white player",
            "room_code": room_code,
            "player_color": "white",
            "fen": game.fen,
            "status": game.status
        }

    if game.black_player == username:
        return {
            "message": "Reconnected as black player",
            "room_code": room_code,
            "player_color": "black",
            "fen": game.fen,
            "status": game.status
        }

    if game.black_player is not None:
        raise HTTPException(status_code=400, detail="Room already has two players")

    game.black_player = username
    game.status = "running"

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        db.add(models.User(username=username))

    db.commit()
    db.refresh(game)

    await manager.broadcast(room_code, {
        "type": "player_joined",
        "message": f"{username} joined the room",
        "status": game.status
    })

    return {
        "message": "Room joined successfully",
        "room_code": room_code,
        "player_color": "black",
        "fen": game.fen,
        "status": game.status
    }


@app.post("/api/move")
async def make_move(data: MoveCreate, db: Session = Depends(get_db)):
    username = clean_name(data.username)
    room_code = data.room_code.strip().upper()
    move_uci = data.move.strip().lower()

    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()

    if not game:
        raise HTTPException(status_code=404, detail="Game room not found")

    if game.status != "running":
        raise HTTPException(status_code=400, detail="Game has not started yet")

    engine = ChessEngine(game.fen)

    current_turn = "white" if engine.board.turn else "black"

    if current_turn == "white" and username != game.white_player:
        raise HTTPException(status_code=400, detail="White player's turn")

    if current_turn == "black" and username != game.black_player:
        raise HTTPException(status_code=400, detail="Black player's turn")

    result = engine.play_move(move_uci)

    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["message"])

    game.fen = result["fen"]

    if result["checkmate"]:
        game.status = "finished"
        game.winner = username

    elif result["stalemate"]:
        game.status = "draw"
        game.winner = "draw"

    db.add(models.Move(
        room_code=room_code,
        player=username,
        move_uci=move_uci,
        fen=result["fen"]
    ))

    db.commit()

    response = {
        "type": "move",
        "room_code": room_code,
        "player": username,
        "move": move_uci,
        "fen": result["fen"],
        "turn": result["turn"],
        "check": result["check"],
        "checkmate": result["checkmate"],
        "stalemate": result["stalemate"],
        "status": game.status,
        "winner": game.winner
    }

    await manager.broadcast(room_code, response)

    return response


@app.get("/api/rooms/{room_code}")
def get_room(room_code: str, db: Session = Depends(get_db)):
    game = db.query(models.Game).filter(
        models.Game.room_code == room_code.upper()
    ).first()

    if not game:
        raise HTTPException(status_code=404, detail="Room not found")

    return {
        "room_code": game.room_code,
        "white_player": game.white_player,
        "black_player": game.black_player,
        "status": game.status,
        "fen": game.fen,
        "winner": game.winner
    }


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    room_code = room_code.upper()
    await manager.connect(room_code, websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")