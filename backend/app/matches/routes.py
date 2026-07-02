from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import secrets

from backend.app.auth.dependencies import get_current_user, RoleChecker
from backend.app.config.database import get_db
from backend.app.utils.crud import CrudMixin, transactional
from backend.app.database.models import Match, MatchEvent, AuditLog, Institution
from backend.app.matches.service import MatchService
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/matches",
    tags=["matches"]
)

# Pydantic models for request bodies
class MatchCreate(BaseModel):
    home_team_id: int
    away_team_id: Optional[int] = None
    opponent_name: Optional[str] = None
    stadium: str
    match_date: Optional[datetime] = None
    competition_id: Optional[int] = None
    division_name: Optional[str] = None
    squad: Optional[List[int]] = None
    starting_xi: Optional[List[int]] = None
    kit_colors: Optional[dict] = None

class MatchUpdate(BaseModel):
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    opponent_name: Optional[str] = None
    stadium: Optional[str] = None
    match_date: Optional[datetime] = None
    status: Optional[str] = None
    score_home: Optional[int] = None
    score_away: Optional[int] = None
    kit_home_color: Optional[str] = None
    kit_home_shorts_color: Optional[str] = None
    kit_away_color: Optional[str] = None
    kit_away_shorts_color: Optional[str] = None
    kit_away_socks_color: Optional[str] = None
    formation: Optional[str] = None
    expected_version: Optional[int] = None

