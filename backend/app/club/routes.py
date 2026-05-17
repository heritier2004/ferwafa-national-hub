from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.config.database import get_db
from backend.app.database.models import Player, Institution, Match, MatchSquad, PlayerStat
from backend.app.auth.dependencies import get_current_user, RoleChecker
from backend.app.utils.crud import CrudMixin, transactional

router = APIRouter(prefix="/api/club", tags=["club"])

club_access = RoleChecker(["CLUB", "FERWAFA"])

@router.post("/player/create", dependencies=[Depends(club_access)])
def create_club_player(data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    if not inst_id:
        raise HTTPException(status_code=403, detail="CLUB user not linked to institution.")

    player_payload = {
        "name": data.get("name"),
        "position": data.get("position"),
        "secondary_position": data.get("secondary_position"),
        "jersey_number": data.get("jersey_number"),
        "preferred_foot": data.get("preferred_foot"),
        "date_of_birth": data.get("date_of_birth"),
        "nationality": data.get("nationality", "Rwandan"),
        "phone_number": data.get("phone_number"),
        "height": data.get("height"),
        "weight": data.get("weight"),
        "fitness_status": data.get("fitness_status", "Fit"),
        "injury_status": data.get("injury_status", "None"),
        "medical_conditions": data.get("medical_notes"),
        "institution_id": inst_id,
        "player_code": f"CLB-{uuid.uuid4().hex[:6].upper()}"
    }
    return CrudMixin.create(Player, db, player_payload, actor_id=current_user["id"])

@router.post("/lineup/submit", dependencies=[Depends(club_access)])
def submit_lineup(match_id: int, players: List[dict], db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Official lineup submission for competitions."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Clear old lineup
    with transactional(db):
        db.query(MatchSquad).filter(MatchSquad.match_id == match_id).delete()
        
        for p in players:
            db.add(MatchSquad(
                match_id=match_id,
                player_id=p["player_id"],
                role=p["role"],
                position=p.get("position"),
                jersey_number=p.get("jersey_number")
            ))
    
    return {"status": "Lineup submitted successfully"}

@router.get("/matches", dependencies=[Depends(club_access)])
def list_club_matches(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    return db.query(Match).filter(
        (Match.home_team_id == inst_id) | (Match.away_team_id == inst_id)
    ).all()

import uuid

@router.get("/stats", dependencies=[Depends(club_access)])
def get_club_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Performance analytics aggregated for the club."""
    inst_id = current_user.get("institution_id")
    # Fetch player stats for this club
    stats = db.query(PlayerStat).join(Player).filter(Player.institution_id == inst_id).all()
    return {
        "player_stats": stats,
        "total_players": len(stats),
        "last_sync": datetime.utcnow().isoformat() if "datetime" in globals() else None
    }

@router.get("/reports", dependencies=[Depends(club_access)])
def get_club_reports(match_id: Optional[int] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Access to match reports (PDF/CSV links)."""
    inst_id = current_user.get("institution_id")
    matches = db.query(Match).filter(
        (Match.home_team_id == inst_id) | (Match.away_team_id == inst_id)
    ).all()
    
    return [
        {
            "match_id": m.id,
            "opponent": m.opponent_name,
            "date": m.match_date,
            "csv_url": f"/api/match/{m.id}/export/csv",
            "pdf_url": f"/api/match/{m.id}/export/pdf"
        } for m in matches if m.is_finalized
    ]
from datetime import datetime
