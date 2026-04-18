from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.matches.service import MatchService

router = APIRouter(prefix="/matches", tags=["matches"])

@router.get("/")
def list_matches(status: str = None, db: Session = Depends(get_db)):
    return MatchService.get_matches(db, status)

@router.patch("/{match_id}/score")
def update_match_score(match_id: int, score_home: int, score_away: int, db: Session = Depends(get_db)):
    return MatchService.update_score(db, match_id, score_home, score_away)