# ── CRUD ENDPOINTS ──────────────────────────────────────────────────

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        import hashlib
        from datetime import timedelta
        from backend.app.database.models import MatchSquad, APIKey, MatchSession, Institution
        from backend.app.match_control.routes import generate_api_key, generate_match_token

        data_dict = payload.dict()
        squad_ids = data_dict.pop('squad', None)
        starting_xi_ids = data_dict.pop('starting_xi', None)
        kit_colors = data_dict.pop('kit_colors', None)

        if kit_colors:
            data_dict['kit_home_color'] = kit_colors.get('jersey', '#FF0000')
            data_dict['kit_home_shorts_color'] = kit_colors.get('shorts', '#FFFFFF')
            data_dict['kit_home_socks_color'] = kit_colors.get('socks', '#FFFFFF')

        new_match = CrudMixin.create(Match, db, data_dict, actor_id=current_user["id"])

        assigned_ids = set()
        if starting_xi_ids:
            for p_id in starting_xi_ids:
                db.add(MatchSquad(
                    match_id=new_match.id,
                    player_id=p_id,
                    role="starting",
                    jersey_number=None
                ))
                assigned_ids.add(p_id)
        if squad_ids:
            for p_id in squad_ids:
                if p_id not in assigned_ids:
                    db.add(MatchSquad(
                        match_id=new_match.id,
                        player_id=p_id,
                        role="substitute",
                        jersey_number=None
                    ))
        db.flush()

        inst = db.query(Institution).filter(Institution.id == new_match.home_team_id).first()
        inst_code = inst.code if inst else "CLUB"

        api_key = generate_api_key(inst_code)
        match_token = generate_match_token()
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

        new_match.match_token = match_token
        new_match.api_key = api_key
        new_match.session_status = "WAITING"
        new_match.expires_at = datetime.utcnow() + timedelta(hours=6)

        api_key_record = APIKey(
            key_hash=hashed_key,
            service_name=f"MATCH_KEY_{new_match.id}",
            owner_email=current_user.get("email") or "club@ferwafa.rw",
            expires_at=new_match.expires_at
        )
        db.add(api_key_record)

        session_payload = {
            "match_id": new_match.id,
            "match_token": match_token
        }
        CrudMixin.create(MatchSession, db, session_payload, actor_id=current_user["id"])

        db.commit()
        db.refresh(new_match)

        return {
            "match_id": new_match.id,
            "match_token": match_token,
            "api_key": api_key,
            "expires_at": new_match.expires_at.isoformat(),
            "message": "Match created and credentials generated successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
def list_matches(status: str = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return MatchService.get_matches(db, status)


@router.patch("/{match_id}", response_model=dict)
def update_match(match_id: int, payload: MatchUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    update_data = payload.dict(exclude_unset=True)
    expected_version = update_data.pop('expected_version', None)
    try:
        updated_match = CrudMixin.update(Match, db, match_id, update_data, actor_id=current_user["id"], expected_version=expected_version)
        return {"message": f"Match {match_id} updated successfully", "match": updated_match}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.delete("/{match_id}", response_model=dict)
def delete_match(match_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        CrudMixin.soft_delete(Match, db, match_id, actor_id=current_user["id"])
        return {"message": f"Match {match_id} soft‑deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ── MATCH CONTROL & CREDENTIALS ─────────────────────────────────────

@router.post("/initialize/{inst_id}")
def initialize_match(inst_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from backend.app.match_control.routes import generate_api_key, generate_match_token
    
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    
    api_key = generate_api_key(inst.code)
    match_token = generate_match_token()
    
    payload = {
        "home_team_id": inst_id,
        "status": "SCHEDULED",
        "match_date": datetime.utcnow(),
        "stadium": inst.stadium_name or "Unknown Venue",
        "score_home": 0,
        "score_away": 0,
        "api_key": api_key,
        "match_token": match_token,
        "session_status": "INACTIVE"
    }
    new_match = CrudMixin.create(Match, db, payload, actor_id=current_user["id"])
    return {"match_id": new_match.id}

@router.post("/{match_id}/credentials")
def generate_match_credentials(match_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    data, status_code = MatchService.validate_and_generate_credentials(db, match_id)
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=data.get("error", "Unknown error"))
    return data

@router.patch("/{match_id}/score")
def update_match_score(match_id: int, score_home: int, score_away: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Update via CRUD for auditing
    CrudMixin.update(Match, db, match_id, {"score_home": score_home, "score_away": score_away}, actor_id=current_user["id"])
    return {"status": "success", "score": f"{score_home}-{score_away}"}

# ── EVENT MANAGEMENT ────────────────────────────────────────────────

@router.post("/events/{event_id}/confirm")
def confirm_event(event_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    event = db.query(MatchEvent).filter(MatchEvent.id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    
    with transactional(db):
        event.is_confirmed = True
        event.editor_id = current_user["id"]
        
        db.add(AuditLog(
            action="EVENT_CONFIRMED",
            match_id=event.match_id,
            actor_email=current_user["email"],
            description=f"Confirmed {event.event_type} event ({event_id})"
        ))
    return {"status": "confirmed"}

@router.post("/events/{event_id}/reject")
def reject_event(event_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    event = db.query(MatchEvent).filter(MatchEvent.id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found")
    
    with transactional(db):
        event.is_voided = True
        event.editor_id = current_user["id"]
        
        db.add(AuditLog(
            action="EVENT_REJECTED",
            match_id=event.match_id,
            actor_email=current_user["email"],
            description=f"Rejected {event.event_type} event ({event_id})"
        ))
    return {"status": "rejected"}

@router.post("/{match_id}/manual-event")
def log_manual_event(match_id: int, event_type: str, player_id: int = None, x: float = None, y: float = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    payload = {
        "match_id": match_id,
        "player_id": player_id,
        "event_type": event_type,
        "x_pos": x,
        "y_pos": y,
        "is_confirmed": True,
        "source": "manual",
        "editor_id": current_user["id"],
        "server_timestamp": datetime.utcnow()
    }
    
    with transactional(db):
        new_ev = MatchEvent(**payload)
        db.add(new_ev)
        db.flush()
        
        db.add(AuditLog(
            action="MANUAL_EVENT_LOGGED",
            match_id=match_id,
            actor_email=current_user["email"],
            description=f"Manually logged {event_type} at ({x}, {y})"
        ))
    return {"status": "logged", "event_id": new_ev.id}

@router.get("/suggest-local/{inst_id}")
def suggest_local_match(inst_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()

    if not inst: return []
    
    opponents = db.query(Institution).filter(
        Institution.id != inst_id,
        Institution.district == inst.district,
        Institution.type == inst.type,
        Institution.is_deleted == False
    ).limit(5).all()
    
    if not opponents:
        opponents = db.query(Institution).filter(
            Institution.id != inst_id,
            Institution.province == inst.province,
            Institution.type == inst.type,
            Institution.is_deleted == False
        ).limit(5).all()

    return [{
        "id": o.id,
        "name": o.name,
        "district": o.district,
        "province": o.province,
        "stadium": o.stadium_name
    } for o in opponents]

@router.post("/{match_id}/squad/auto-generate")
def auto_generate_squad(match_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    data = MatchService.auto_generate_squad(db, match_id)

    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])
    return data
