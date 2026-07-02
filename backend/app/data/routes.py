from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import MatchEvent, PlayerStat, Match
from typing import List
from backend.app.auth.dependencies import get_current_user

router = APIRouter(
    prefix="/api/data",
    tags=["data"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/sync-event")
def sync_event(data: dict, db: Session = Depends(get_db)):
    """Backend-to-Backend sync of events."""
    new_event = MatchEvent(**data)
    db.add(new_event)
    db.commit()
    return {"status": "synced"}

@router.post("/save-stat")
def save_stat(data: dict, db: Session = Depends(get_db)):
    """Save calculated statistics."""
    # Logic to update PlayerStat or MatchAnalytics
    return {"status": "stat_saved"}

@router.get("/match-history")
def get_match_history(db: Session = Depends(get_db)):
    return db.query(Match).all()

@router.get("/player-stats/{player_id}")
def get_player_stats(player_id: int, db: Session = Depends(get_db)):
    return db.query(PlayerStat).filter(PlayerStat.player_id == player_id).all()
