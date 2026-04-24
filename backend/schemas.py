from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str


class RoomCreate(BaseModel):
    username: str


class RoomJoin(BaseModel):
    username: str
    room_code: str


class MoveCreate(BaseModel):
    username: str
    room_code: str
    move: str