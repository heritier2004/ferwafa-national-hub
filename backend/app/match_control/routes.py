"""
Match Control API Routes
Handles match creation, squad setup, kit configuration,
manual events, VAR corrections, and AI machine session management.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import (
    Match, Institution, Player, MatchEvent,
    MatchSquad, MatchSession, SystemActivity, DisciplinaryRecord,
    PlayerStat, APIKey
)
from pydantic import BaseModel
from typing import List, Optional
import uuid
import secrets
from datetime import datetime
from backend.app.utils.crud import CrudMixin, transactional, crud_error

from backend.app.auth.dependencies import get_current_user, RoleChecker

router = APIRouter(
    prefix="/api/match", 
    tags=["match_control"],
    dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))]
)


# ======================================================
# KEY / TOKEN GENERATORS
# ======================================================

def generate_api_key(institution_code: str) -> str:
    """Bulletproof generator: FWFA-{CODE}-{YEAR}-{RAND4}"""
    rand = secrets.token_hex(3).upper()
    year = datetime.now().year
    # Handle empty or short codes gracefully
    safe_code = (institution_code or "UNKN").upper().replace(" ", "").strip()
    if len(safe_code) < 3: safe_code = (safe_code + "XXX")[:4]
    code = safe_code[:6]
    return f"FWFA-{code}-{year}-{rand}"


def generate_match_token() -> str:
    """Human-readable match session token: MATCH-YEAR-RANDOM"""
    rand = secrets.token_hex(3).upper()
    year = datetime.now().year
    return f"MATCH-{year}-{rand}"


# ======================================================
# REQUEST SCHEMAS
# ======================================================

class CreateMatchRequest(BaseModel):
    institution_id: int
    match_date: str          # ISO format: "2026-04-20T15:00"
    venue: str
    competition_type: str    # League, Cup, Friendly, International
    opponent_name: str


class SquadPlayer(BaseModel):
    player_id: int
    role: str                # "starting" or "substitute"
    position: Optional[str] = None
    jersey_number: Optional[int] = None


class AssignSquadRequest(BaseModel):
    players: List[SquadPlayer]


class KitRequest(BaseModel):
    kit_home_color: str      # hex, e.g. "#FF0000"
    kit_home_socks_color: str
    kit_away_color: str      # hex, e.g. "#0000FF"
    kit_away_socks_color: str


class ManualEventRequest(BaseModel):
    event_type: str          # goal, foul, yellow_card, red_card, substitution, offside
    player_id: Optional[int] = None
    minute: int
    team: Optional[str] = "home"   # "home" or "away"
    x: Optional[float] = None
    y: Optional[float] = None
    description: Optional[str] = None


class StatusRequest(BaseModel):
    status: str              # LIVE, PAUSED, COMPLETED

class PlayerPerformance(BaseModel):
    player_id: int
    assists: int = 0
    shots: int = 0
    passes: int = 0
    tackles: int = 0
    saves: int = 0
    minutes_played: int = 0

class BulkPerformanceRequest(BaseModel):
    performances: List[PlayerPerformance]

class AnalyticsRequest(BaseModel):
    minute: int
    possession_home: float
    possession_away: float

class UpdateEventRequest(BaseModel):
    player_id: Optional[int] = None
    minute: Optional[int] = None
    event_type: Optional[str] = None

class AiAuthRequest(BaseModel):
    api_key: str
    match_token: str


# ======================================================
# ENDPOINTS
# ======================================================

@router.post("/create")
def create_match(req: CreateMatchRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Create a new match session and generate API Key + Match Token."""
    # RBAC: CLUB role is limited to its own institution
    inst_id = req.institution_id
    if current_user["role"] == "CLUB":
        inst_id = current_user["institution_id"]
        if not inst_id:
            raise HTTPException(status_code=403, detail="CLUB user is not linked to an institution")

    institution = db.query(Institution).filter(
        Institution.id == inst_id
    ).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    api_key = generate_api_key(institution.code)
    match_token = generate_match_token()

    try:
        match_dt = datetime.fromisoformat(req.match_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")

    with transactional(db):
        import hashlib
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 1. Create API Key record
        api_key_record = APIKey(
            key_hash=hashed_key,
            service_name=f"AI_MACHINE_NODE_{institution.code}_{match_token}",
            owner_email=current_user.get("email") or f"manager@{institution.code.lower()}.rw",
            is_active=True
        )
        db.add(api_key_record)
        db.flush()

        # 2. Create Match
        match_payload = {
            "home_team_id": inst_id,
            "stadium": req.venue,
            "match_date": match_dt,
            "competition_type": req.competition_type,
            "opponent_name": req.opponent_name,
            "api_key": api_key,
            "match_token": match_token,
            "status": "SCHEDULED"
        }
        new_match = CrudMixin.create(Match, db, match_payload, actor_id=current_user["id"])
        
        # 3. Create MatchSession
        session_payload = {
            "match_id": new_match.id,
            "match_token": match_token,
            "api_key_id": api_key_record.id,
            "device_type": "AI_MACHINE_NODE",
            "status": "INACTIVE",
            "ai_connected": False
        }
        CrudMixin.create(MatchSession, db, session_payload, actor_id=current_user["id"])

        # CrudMixin already handles AuditLog for create(), but we can add a specific activity log if needed
        # but for now, the CrudMixin.create is sufficient for forensics.
        
    return {
        "match_id": new_match.id,
        "api_key": api_key,
        "match_token": match_token,
        "message": "Match session created. Configure squad and kits, then install the API Key on the AI Machine."
    }

@router.post("/save-setup")
def save_match_setup(data: dict, db: Session = Depends(get_db)):
    """Save lineup, kits, and stadium settings in one call."""
    match_id = data.get("match_id")
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    if "kits" in data:
        match.kit_home_color = data["kits"].get("home")
        match.kit_away_color = data["kits"].get("away")
    
    if "stadium" in data:
        match.stadium = data["stadium"]
        
    db.commit()
    return {"status": "Setup saved"}

@router.post("/generate-token")
def refresh_token(match_id: int, db: Session = Depends(get_db)):
    """Explicit endpoint to refresh Match Token/API Key."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match.match_token = generate_match_token()
    db.commit()
    return {"match_token": match.match_token}

@router.post("/validate-ai")
def validate_ai_credentials(req: AiAuthRequest, db: Session = Depends(get_db)):
    """AI Machine validates its credentials before connecting."""
    match = db.query(Match).filter(
        Match.match_token == req.match_token,
        Match.api_key == req.api_key
    ).first()
    if not match:
        raise HTTPException(status_code=401, detail="Invalid token or API key")

    return {"valid": True, "match_id": match.id}

@router.post("/end")
def end_match(match_id: int, db: Session = Depends(get_db)):
    """Finalize match and generate reports."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match.status = "COMPLETED"
    match.is_finalized = True
    db.commit()
    return {"status": "Match finalized", "report_url": f"/api/match/{match_id}/export/csv"}


@router.get("/all")
def get_all_matches(institution_id: Optional[int] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List all matches. Filtered by institution for CLUB role or by parameter."""
    query = db.query(Match)
    
    # RBAC: CLUB role is strictly limited to its own matches
    if current_user["role"] == "CLUB":
        inst_id = current_user["institution_id"]
        query = query.filter((Match.home_team_id == inst_id) | (Match.away_team_id == inst_id))
    elif institution_id:
        query = query.filter((Match.home_team_id == institution_id) | (Match.away_team_id == institution_id))
        
    matches = query.order_by(Match.match_date.desc()).all()

    result = []
    for m in matches:
        home = db.query(Institution).filter(Institution.id == m.home_team_id).first()
        ai_session = db.query(MatchSession).filter(MatchSession.match_id == m.id).first()
        result.append({
            "id": m.id,
            "home_team": home.name if home else "Unknown",
            "opponent": m.opponent_name or "TBD",
            "venue": m.stadium,
            "date": m.match_date.strftime("%Y-%m-%d %H:%M") if m.match_date else None,
            "competition": m.competition_type,
            "status": m.status,
            "score_home": m.score_home,
            "score_away": m.score_away,
            "api_key": m.api_key,
            "match_token": m.match_token,
            "ai_connected": ai_session.ai_connected if ai_session else False
        })
    return result


@router.get("/{match_id}")
def get_match(match_id: int, db: Session = Depends(get_db)):
    """Full match detail including squad, kits, and AI connection status."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    home = db.query(Institution).filter(Institution.id == match.home_team_id).first()
    ai_session = db.query(MatchSession).filter(MatchSession.match_id == match_id).first()

    squad_entries = db.query(MatchSquad).filter(MatchSquad.match_id == match_id).all()
    squad_data = []
    for s in squad_entries:
        player = db.query(Player).filter(Player.id == s.player_id).first()
        if player:
            squad_data.append({
                "player_id": player.id,
                "name": player.name,
                "position": s.position,
                "role": s.role,
                "jersey_number": s.jersey_number
            })

    return {
        "id": match.id,
        "home_team": home.name if home else "Unknown",
        "home_team_id": match.home_team_id,
        "opponent": match.opponent_name,
        "venue": match.stadium,
        "date": match.match_date.isoformat() if match.match_date else None,
        "competition": match.competition_type,
        "status": match.status,
        "score_home": match.score_home,
        "score_away": match.score_away,
        "api_key": match.api_key,
        "match_token": match.match_token,
        "kit_home": match.kit_home_color,
        "kit_home_socks": match.kit_home_socks_color,
        "kit_away": match.kit_away_color,
        "kit_away_socks": match.kit_away_socks_color,
        "squad": squad_data,
        "ai_connected": ai_session.ai_connected if ai_session else False,
        "ai_last_heartbeat": ai_session.last_heartbeat.isoformat() if (ai_session and ai_session.last_heartbeat) else None
    }


@router.post("/{match_id}/squad")
def assign_squad(match_id: int, req: AssignSquadRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Assign 18-man squad with positions and roles (starting/bench)."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Clear existing squad
    with transactional(db):
        db.query(MatchSquad).filter(MatchSquad.match_id == match_id).delete()
        
        for p in req.players:
            squad_payload = {
                "match_id": match_id,
                "player_id": p.player_id,
                "role": p.role,
                "position": p.position,
                "jersey_number": p.jersey_number
            }
            # MatchSquad is a join table, we use db.add but wrap in transaction
            db.add(MatchSquad(**squad_payload))
            
    return {"message": f"Squad of {len(req.players)} players assigned successfully"}


@router.post("/{match_id}/kits")
def set_kits(match_id: int, req: KitRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Set home and away kit colors for AI jersey detection."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    kit_payload = {
        "kit_home_color": req.kit_home_color,
        "kit_home_socks_color": req.kit_home_socks_color,
        "kit_away_color": req.kit_away_color,
        "kit_away_socks_color": req.kit_away_socks_color
    }
    CrudMixin.update(Match, db, match_id, kit_payload, actor_id=current_user["id"])
    return {"message": "Kit colors saved. AI Machine will use these for jersey detection."}


@router.post("/{match_id}/event/manual")
async def manual_event(match_id: int, req: ManualEventRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Record a manual event (goal, foul, card, substitution) and sync with National Databases."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    with transactional(db):
        # 1. Store as a Match Event
        event_payload = {
            "match_id": match_id,
            "player_id": req.player_id,
            "event_type": req.event_type,
            "timestamp_match": req.minute,
            "x_pos": req.x,
            "y_pos": req.y,
            "source": "manual",
            "is_confirmed": True,
            "value": 1.0
        }
        event = CrudMixin.create(MatchEvent, db, event_payload, actor_id=current_user["id"])

        # 2. Update Global Match Score for Goals
        if req.event_type == "goal":
            score_field = "score_home" if req.team == "home" else "score_away"
            new_score = (getattr(match, score_field) or 0) + 1
            CrudMixin.update(Match, db, match_id, {score_field: new_score}, actor_id=current_user["id"])

        # 3. CRITICAL: Add to National Disciplinary Record for Cards
        if req.event_type in ["yellow_card", "red_card"]:
            disc_payload = {
                "match_id": match_id,
                "player_id": req.player_id,
                "card_type": "YELLOW" if req.event_type == "yellow_card" else "RED",
                "description": req.description or f"Manual card issued in min {req.minute}",
                "minute": req.minute
            }
            CrudMixin.create(DisciplinaryRecord, db, disc_payload, actor_id=current_user["id"])
    
    db.refresh(event)

    # 4. Real-time Broadcast
    from backend.app.match_control.ai_ingest import manager
    player = db.query(Player).filter(Player.id == req.player_id).first() if req.player_id else None
    await manager.broadcast_match_event(match_id, {
        "type": "match_event",
        "event_type": req.event_type,
        "event_id": event.id,
        "player_id": req.player_id,
        "player_name": player.name if player else "Unknown",
        "minute": req.minute,
        "team": req.team,
        "description": req.description,
        "source": "manual",
        "score_home": match.score_home,
        "score_away": match.score_away
    })

    return {"message": "Event recorded and synced to National Database", "event_id": event.id}


@router.post("/{match_id}/event")
async def log_event_simple(match_id: int, req: ManualEventRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Simple event alias — same as /event/manual. Used by the Match Control Center UI."""
    return await manual_event(match_id, req, db, current_user)


@router.delete("/{match_id}/correct/{event_id}")
async def var_correction(match_id: int, event_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """VAR-style correction: remove an incorrect event."""
    event = db.query(MatchEvent).filter(
        MatchEvent.id == event_id,
        MatchEvent.match_id == match_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Revert goal score if needed
    match = db.query(Match).filter(Match.id == match_id).first()
    with transactional(db):
        if event.event_type == "goal" and match:
            score_field = "score_home" if any(p.player_id == event.player_id for p in match.squad if p.role == "starting" or p.role == "substitute") else "score_away"
            new_score = max(0, (getattr(match, score_field) or 0) - 1)
            CrudMixin.update(Match, db, match_id, {score_field: new_score}, actor_id=current_user["id"])

        CrudMixin.soft_delete(MatchEvent, db, event_id, actor_id=current_user["id"])

    from backend.app.match_control.ai_ingest import manager
    await manager.broadcast_match_event(match_id, {
        "type": "var_correction",
        "removed_event_id": event_id,
        "score_home": match.score_home if match else 0,
        "score_away": match.score_away if match else 0
    })

    return {"message": "Event removed — VAR correction applied"}


@router.get("/{match_id}/events")
def get_events(match_id: int, db: Session = Depends(get_db)):
    """Get all events for a match (for timeline rendering on Match Page)."""
    events = db.query(MatchEvent).filter(
        MatchEvent.match_id == match_id
    ).order_by(MatchEvent.timestamp_match.asc()).all()

    result = []
    for e in events:
        player = db.query(Player).filter(Player.id == e.player_id).first() if e.player_id else None
        result.append({
            "id": e.id,
            "type": e.event_type,
            "minute": e.timestamp_match,
            "player": player.name if player else "Unknown",
            "player_id": e.player_id,
            "x_pos": e.x_pos,
            "y_pos": e.y_pos,
            "is_confirmed": e.is_confirmed,
            "ai_confidence": e.ai_confidence,
            "conf_breakdown": {
                "ocr": e.ocr_conf,
                "det": e.det_conf,
                "track": e.track_conf
            }
        })
    return result


@router.post("/{match_id}/event/{event_id}/approve")
def approve_event(match_id: int, event_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Manually approve an AI-generated event."""
    CrudMixin.update(MatchEvent, db, event_id, {"is_confirmed": True}, actor_id=current_user["id"])
    return {"message": "Event approved", "id": event_id}


@router.patch("/{match_id}/event/{event_id}")
def update_event(match_id: int, event_id: int, req: UpdateEventRequest, db: Session = Depends(get_db)):
    """Manually correct/edit an event (Immutable Correction Pattern)."""
    old_event = db.query(MatchEvent).filter(MatchEvent.id == event_id, MatchEvent.match_id == match_id).first()
    if not old_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create NEW linked correction event
    new_event = MatchEvent(
        match_id=match_id,
        player_id=req.player_id if req.player_id is not None else old_event.player_id,
        event_type=req.event_type if req.event_type is not None else old_event.event_type,
        timestamp_match=req.minute if req.minute is not None else old_event.timestamp_match,
        x_pos=old_event.x_pos,
        y_pos=old_event.y_pos,
        source="correction",
        parent_event_id=old_event.id,
        is_confirmed=True,
        ai_confidence=old_event.ai_confidence
    )
    db.add(new_event)
    db.flush() # get ID

    # Void old event
    old_event.is_voided = True
    db.commit()
    
    return {"message": "Event corrected (New record created)", "new_id": new_event.id, "old_id": event_id}


@router.get("/{match_id}/export/csv")
def export_match_csv(match_id: int, db: Session = Depends(get_db)):
    """Generate a professional CSV export of all match events and stats."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match: raise HTTPException(status_code=404, detail="Match not found")

    events = db.query(MatchEvent).filter(MatchEvent.match_id == match_id).order_by(MatchEvent.timestamp_match.asc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Minute", "Event Type", "Player ID", "Player Name", "Team", "Confidence (%)", "Source", "X", "Y", "is_confirmed"])
    
    for e in events:
        player = db.query(Player).filter(Player.id == e.player_id).first() if e.player_id else None
        writer.writerow([
            e.timestamp_match, 
            e.event_type, 
            e.player_id or "—", 
            player.name if player else "Unknown",
            "Home" if e.player_id and any(p.player_id == e.player_id for p in match.squad) else "Away", # simplified
            round((e.ai_confidence or 1.0) * 100, 1),
            e.source,
            round(e.x_pos or 0, 2),
            round(e.y_pos or 0, 2),
            e.is_confirmed
        ])
    
    output.seek(0)
    filename = f"MatchReport_{match_id}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post("/{match_id}/status")
async def update_status(match_id: int, req: StatusRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Update match status: LIVE, PAUSED, COMPLETED."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    CrudMixin.update(Match, db, match_id, {"status": req.status}, actor_id=current_user["id"])

    from backend.app.match_control.ai_ingest import manager
    await manager.broadcast_match_event(match_id, {
        "type": "status_change",
        "status": req.status
    })

    return {"message": f"Match status → {req.status}"}




@router.get("/institution/{institution_id}/players")
def get_institution_players(institution_id: int, team_category: Optional[str] = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Fetch players for an institution (with RBAC and category filtering)."""
    # RBAC: CLUB role can only see its own players
    if current_user["role"] == "CLUB" and current_user["institution_id"] != institution_id:
        raise HTTPException(
            status_code=403, 
            detail="CROSS-CLUB ACCESS DENIED: You can only access players for your own club."
        )

    query = db.query(Player).filter(Player.institution_id == institution_id)
    if team_category:
        query = query.filter(Player.team_category == team_category)
        
    players = query.all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "player_code": p.player_code,
            "team_category": p.team_category,
            "age": p.age,
            "nationality": p.nationality,
            "jersey_number": p.jersey_number # default from registry
        }
        for p in players
    ]
