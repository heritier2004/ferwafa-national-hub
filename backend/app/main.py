from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, uuid, shutil
from backend.app.auth import routes as auth_routes
from backend.app.admin import routes as admin_routes
from backend.app.ferwafa import routes as ferwafa_routes
from backend.app.match_control import routes as match_control_routes
from backend.app.config.database import Base, engine, SessionLocal
from backend.app.database.models import SystemError, Match
import traceback
from backend.app.database import models
from sqlalchemy import text
from backend.app.auth.security import get_password_hash
from backend.app.database.models import User, SystemSetting

# =====================================================
# DATABASE SETUP — Create tables + safe migrations
# =====================================================
Base.metadata.create_all(bind=engine)

# Safe column migrations for existing 'matches' table
_MATCH_MIGRATIONS = [
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS api_key VARCHAR UNIQUE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS match_token VARCHAR UNIQUE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS opponent_name VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_type VARCHAR DEFAULT 'League'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_home_color VARCHAR DEFAULT '#FF0000'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_home_socks_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_color VARCHAR DEFAULT '#0000FF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_socks_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_id INTEGER",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_finalized BOOLEAN DEFAULT FALSE",
]

_GLOBAL_MIGRATIONS = [
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS stadium_name VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS province VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS sector VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS cell VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT",
]

with engine.connect() as conn:
    for sql in _MATCH_MIGRATIONS + _GLOBAL_MIGRATIONS:
        try:
            conn.execute(text(sql))
        except Exception:
            pass
    conn.commit()

# --- NEW: Database Seeding ---
db_seed = SessionLocal()
try:
    # 1. Seed Super Admin
    admin_user = db_seed.query(User).filter(User.email == "admin@ferwafa.rw").first()
    if not admin_user:
        admin_user = User(email="admin@ferwafa.rw", role="SUPER_ADMIN")
        db_seed.add(admin_user)
        print("[SEED] Creating Super Admin...")
    
    admin_user.full_name = "Technical Lead (Super Admin)"
    admin_user.password_hash = get_password_hash("admin123")
    print("[SEED] Super Admin updated/verified: admin@ferwafa.rw / admin123")

    # 2. Seed FERWAFA Official
    ferwafa_user = db_seed.query(User).filter(User.email == "hq@ferwafa.rw").first()
    if not ferwafa_user:
        ferwafa_user = User(email="hq@ferwafa.rw", role="FERWAFA")
        db_seed.add(ferwafa_user)
        print("[SEED] Creating FERWAFA HQ...")
    
    ferwafa_user.full_name = "FERWAFA National Hub"
    ferwafa_user.password_hash = get_password_hash("ferwafa123")
    print("[SEED] FERWAFA HQ updated/verified: hq@ferwafa.rw / ferwafa123")

    # 3. Seed Global System Settings
    if not db_seed.query(SystemSetting).filter(SystemSetting.key == "footer_text").first():
        db_seed.add(SystemSetting(
            key="footer_text", 
            value="&copy; 2026 FERWAFA National Intelligence Platform. All Rights Reserved. | Technical Support: tech@ferwafa.rw",
            description="Site-wide footer text"
        ))
    if not db_seed.query(SystemSetting).filter(SystemSetting.key == "system_name").first():
        db_seed.add(SystemSetting(
            key="system_name",
            value="FERWAFA National Hub",
            description="Site branding name"
        ))

    # 4. Seed Official Competition
    from backend.app.database.models import Competition
    if not db_seed.query(Competition).filter(Competition.name == "National Premier League 2026").first():
        db_seed.add(Competition(
            name="National Premier League 2026",
            type="LEAGUE",
            season="2026",
            status="ACTIVE"
        ))
        print("[SEED] Created National Premier League 2026")

    db_seed.commit()
except Exception as e:
    print(f"[SEED] Seeding Error: {e}")
finally:
    db_seed.close()
# -----------------------------

# =====================================================
# APP
# =====================================================
app = FastAPI(title="National Football Intelligence System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# GLOBAL EXCEPTION HANDLER
# =====================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    db = SessionLocal()
    try:
        new_error = SystemError(
            error_type=type(exc).__name__,
            message=str(exc),
            traceback=traceback.format_exc()
        )
        db.add(new_error)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

    return JSONResponse(
        status_code=500,
        content={"detail": "An internal system error occurred. It has been logged for the Super Admin."},
    )

# =====================================================
# ROUTES
# =====================================================
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_routes.router)
app.include_router(ferwafa_routes.router)
app.include_router(match_control_routes.router)

