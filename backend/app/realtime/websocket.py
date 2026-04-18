from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {} # match_id -> list of websockets

    async def connect(self, websocket: WebSocket, match_id: int):
        await websocket.accept()
        if match_id not in self.active_connections:
            self.active_connections[match_id] = []
        self.active_connections[match_id].append(websocket)

    def disconnect(self, websocket: WebSocket, match_id: int):
        if match_id in self.active_connections:
            self.active_connections[match_id].remove(websocket)
            if not self.active_connections[match_id]:
                del self.active_connections[match_id]

    async def broadcast_match_event(self, match_id: int, message: dict):
        if match_id in self.active_connections:
            for connection in self.active_connections[match_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Connection closed or failed
                    pass

manager = ConnectionManager()
