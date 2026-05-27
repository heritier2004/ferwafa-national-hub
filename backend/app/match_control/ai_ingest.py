import json
import hmac
import hashlib
from fastapi import WebSocket
from typing import Dict, List
from backend.app.config.database import SessionLocal
from backend.app.database.models import Match, MatchSession
from datetime import datetime
from backend.app.live.intelligence import IntelligenceService

class MatchConnectionManager:
    def __init__(self):
        self.match_viewers: Dict[int, List[WebSocket]] = {}
        self.ai_machines: Dict[int, WebSocket] = {}

    async def connect_viewer(self, websocket: WebSocket, match_id: int):
        await websocket.accept()
        if match_id not in self.match_viewers:
            self.match_viewers[match_id] = []
        self.match_viewers[match_id].append(websocket)

    def disconnect_viewer(self, websocket: WebSocket, match_id: int):
        if match_id in self.match_viewers:
            try: self.match_viewers[match_id].remove(websocket)
            except ValueError: pass

    async def connect_ai_machine(self, websocket: WebSocket, match_id: int) -> bool:
        if match_id in self.ai_machines: return False
        await websocket.accept()
        self.ai_machines[match_id] = websocket
        self._set_ai_status(match_id, connected=True)
        return True

    def disconnect_ai_machine(self, match_id: int):
        if match_id in self.ai_machines: del self.ai_machines[match_id]
        self._set_ai_status(match_id, connected=False)

    def _set_ai_status(self, match_id: int, connected: bool):
        db = SessionLocal()
        try:
            session = db.query(MatchSession).filter(MatchSession.match_id == match_id).first()
            if session:
                session.ai_connected = connected
                if not connected:
                    session.status = "INACTIVE"
                session.last_heartbeat = datetime.utcnow()
                db.commit()
        except Exception: pass
        finally: db.close()

    async def handle_secure_message(self, match_id: int, data: dict):
        """
        Validates HMAC signature and processes payload through IntelligenceService.
        """
        db = SessionLocal()
        try:
            match = db.query(Match).filter(Match.id == match_id).first()
            if not match: return

            # 1. VERIFY SIGNATURE
            sig = data.get("signature")
            payload = data.get("payload")
            if not sig or not payload:
                raise ValueError("Signature or payload missing")

            if not match.api_key:
                raise ValueError("Match has no registered API Key for signing verification")

            msg_string = json.dumps(payload, sort_keys=True)
            expected_sig = hmac.new(
                match.api_key.encode(),
                msg_string.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(sig, expected_sig):
                raise ValueError("HMAC signature verification failed")
            
            # 2. PROCESS PAYLOAD
            msg_type = payload.get("type")
            
            if msg_type == "tracking_update":
                for frame in payload.get("frames", []):
                    IntelligenceService.process_tracking_frame(db, match_id, frame)
            
            elif msg_type == "match_event":
                event = IntelligenceService.process_ai_event(db, match_id, payload)
                payload["is_confirmed"] = event.is_confirmed
                payload["event_id"] = event.id

            elif msg_type == "tactical_update":
                IntelligenceService.update_tactical_state(db, match_id, payload)

            # 3. BROADCAST TO VIEWERS
            payload["match_id"] = match_id
            payload["server_time"] = datetime.utcnow().isoformat()
            await self.broadcast_match_event(match_id, payload)

        except Exception as e:
            print(f"[AI_INGEST_ERROR] {e}")
        finally:
            db.close()

    async def broadcast_match_event(self, match_id: int, data: dict):
        if match_id not in self.match_viewers: return
        dead = []
        for ws in self.match_viewers[match_id]:
            try: await ws.send_json(data)
            except Exception: dead.append(ws)
        for ws in dead:
            try: self.match_viewers[match_id].remove(ws)
            except ValueError: pass

manager = MatchConnectionManager()
