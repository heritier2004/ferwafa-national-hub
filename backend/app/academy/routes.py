from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import Attendance, Player, Match, AIAnalysis, Institution, PlayerStat
from sqlalchemy import func
from datetime import datetime, date
from pydantic import BaseModel
from typing import List

from backend.app.auth.dependencies import get_current_user, RoleChecker

router = APIRouter(
    prefix="/api/academy", 
    tags=["academy"],
    dependencies=[Depends(RoleChecker(["ACADEMY", "FERWAFA"]))]
)

@router.get("/stats/{inst_id}")
def get_academy_stats(inst_id: int, db: Session = Depends(get_db)):
    # 1. Elite Prospects (Talent Score > 85)
    elite_count = db.query(Player).filter(
        Player.institution_id == inst_id,
        Player.talent_score >= 85
    ).count()

    # 2. National Call-ups (Mock for demo, or based on is_elite_prospect)
    national_prospects = db.query(Player).filter(
        Player.institution_id == inst_id,
        Player.is_elite_prospect == True
    ).count()

    # 3. Development Trend
    # Get average rating of players in the academy
    avg_rating = db.query(func.avg(PlayerStat.rating)).join(Player).filter(
        Player.institution_id == inst_id
    ).scalar() or 7.2

    return {
        "elite_prospects": f"{elite_count} Elite Talents Identified",
        "national_prospects": f"{national_prospects} Players on National Radar",
        "avg_performance": f"System Average: {round(avg_rating, 1)} / 10.0"
    }

@router.get("/players/{inst_id}")
def get_academy_players(inst_id: int, db: Session = Depends(get_db)):
    players = db.query(Player).filter(Player.institution_id == inst_id).all()
    return [{
        "id": p.id,
        "name": p.name,
        "position": p.position,
        "player_code": p.player_code,
        "photo_url": p.photo_url,
        "talent_score": p.talent_score,
        "is_elite": p.is_elite_prospect
    } for p in players]

@router.get("/talent-identification/{inst_id}")
def get_talent_id(inst_id: int, db: Session = Depends(get_db)):
    # Get top performers based on metrics
    top_players = db.query(Player).filter(
        Player.institution_id == inst_id
    ).order_by(Player.talent_score.desc()).limit(5).all()
    
    return [{
        "name": p.name,
        "score": p.talent_score,
        "position": p.position,
        "photo": p.photo_url
    } for p in top_players]
