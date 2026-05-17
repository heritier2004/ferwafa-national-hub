from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import Match, MatchSession
import hmac, hashlib, json
import uuid, os, shutil
from datetime import datetime

router = APIRouter(prefix="/api/ai", tags=["ai"])

async def verify_hmac(request: Request, db: Session = Depends(get_db)):
    """Middleware-style dependency for HMAC verification."""
    body = await request.json()
    sig = body.get("signature")
    payload = body.get("payload")
    match_token = body.get("match_token")
    api_key = body.get("api_key")

    if not sig or not payload or not match_token or not api_key:
        raise HTTPException(status_code=401, detail="Missing HMAC signature or credentials")

    match = db.query(Match).filter(Match.match_token == match_token, Match.api_key == api_key).first()
    if not match:
        raise HTTPException(status_code=401, detail="Invalid Match Token or API Key")

    # Re-calculate HMAC
    msg_string = json.dumps(payload, sort_keys=True)
    expected_sig = hmac.new(
        api_key.encode(),
        msg_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")
    
    return match

@router.post("/handshake")
async def ai_handshake(match: Match = Depends(verify_hmac), db: Session = Depends(get_db)):
    """Secure AI connection initialization with full environmental context."""
    from backend.app.database.models import Institution, Player
    home = db.query(Institution).filter(Institution.id == match.home_team_id).first()
    
    squad_data = []
    for member in match.squad:
        player = db.query(Player).filter(Player.id == member.player_id).first()
        squad_data.append({
            "player_id": member.player_id,
            "name": player.name if player else "Unknown",
            "jersey": member.jersey_number,
            "team": "home"
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
        "squad": squad_data,
        "server_time_iso": datetime.utcnow().isoformat() if "datetime" in globals() else None,
        # --- Location Intelligence ---
        "location_id": match.location_id,
        "region": match.region,
        "district": match.district,
        "venue_quality": match.venue_quality or 1.0,
        "pitch_type": home.pitch_type if home else "Natural Grass",
        "has_floodlights": home.has_floodlights if home else False
    }
@router.post("/stream-event")
async def stream_event(match: Match = Depends(verify_hmac), request: Request = None):
    """HTTP fallback for event streaming."""
    body = await request.json()
    payload = body.get("payload")
    # Process event logic (similar to WebSocket ingest)
    return {"status": "event_received", "event_id": uuid.uuid4().hex}

@router.post("/upload-frame")
async def upload_frame(match: Match = Depends(verify_hmac), file: UploadFile = File(...)):
    """Upload tactical frames for AI review."""
    UPLOAD_DIR = os.path.join(os.getcwd(), "frontend", "assets", "uploads", "tactical")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_path = os.path.join(UPLOAD_DIR, f"frame_{match.id}_{uuid.uuid4().hex[:8]}.jpg")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"status": "frame_uploaded", "url": file_path}

@router.get("/lineup-sync/{match_token}")
def sync_lineup(match_token: str, db: Session = Depends(get_db)):
    """Retrieve the latest official lineup for AI OCR mapping."""
    match = db.query(Match).filter(Match.match_token == match_token).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    return {"squad": [
        {"player_id": s.player_id, "jersey": s.jersey_number, "position": s.position}
        for s in match.squad
    ]}

@router.post("/status")
async def ai_status(data: dict, match: Match = Depends(verify_hmac)):
    """Report hardware health (CPU/GPU/FPS)."""
    return {"status": "ok"}
