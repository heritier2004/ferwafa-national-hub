import json
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
from sqlalchemy.orm import Session
from backend.app.config.database import SessionLocal
from backend.app.live.intelligence import IntelligenceService

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

    async def handle_ai_data(self, match_id: int, data: dict):
        """
        Processes incoming data from AI Machine and broadcasts to UI.
        """
        db = SessionLocal()
        try:
            msg_type = data.get("type")
            
            if msg_type == "tracking_update":
                # Process tracking frames
                for frame in data.get("frames", []):
                    IntelligenceService.process_tracking_frame(db, match_id, frame)
                # Broadcast tracking to dashboard
                await self.broadcast(match_id, data)

            elif msg_type == "match_event":
                # Process events
                event = IntelligenceService.process_ai_event(db, match_id, data)
                # Broadcast event (confirmed or pending)
                data["event_id"] = event.id
                data["is_confirmed"] = event.is_confirmed
                await self.broadcast(match_id, data)

            elif msg_type == "tactical_update":
                # Process tactical snapshots
                IntelligenceService.generate_tactical_snapshot(db, match_id, data)
                await self.broadcast(match_id, data)

        except Exception as e:
            print(f"WebSocket Data Error: {e}")
        finally:
            db.close()

    async def broadcast(self, match_id: int, message: dict):
        if match_id in self.active_connections:
            for connection in self.active_connections[match_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()
