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
    MatchSquad, MatchSession, SystemActivity
)
from pydantic import BaseModel
from typing import List, Optional
import uuid
import secrets
from datetime import datetime

router = APIRouter(prefix="/api/match", tags=["match_control"])


# ======================================================
# KEY / TOKEN GENERATORS
# ======================================================

def generate_api_key(institution_code: str) -> str:
    """Human-readable: FWFA-{CODE}-{YEAR}-{RAND4}"""
    rand = secrets.token_hex(2).upper()
    year = datetime.now().year
    code = institution_code.upper().replace(" ", "")[:6]
    return f"FWFA-{code}-{year}-{rand}"


def generate_match_token() -> str:
    """UUID v4 match session token"""
    return str(uuid.uuid4())


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
    role: str                # "starting" or "bench"
    position: str            # GK, LB, CB, RB, CDM, CM, CAM, LW, RW, ST
    jersey_number: int


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


class UpdateEventRequest(BaseModel):
    player_id: Optional[int] = None
    minute: Optional[int] = None
    event_type: Optional[str] = None


# ======================================================
# ENDPOINTS
# ======================================================

@router.post("/create")
def create_match(req: CreateMatchRequest, db: Session = Depends(get_db)):
    """Create a new match session and generate API Key + Match Token."""
    institution = db.query(Institution).filter(
        Institution.id == req.institution_id
    ).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    api_key = generate_api_key(institution.code)
    match_token = generate_match_token()

    try:
        match_dt = datetime.fromisoformat(req.match_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601.")

    new_match = Match(
        home_team_id=req.institution_id,
        stadium=req.venue,
        match_date=match_dt,
        competition_type=req.competition_type,
        opponent_name=req.opponent_name,
        api_key=api_key,
        match_token=match_token,
        status="SCHEDULED"
    )
    db.add(new_match)
    db.flush()

    session = MatchSession(
        match_id=new_match.id,
        match_token=match_token
    )
    db.add(session)

    log = SystemActivity(
        action="MATCH_CREATED",
        description=f"Match: {institution.name} vs {req.opponent_name} @ {req.venue} ({req.competition_type})",
        actor_email="SYSTEM"
    )
    db.add(log)
    db.commit()

    return {
        "match_id": new_match.id,
        "api_key": api_key,
        "match_token": match_token,
        "message": "Match session created. Configure squad and kits, then install the API Key on the AI Machine."
    }


@router.get("/all")
def get_all_matches(institution_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all matches, optionally filtered by institution."""
    query = db.query(Match)
    if institution_id:
        query = query.filter(
            (Match.home_team_id == institution_id) | (Match.away_team_id == institution_id)
        )
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
def assign_squad(match_id: int, req: AssignSquadRequest, db: Session = Depends(get_db)):
    """Assign 18-man squad with positions and roles (starting/bench)."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Clear existing squad
    db.query(MatchSquad).filter(MatchSquad.match_id == match_id).delete()
    db.flush()

    for p in req.players:
        squad_entry = MatchSquad(
            match_id=match_id,
            player_id=p.player_id,
            role=p.role,
            position=p.position,
            jersey_number=p.jersey_number
        )
        db.add(squad_entry)

    db.commit()
    return {"message": f"Squad of {len(req.players)} players assigned successfully"}


@router.post("/{match_id}/kits")
def set_kits(match_id: int, req: KitRequest, db: Session = Depends(get_db)):
    """Set home and away kit colors for AI jersey detection."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.kit_home_color = req.kit_home_color
    match.kit_home_socks_color = req.kit_home_socks_color
    match.kit_away_color = req.kit_away_color
    match.kit_away_socks_color = req.kit_away_socks_color
    db.commit()
    return {"message": "Kit colors saved. AI Machine will use these for jersey detection."}


@router.post("/{match_id}/event/manual")
async def manual_event(match_id: int, req: ManualEventRequest, db: Session = Depends(get_db)):
    """Record a manual event (goal, foul, card, substitution) from the Match Page."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    event = MatchEvent(
        match_id=match_id,
        player_id=req.player_id,
        event_type=req.event_type,
        timestamp_match=req.minute,
        x_pos=req.x,
        y_pos=req.y,
        source="manual",
        is_confirmed=True,
        value=1.0
    )
    db.add(event)

    # Update score for manual goals
    if req.event_type == "goal":
        if req.team == "home":
            match.score_home = (match.score_home or 0) + 1
        else:
            match.score_away = (match.score_away or 0) + 1

    db.commit()
    db.refresh(event)

    # Broadcast to Match Page WebSocket viewers
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

    return {"message": "Event recorded", "event_id": event.id}


@router.delete("/{match_id}/correct/{event_id}")
async def var_correction(match_id: int, event_id: int, db: Session = Depends(get_db)):
    """VAR-style correction: remove an incorrect event."""
    event = db.query(MatchEvent).filter(
        MatchEvent.id == event_id,
        MatchEvent.match_id == match_id
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Revert goal score if needed
    match = db.query(Match).filter(Match.id == match_id).first()
    if event.event_type == "goal" and match:
        match.score_home = max(0, (match.score_home or 0) - 1)

    db.delete(event)
    db.commit()

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
def approve_event(match_id: int, event_id: int, db: Session = Depends(get_db)):
    """Manually approve an AI-generated event."""
    event = db.query(MatchEvent).filter(MatchEvent.id == event_id, MatchEvent.match_id == match_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.is_confirmed = True
    db.commit()
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
async def update_status(match_id: int, req: StatusRequest, db: Session = Depends(get_db)):
    """Update match status: LIVE, PAUSED, COMPLETED."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = req.status
    db.commit()

    from backend.app.match_control.ai_ingest import manager
    await manager.broadcast_match_event(match_id, {
        "type": "status_change",
        "status": req.status
    })

    return {"message": f"Match status → {req.status}"}


@router.get("/token/{token}/validate")
def validate_token(token: str, key: str, db: Session = Depends(get_db)):
    """AI Machine validates its credentials before connecting."""
    match = db.query(Match).filter(
        Match.match_token == token,
        Match.api_key == key
    ).first()
    if not match:
        raise HTTPException(status_code=401, detail="Invalid token or API key — connection rejected")

    home = db.query(Institution).filter(Institution.id == match.home_team_id).first()
    
    # Fetch squad for AI identity binding
    squad_data = []
    for member in match.squad:
        player = db.query(Player).filter(Player.id == member.player_id).first()
        squad_data.append({
            "player_id": member.player_id,
            "name": player.name if player else "Unknown",
            "jersey": member.jersey_number,
            "team": "home" # Assuming home institution managed squad for now
        })

    return {
        "valid": True,
        "match_id": match.id,
        "home_team": home.name if home else "Unknown",
        "opponent": match.opponent_name,
        "status": match.status,
        "kit_home": match.kit_home_color,
        "kit_home_socks": match.kit_home_socks_color,
        "kit_away": match.kit_away_color,
        "kit_away_socks": match.kit_away_socks_color,
        "venue": match.stadium,
        "competition": match.competition_type,
        "squad": squad_data
    }


@router.get("/institution/{institution_id}/players")
def get_institution_players(institution_id: int, db: Session = Depends(get_db)):
    """Fetch players for squad selection on the Match Page."""
    players = db.query(Player).filter(Player.institution_id == institution_id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "player_code": p.player_code,
            "number": None  # jersey number assigned during squad setup
        }
        for p in players
    ]
