from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.config.database import get_db
from backend.app.database.models import Player, Institution, Match, MatchSquad, PlayerStat, TrainingSession, Transfer
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

# ==========================================
# TRAINING HUB ENDPOINTS
# ==========================================

@router.get("/training", dependencies=[Depends(club_access)])
def get_training_sessions(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    sessions = db.query(TrainingSession).filter(
        TrainingSession.institution_id == inst_id,
        TrainingSession.is_deleted == False
    ).order_by(TrainingSession.date.desc()).all()
    return sessions

@router.post("/training", dependencies=[Depends(club_access)])
def create_training_session(data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    if not inst_id:
        raise HTTPException(status_code=403, detail="Not linked to an institution")

    payload = {
        "institution_id": inst_id,
        "date": datetime.utcnow() if not data.get("date") else datetime.fromisoformat(data["date"].replace("Z", "+00:00")),
        "topic": data.get("topic", "General Training"),
        "notes": data.get("notes", ""),
        "attendance_rate": data.get("attendance_rate", 100.0)
    }
    return CrudMixin.create(TrainingSession, db, payload, actor_id=current_user["id"])

@router.delete("/training/{session_id}", dependencies=[Depends(club_access)])
def delete_training_session(session_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id, TrainingSession.institution_id == inst_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_deleted = True
    db.commit()
    return {"message": "Session deleted"}

@router.put("/training/{session_id}", dependencies=[Depends(club_access)])
def update_training_session(session_id: int, data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id, TrainingSession.institution_id == inst_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if "date" in data:
        session.date = datetime.utcnow() if not data.get("date") else datetime.fromisoformat(data["date"].replace("Z", "+00:00"))
    if "topic" in data:
        session.topic = data["topic"]
    if "notes" in data:
        session.notes = data["notes"]
    if "attendance_rate" in data:
        session.attendance_rate = data["attendance_rate"]
        
    db.commit()
    return {"message": "Session updated"}

# ==========================================
# TRANSFER ENDPOINTS
# ==========================================

@router.get("/transfers", dependencies=[Depends(club_access)])
def get_transfers(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    transfers = db.query(Transfer).filter(
        (Transfer.from_institution_id == inst_id) | (Transfer.to_institution_id == inst_id),
        Transfer.is_deleted == False
    ).order_by(Transfer.transfer_date.desc()).all()
    
    res = []
    for t in transfers:
        player = db.query(Player).filter(Player.id == t.player_id).first()
        from_inst = db.query(Institution).filter(Institution.id == t.from_institution_id).first()
        to_inst = db.query(Institution).filter(Institution.id == t.to_institution_id).first()
        
        res.append({
            "id": t.id,
            "player_id": t.player_id,
            "player_name": player.name if player else "Unknown",
            "position": player.position if player else "-",
            "age": player.age if player else None,
            "team_category": player.team_category if player else "-",
            "from_institution": from_inst.name if from_inst else "Free Agent",
            "from_institution_id": t.from_institution_id,
            "to_institution": to_inst.name if to_inst else "-",
            "to_institution_id": t.to_institution_id,
            "fee": t.fee,
            "status": t.status,
            "transfer_date": t.transfer_date
        })
    return res

@router.post("/transfers/request", dependencies=[Depends(club_access)])
def request_transfer(data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    if not inst_id:
        raise HTTPException(status_code=403, detail="Not linked to an institution")
        
    player_id = data.get("player_id")
    to_inst_id = data.get("to_institution_id")
    
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
        
    payload = {
        "player_id": player_id,
        "from_institution_id": player.institution_id,
        "to_institution_id": to_inst_id,
        "fee": data.get("fee", 0.0),
        "status": "PENDING"
    }
    return CrudMixin.create(Transfer, db, payload, actor_id=current_user["id"])

@router.put("/transfers/{transfer_id}/status", dependencies=[Depends(club_access)])
def update_transfer_status(transfer_id: int, data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
        
    if transfer.from_institution_id != inst_id and transfer.to_institution_id != inst_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this transfer")
        
    new_status = data.get("status")
    if new_status not in ["APPROVED", "REJECTED", "CANCELLED", "COMPLETED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    transfer.status = new_status
    
    if new_status in ["APPROVED", "COMPLETED"]:
        player = db.query(Player).filter(Player.id == transfer.player_id).first()
        if player:
            player.institution_id = transfer.to_institution_id
            
    db.commit()
    return {"message": f"Transfer status updated to {new_status}"}

# ==========================================
# INSTITUTION CONFIGURATION ENDPOINTS
# ==========================================

@router.put("/institution", dependencies=[Depends(club_access)])
def update_institution(data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst_id = current_user.get("institution_id")
    if not inst_id:
        raise HTTPException(status_code=403, detail="Not linked to an institution")
        
    institution = db.query(Institution).filter(Institution.id == inst_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
        
    if "logo_url" in data:
        institution.logo_url = data["logo_url"]
    if "stadium_name" in data:
        institution.stadium_name = data["stadium_name"]
    if "name" in data:
        institution.name = data["name"]
        
    db.commit()
    return {
        "message": "Institution updated",
        "logo_url": institution.logo_url,
        "stadium_name": institution.stadium_name,
        "institution_name": institution.name
    }
