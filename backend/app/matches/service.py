from sqlalchemy.orm import Session
from backend.app.matches.models import Match

class MatchService:
    @staticmethod
    def get_matches(db: Session, status: str = None):
        query = db.query(Match)
        if status:
            query = query.filter(Match.status == status)
        return query.all()

    @staticmethod
    def create_match(db: Session, match_data: dict):
        new_match = Match(**match_data)
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        return new_match

    @staticmethod
    def update_score(db: Session, match_id: int, score_home: int, score_away: int):
        match = db.query(Match).filter(Match.id == match_id).first()
        if match:
            match.score_home = score_home
            match.score_away = score_away
            db.commit()
            db.refresh(match)
        return match