# =====================================================
# UPLOAD HANDLER
# =====================================================
UPLOAD_DIR = os.path.join(os.getcwd(), "frontend", "assets", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/assets/uploads/{unique_filename}"}

# =====================================================
# WEBSOCKET — AI MACHINE INGESTION
# =====================================================
@app.websocket("/ws/ai-ingest")
async def ai_machine_ingest(websocket: WebSocket, token: str, key: str):
    """
    AI Pitch Machine connects here with its match token + API key.
    The server validates credentials, then forwards all events
    to Match Page viewers subscribed to that match.
    """
    from backend.app.match_control.ai_ingest import manager

    db = SessionLocal()
    try:
        match = db.query(Match).filter(
            Match.match_token == token,
            Match.api_key == key
        ).first()

        if not match:
            await websocket.accept()
            await websocket.send_json({
                "type": "auth_error",
                "message": "Invalid token or API key — connection rejected"
            })
            await websocket.close(code=4001)
            return

        match_id = match.id
    finally:
        db.close()

    connected = await manager.connect_ai_machine(websocket, match_id)
    if not connected:
        await websocket.close(code=4002) # Duplicate session rejected
        return

    # Notify Match Page that AI is now live
    await manager.broadcast_match_event(match_id, {
        "type": "ai_connected",
        "message": "AI Pitch Machine is now online"
    })

    try:
        while True:
            data = await websocket.receive_json()
            
            # --- SIGNATURE VERIFICATION (Production Hardening) ---
            sig = data.get("signature")
            payload = data.get("payload")
            
            if not sig or not payload: continue
            
            # Re-calculate HMAC using shared API Key
            msgString = json.dumps(payload, sort_keys=True)
            expected_sig = hmac.new(
                api_key.encode(),
                msgString.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(sig, expected_sig):
                print(f"❌ [AUTH_FAIL] Invalid HMAC on match {match_id}")
                continue
            
            # -----------------------------------------------------

            data = payload # Unwrap for processing
            manager.update_heartbeat(match_id)
            
            # 3. Ingest & Persist if it's a match event
            if data.get("type") == "match_event" and manager.validate_ai_event(match_id, data):
                db_p = SessionLocal()
                try:
                    src_id = data.get("source_event_id")
                    if src_id:
                        exists = db_p.query(models.MatchEvent).filter(
                            models.MatchEvent.source_event_id == src_id
                        ).first()
                        if exists:
                            db_p.close()
                            continue

                    # Tiered Confidence Logic
                    total_conf = data.get("ai_confidence", 0)
                    is_auto_confirmed = (total_conf >= 0.8)

                    # Create Database Record (Ledger Sync)
                    new_ev = models.MatchEvent(
                        match_id=match_id,
                        player_id=data.get("player_id"),
                        event_type=data.get("event_type", "ai_event"),
                        timestamp_match=data.get("minute", 0),
                        x_pos=data.get("x") if data.get("x") is not None else data.get("x_pos"),
                        y_pos=data.get("y") if data.get("y") is not None else data.get("y_pos"),
                        ai_confidence=total_conf,
                        ocr_conf=data.get("ocr_conf"),
                        det_conf=data.get("det_conf"),
                        track_conf=data.get("track_conf"),
                        is_confirmed=is_auto_confirmed,
                        source="ai",
                        source_event_id=src_id,
                        server_timestamp=datetime.utcnow() # Authoritative Time
                    )
                    db_p.add(new_ev)
                    
                    # Score update for confirmed goals
                    if data.get("event_type") == "goal" and is_auto_confirmed:
                        match_ref = db_p.query(models.Match).filter(models.Match.id == match_id).first()
                        if match_ref:
                            if data.get("team") == "home": match_ref.score_home += 1
                            else: match_ref.score_away += 1
                            data["score_home"] = match_ref.score_home
                            data["score_away"] = match_ref.score_away

                    db_p.commit()
                except Exception as e:
                    print(f"[DB_INGEST_ERROR] {e}")
                finally:
                    db_p.close()

            # 4. Global Broadcast
            data["source"] = "ai_machine"
            await manager.broadcast_match_event(match_id, data)
    except WebSocketDisconnect:
        manager.disconnect_ai_machine(match_id)
        await manager.broadcast_match_event(match_id, {
            "type": "ai_disconnected",
            "message": "AI Pitch Machine has disconnected"
        })


# =====================================================
# WEBSOCKET — MATCH PAGE VIEWER
# =====================================================
@app.websocket("/ws/match/{match_id}")
async def match_page_viewer(websocket: WebSocket, match_id: int):
    """Match Page connects here to receive real-time events."""
    from backend.app.match_control.ai_ingest import manager
    await manager.connect_viewer(websocket, match_id)
    try:
        while True:
            # Keep-alive: receive any client messages (e.g. ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_viewer(websocket, match_id)


# =====================================================
# DOWNLOAD ENDPOINT
# =====================================================
@app.get("/api/download/ai-machine")
async def download_ai_machine(os_type: str = "windows"):
    if os_type == "windows":
        exe_path = os.path.join(os.getcwd(), "dist", "AIMatchMachine.exe")
        if os.path.exists(exe_path):
            return FileResponse(path=exe_path, filename="AIMatchMachine.exe", media_type="application/vnd.microsoft.portable-executable")
        return JSONResponse(status_code=404, content={"message": "AI Machine executable not found. Build may still be running."})
    else:
        import shutil
        dist_dir = os.path.join(os.getcwd(), "dist")
        os.makedirs(dist_dir, exist_ok=True)
        zip_base_path = os.path.join(dist_dir, "AI_Pitch_Machine_CrossPlatform")
        
        ai_machine_dir = os.path.join(os.getcwd(), "ai_machine")
        if os.path.exists(ai_machine_dir):
            shutil.make_archive(zip_base_path, 'zip', os.path.dirname(ai_machine_dir), os.path.basename(ai_machine_dir))
            return FileResponse(path=zip_base_path + ".zip", filename="AI_Pitch_Machine_CrossPlatform.zip", media_type="application/zip")
            
        return JSONResponse(status_code=404, content={"message": "AI Machine package not found."})

# =====================================================
# STATIC FILES (Frontend)
# =====================================================
frontend_path = os.path.join(os.getcwd(), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
