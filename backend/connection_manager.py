from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.rooms = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()

        if room_code not in self.rooms:
            self.rooms[room_code] = []

        self.rooms[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.rooms:
            if websocket in self.rooms[room_code]:
                self.rooms[room_code].remove(websocket)

    async def broadcast(self, room_code: str, message: dict):
        if room_code not in self.rooms:
            return

        for connection in self.rooms[room_code]:
            await connection.send_json(message)