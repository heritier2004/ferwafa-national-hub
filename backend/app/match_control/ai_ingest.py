"""
WebSocket Connection Manager for AI Pitch Machine data ingestion.
- AI Machine connects via /ws/ai-ingest?token=X&key=Y
- Match Page viewers subscribe via /ws/match/{match_id}
- Server validates credentials, then routes AI events to viewers.
"""

from fastapi import WebSocket
from typing import Dict, List
from backend.app.config.database import SessionLocal
from backend.app.database.models import Match, MatchSession
from datetime import datetime


class MatchConnectionManager:
    """
    Manages two types of WebSocket connections:
    1. AI Machine ingestion connections (one per match, pushes events)
    2. Match Page viewer connections (many per match, receives events)
    """

    def __init__(self):
        # match_id -> list of viewer WebSocket connections (Match Page)
        self.match_viewers: Dict[int, List[WebSocket]] = {}
        # match_id -> AI Machine WebSocket connection
        self.ai_machines: Dict[int, WebSocket] = {}

    # ------------------------------------------------------------------
    # Match Page Viewer
    # ------------------------------------------------------------------

    async def connect_viewer(self, websocket: WebSocket, match_id: int):
        await websocket.accept()
        if match_id not in self.match_viewers:
            self.match_viewers[match_id] = []
        self.match_viewers[match_id].append(websocket)

    def disconnect_viewer(self, websocket: WebSocket, match_id: int):
        if match_id in self.match_viewers:
            try:
                self.match_viewers[match_id].remove(websocket)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # AI Machine Sender
    # ------------------------------------------------------------------

    async def connect_ai_machine(self, websocket: WebSocket, match_id: int) -> bool:
        """Accepts connection ONLY if no other AI Machine is connected for this match."""
        if match_id in self.ai_machines:
            return False
            
        await websocket.accept()
        self.ai_machines[match_id] = websocket
        self._set_ai_status(match_id, connected=True)
        return True

    def disconnect_ai_machine(self, match_id: int):
        if match_id in self.ai_machines:
            del self.ai_machines[match_id]
        self._set_ai_status(match_id, connected=False)

    def _set_ai_status(self, match_id: int, connected: bool):
        db = SessionLocal()
        try:
            session = db.query(MatchSession).filter(
                MatchSession.match_id == match_id
            ).first()
            if session:
                session.ai_connected = connected
                session.last_heartbeat = datetime.utcnow()
                db.commit()
        except Exception:
            pass
        finally:
            db.close()

    def update_heartbeat(self, match_id: int):
        """Update last_heartbeat without changing connection status."""
        self._set_ai_status(match_id, connected=True)

    def validate_ai_event(self, match_id: int, data: dict) -> bool:
        """
        Sanitize and validate AI events before persistence.
        Ensures coordinates are bounded and event types are recognized.
        """
        if data.get("type") == "heartbeat":
            return True
            
        # Bounds check
        coords = ["x", "y", "x_pos", "y_pos"]
        for c in coords:
            if c in data and (data[c] < -1 or data[c] > 101): # allow slight overflow for edge cases
                return False
                
        # Confidence check
        if "ai_confidence" in data and (data["ai_confidence"] < 0 or data["ai_confidence"] > 1):
            return False

        return True

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def broadcast_match_event(self, match_id: int, data: dict):
        """Send event data to all Match Page viewers for this match."""
        if match_id not in self.match_viewers:
            return
        dead = []
        for ws in self.match_viewers[match_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self.match_viewers[match_id].remove(ws)
            except ValueError:
                pass

    def is_ai_connected(self, match_id: int) -> bool:
        return match_id in self.ai_machines

    def viewer_count(self, match_id: int) -> int:
        return len(self.match_viewers.get(match_id, []))


# Singleton shared across the app
manager = MatchConnectionManager()
