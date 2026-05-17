from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.players.service import PlayerService
from pydantic import BaseModel
from typing import Optional

from backend.app.auth.dependencies import get_current_user, RoleChecker

router = APIRouter(
    prefix="/players", 
    tags=["players"],
    dependencies=[Depends(RoleChecker(["CLUB", "SCHOOL", "ACADEMY", "FERWAFA"]))]
)

class PlayerCreate(BaseModel):
    name: str
    position: str
    institution_id: int
    photo_url: str
    age: Optional[int] = None
    jersey_number: Optional[int] = None
    nationality: str = "Rwandan"

class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None
    age: Optional[int] = None
    jersey_number: Optional[int] = None
    nationality: Optional[str] = None

@router.get("/")
def list_players(institution_id: int = None, db: Session = Depends(get_db)):
    return PlayerService.get_all_players(db, institution_id)

@router.post("/")
def add_player(player: PlayerCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # 1. Enforce photo for School/Academy
    from backend.app.database.models import Institution
    inst = db.query(Institution).filter(Institution.id == player.institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
        
    if inst.type in ["school", "academy"] and not player.photo_url:
        raise HTTPException(status_code=400, detail="Photo is REQUIRED for School and Academy registrations.")

    # 2. Inherit Location from Institution
    location_data = {
        "location_id": inst.code,
        "region": inst.province,
        "district": inst.district
    }

    code = PlayerService.generate_player_code(db, player.institution_id)
    return PlayerService.create_player(db, {
        **player.dict(), 
        "player_code": code,
        **location_data
    }, actor_id=current_user["id"])

@router.put("/{player_id}")
def update_player(player_id: int, player: PlayerUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    updated_player = PlayerService.update_player(db, player_id, player.dict(exclude_unset=True), actor_id=current_user["id"])
    if not updated_player:
        raise HTTPException(status_code=404, detail="Player not found")
    return updated_player

@router.delete("/{player_id}")
def delete_player(player_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    success = PlayerService.delete_player(db, player_id, actor_id=current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"message": "Player released from squad successfully"}

@router.get("/{player_id}/dna")
def get_player_dna(player_id: int, db: Session = Depends(get_db)):
    """Football DNA / Player Identity: Permanent career timeline and progression history."""
    from backend.app.database.models import Player, Transfer, MatchEvent, PlayerStat, Institution, Award
    
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player DNA profile not found")

    # 1. Career Roadmap (Transfers + Initial Institution)
    transfers = db.query(Transfer).filter(Transfer.player_id == player_id).order_by(Transfer.transfer_date.asc()).all()
    
    history = []
    # Initial registration
    initial_inst = db.query(Institution).filter(Institution.id == player.institution_id).first()
    history.append({
        "type": "REGISTRATION",
        "institution": initial_inst.name if initial_inst else "Unknown",
        "date": player.player_code, # Reference only
        "note": "Official Identity Initialized"
    })

    for t in transfers:
        history.append({
            "type": "TRANSFER",
            "from": t.from_institution.name if t.from_institution else "N/A",
            "to": t.to_institution.name if t.to_institution else "N/A",
            "date": t.transfer_date.strftime("%Y-%m-%d"),
            "status": t.status
        })

    # 2. Key Achievements (Awards)
    awards = db.query(Award).filter(Award.player_id == player_id).order_by(Award.timestamp.desc()).all()
    achievements = [{"award": a.award_type, "season": a.season, "date": a.timestamp.strftime("%Y-%m-%d")} for a in awards]

    # 3. Performance Evolution (Trend of stats)
    stats = db.query(PlayerStat).filter(PlayerStat.player_id == player_id).order_by(PlayerStat.timestamp.asc()).all()
    evolution = [{
        "date": s.timestamp.strftime("%Y-%m-%d"),
        "rating": s.rating,
        "goals": s.shots,
        "sprint": s.sprint_distance
    } for s in stats]

    return {
        "identity": {
            "player_code": player.player_code,
            "name": player.name,
            "nationality": player.nationality,
            "current_institution": initial_inst.name if initial_inst else "None"
        },
        "timeline": history,
        "achievements": achievements,
        "performance_trend": evolution,
        "ai_profile": {
            "potential": player.potential_score,
            "readiness": "Professional" if player.potential_score > 85 else "Development"
        }
    }
