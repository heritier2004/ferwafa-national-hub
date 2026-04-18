from sqlalchemy.orm import Session
from backend.app.database.additional_models import LiveSession
import uuid

class LiveSessionManager:
    @staticmethod
    def create_session(db: Session, match_id: int):
        # Generate internal system link
        session_id = str(uuid.uuid4())[:8]
        link = f"/live/match/{match_id}?session={session_id}"
        
        session = LiveSession(
            match_id=match_id,
            live_link=link,
            status="ACTIVE",
            websocket_endpoint=f"ws/match/{match_id}"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session(db: Session, match_id: int):
        return db.query(LiveSession).filter(LiveSession.match_id == match_id).first()
