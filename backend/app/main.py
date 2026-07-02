from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os, uuid, shutil, json, hmac, hashlib
from datetime import datetime
from backend.app.auth import routes as auth_routes
from backend.app.admin import routes as admin_routes
from backend.app.admin import debug_routes
from backend.app.admin import generic_routes
from backend.app.admin import infrastructure_routes as infra_routes
from backend.app.admin.security_middleware import SecurityMiddleware
from backend.app.ferwafa import routes as ferwafa_routes
from backend.app.match_control import routes as match_control_routes
from backend.app.scouting import routes as scouting_routes
from backend.app.school import routes as school_routes
from backend.app.analytics import routes as analytics_routes
from backend.app.players import routes as players_routes
from backend.app.academy import routes as academy_routes
from backend.app.youth import routes as youth_routes
from backend.app.club import routes as club_routes
from backend.app.ai import routes as ai_routes
from backend.app.data import routes as data_routes
from backend.app.matches import routes as matches_routes
from backend.app.config.database import Base, engine, SessionLocal
from backend.app.auth.dependencies import get_current_user
from backend.app.database.models import SystemError, Match
import traceback
from backend.app.database import models
from sqlalchemy import text, inspect as sa_inspect
from contextlib import asynccontextmanager
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
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_home_shorts_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_home_socks_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_color VARCHAR DEFAULT '#0000FF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_shorts_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_socks_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS formation VARCHAR DEFAULT '4-3-3'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_id INTEGER",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_finalized BOOLEAN DEFAULT FALSE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS location_id VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS region VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS venue_quality FLOAT DEFAULT 1.0",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS division_name VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS session_status VARCHAR DEFAULT 'INACTIVE'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
]

_GLOBAL_MIGRATIONS = [
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS stadium_name VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS province VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS sector VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS cell VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS age INTEGER",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS location_id VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS region VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS team_category VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS talent_score FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS is_elite_prospect BOOLEAN DEFAULT FALSE",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS potential_score FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS growth_curve FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS injury_risk FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS fatigue_index FLOAT DEFAULT 0.0",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS national_ranking INTEGER",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS sprint_distance FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS stamina_index FLOAT DEFAULT 1.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS tactical_rating FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS xg FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS pass_accuracy FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS defensive_actions INTEGER DEFAULT 0",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS contact VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE",
]

_EVENT_MIGRATIONS = [
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS ai_confidence FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS ocr_conf FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS det_conf FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS track_conf FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS is_confirmed BOOLEAN DEFAULT TRUE",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'manual'",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS is_voided BOOLEAN DEFAULT FALSE",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS parent_event_id INTEGER",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS original_ai_payload TEXT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS source_event_id VARCHAR",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS server_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS value FLOAT DEFAULT 1.0",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS editor_id INTEGER",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS audit_reason VARCHAR",
]

_COMPETITION_MIGRATIONS = [
    "ALTER TABLE competitions ADD COLUMN IF NOT EXISTS category VARCHAR",
    "ALTER TABLE competitions ADD COLUMN IF NOT EXISTS rules TEXT",
]

_CASCADE_MIGRATIONS = [
    # Match Events
    "ALTER TABLE match_events DROP CONSTRAINT IF EXISTS match_events_match_id_fkey, ADD CONSTRAINT match_events_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE",
    "ALTER TABLE match_events DROP CONSTRAINT IF EXISTS match_events_player_id_fkey, ADD CONSTRAINT match_events_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE",
    
    # Player Stats
    "ALTER TABLE player_stats DROP CONSTRAINT IF EXISTS player_stats_match_id_fkey, ADD CONSTRAINT player_stats_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE",
    "ALTER TABLE player_stats DROP CONSTRAINT IF EXISTS player_stats_player_id_fkey, ADD CONSTRAINT player_stats_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE",
    
    # AI Analysis
    "ALTER TABLE ai_analysis DROP CONSTRAINT IF EXISTS ai_analysis_match_id_fkey, ADD CONSTRAINT ai_analysis_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE",
    "ALTER TABLE ai_analysis DROP CONSTRAINT IF EXISTS ai_analysis_player_id_fkey, ADD CONSTRAINT ai_analysis_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE",
    
    # Match Squads
    "ALTER TABLE match_squads DROP CONSTRAINT IF EXISTS match_squads_match_id_fkey, ADD CONSTRAINT match_squads_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE",
    "ALTER TABLE match_squads DROP CONSTRAINT IF EXISTS match_squads_player_id_fkey, ADD CONSTRAINT match_squads_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE",
    
    # Match Sessions
    "ALTER TABLE match_sessions DROP CONSTRAINT IF EXISTS match_sessions_match_id_fkey, ADD CONSTRAINT match_sessions_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE",
    
    # Attendance
    "ALTER TABLE attendance DROP CONSTRAINT IF EXISTS attendance_player_id_fkey, ADD CONSTRAINT attendance_player_id_fkey FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE",
]

_SESSION_MIGRATIONS = [
    "ALTER TABLE match_sessions ADD COLUMN IF NOT EXISTS stream_id VARCHAR UNIQUE",
    "ALTER TABLE match_sessions ADD COLUMN IF NOT EXISTS api_key_id INTEGER",
    "ALTER TABLE match_sessions ADD COLUMN IF NOT EXISTS device_type VARCHAR DEFAULT 'UNKNOWN'",
    "ALTER TABLE match_sessions ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'INACTIVE'"
]

def _run_safe_migrations():
    """Run dialect-aware column migrations. Checks column existence via inspect."""
    is_sqlite = str(engine.url).startswith("sqlite")
    inspector = sa_inspect(engine)
    column_cache = {}

    with engine.connect() as conn:
        for sql in _MATCH_MIGRATIONS + _GLOBAL_MIGRATIONS + _EVENT_MIGRATIONS + _COMPETITION_MIGRATIONS + _SESSION_MIGRATIONS:
            try:
                parts = sql.split()
                table_name = parts[2]
                if "IF NOT EXISTS" in sql:
                    col_idx = parts.index("EXISTS") + 1
                else:
                    col_idx = parts.index("COLUMN") + 1
                col_name = parts[col_idx]

                if table_name not in column_cache:
                    try:
                        column_cache[table_name] = {c["name"] for c in inspector.get_columns(table_name)}
                    except Exception:
                        column_cache[table_name] = set()

                if col_name in column_cache[table_name]:
                    continue

                clean_sql = sql.replace(" IF NOT EXISTS", "")
                if is_sqlite:
                    clean_sql = clean_sql.replace(" UNIQUE", "")
                conn.execute(text(clean_sql))
                column_cache[table_name].add(col_name)
            except Exception:
                pass

        if not is_sqlite:
            for sql in _CASCADE_MIGRATIONS:
                try:
                    conn.execute(text(sql))
                except Exception:
                    pass

        conn.commit()

_run_safe_migrations()

# =====================================================
# APP — Lifespan Context Manager (replaces deprecated @app.on_event)
# =====================================================
@asynccontextmanager
async def lifespan(_app_instance):
    """Seed the database on startup without blocking the main event loop."""
    db_seed = SessionLocal()
    try:
        # 1. Seed Super Admin
        from backend.app.database.models import User, SystemSetting, Competition
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
                value="National Football Intel",
                description="Site branding name"
            ))

        # 4. Seed Sample Club
        from backend.app.database.models import Institution
        club_inst = db_seed.query(Institution).filter(Institution.code == "AMAV-2026").first()
        if not club_inst:
            club_inst = Institution(
                name="Amavubi Stars FC",
                type="club",
                code="AMAV-2026",
                stadium_name="Kigali Pelé Stadium",
                province="Kigali City",
                division="Premier League",
                status="APPROVED"
            )
            db_seed.add(club_inst)
            db_seed.commit()
            db_seed.refresh(club_inst)
            print(f"[SEED] Created Club Institution: {club_inst.name}")
        else:
            if club_inst.status != "APPROVED":
                club_inst.status = "APPROVED"
                db_seed.commit()
                print(f"[SEED] Updated Club Institution status to APPROVED")

        club_user = db_seed.query(User).filter(User.email == "club@ferwafa.rw").first()
        if not club_user:
            club_user = User(
                email="club@ferwafa.rw", 
                role="CLUB",
                full_name="Amavubi Club Manager",
                institution_id=club_inst.id
            )
            club_user.password_hash = get_password_hash("club123")
            db_seed.add(club_user)
            print("[SEED] Created Club User: club@ferwafa.rw / club123")

        # 4.5 Seed Sample Players for the Club
        from backend.app.database.models import Player
        existing_players = db_seed.query(Player).filter(Player.institution_id == club_inst.id).count()
        if existing_players == 0:
            print(f"[SEED] Seeding 18 players for {club_inst.name}...")
            positions = ["GK", "CB", "CB", "LB", "RB", "CM", "CM", "LW", "RW", "ST", "ST", "GK", "CB", "CM", "LW", "ST", "CM", "LB"]
            for i in range(18):
                new_p = Player(
                    institution_id=club_inst.id,
                    player_code=f"AMAV-{100+i}",
                    name=f"Player Alpha {i+1}",
                    position=positions[i],
                    jersey_number=i+1,
                    nationality="Rwandan"
                )
                db_seed.add(new_p)
            print("[SEED] 18 players seeded successfully.")
        
        db_seed.commit()

        # 5. Seed Official Competition
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
    yield

app = FastAPI(title="National Football Intelligence System", lifespan=lifespan)

# CORS & Security
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",")]
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# =====================================================
# GLOBAL EXCEPTION HANDLER
# =====================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    db = SessionLocal()
    request_id = getattr(request.state, "request_id", "N/A")
    try:
        new_error = SystemError(
            error_type=type(exc).__name__,
            message=str(exc),
            traceback=traceback.format_exc(),
            request_id=request_id
        )
        db.add(new_error)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal system error occurred. It has been logged for the Super Admin.",
            "request_id": request_id
        },
    )

# AI Machine Handshake moved to match_control/routes.py

# =====================================================
# ROUTES
# =====================================================
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin_routes.router)
app.include_router(infra_routes.router)
app.include_router(ferwafa_routes.router)
app.include_router(match_control_routes.router)
app.include_router(scouting_routes.router, prefix="/api")
app.include_router(school_routes.router)
app.include_router(analytics_routes.router)
app.include_router(players_routes.router, prefix="/api")
app.include_router(academy_routes.router)

# --- NEW UNIFIED ENDPOINT GROUPS ---
app.include_router(youth_routes.router)
app.include_router(club_routes.router)
app.include_router(ai_routes.router)
app.include_router(data_routes.router)
app.include_router(debug_routes.router)
app.include_router(generic_routes.router)
app.include_router(matches_routes.router)

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
    """
    from backend.app.match_control.ai_ingest import manager
    from backend.app.database.models import APIKey, MatchSession
    import hashlib

    db = SessionLocal()
    try:
        # 1. AUTHENTICATE API KEY
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        api_key_record = db.query(APIKey).filter(APIKey.key_hash == hashed_key, APIKey.is_active == True).first()
        if not api_key_record:
            await websocket.accept()
            await websocket.send_json({"type": "auth_error", "message": "Invalid API Key"})
            await websocket.close(code=4001)
            return

        # 2. VALIDATE MATCH TOKEN
        match = db.query(Match).filter(Match.match_token == token).first()
        if not match:
            await websocket.accept()
            await websocket.send_json({"type": "auth_error", "message": "Invalid Match Token"})
            await websocket.close(code=4001)
            return

        match_id = match.id
        
        # 3. CREATE STREAM SESSION BINDING
        stream_id = str(uuid.uuid4())
        session = db.query(MatchSession).filter(MatchSession.match_id == match_id).first()
        if not session:
            session = MatchSession(match_id=match_id, match_token=token)
            db.add(session)
        
        session.stream_id = stream_id
        session.api_key_id = api_key_record.id
        session.device_type = "AI_MACHINE_NODE"
        session.status = "ACTIVE"
        session.ai_connected = True
        session.last_heartbeat = datetime.utcnow()
        db.commit()

        # 4. CONNECT TO LIVE EVENT BUS
        if not await manager.connect_ai_machine(websocket, match_id):
            await websocket.close(code=4002)
            return

        # 5. BROADCAST STATUS
        await manager.broadcast_match_event(match_id, {
            "type": "ai_connected",
            "message": "AI Intelligence Hub Online",
            "stream_id": stream_id
        })

        # 6. LISTEN & PROCESS IN BACKGROUND
        while True:
            data = await websocket.receive_json()
            try:
                await manager.handle_secure_message(match_id, data)
            except ValueError as ve:
                await websocket.send_json({"type": "auth_error", "message": str(ve)})
                await websocket.close(code=4003)
                break

    except WebSocketDisconnect:
        manager.disconnect_ai_machine(match_id)
        await manager.broadcast_match_event(match_id, {
            "type": "ai_disconnected",
            "message": "AI Intelligence Hub Offline"
        })
    finally:
        db.close()


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
# DOWNLOAD ENDPOINT (Unified Universal Package)
# =====================================================
@app.get("/api/download/ai-machine")
async def download_ai_machine(current_user: dict = Depends(get_current_user), _os_type: str = "universal"):
    # We serve the single universal package that handles all OS via its own launchers
    # Use path relative to backend app root or current directory
    zip_path = os.path.join(os.getcwd(), "backend", "dist", "ai_machine_universal.zip")
    if not os.path.exists(zip_path):
        zip_path = os.path.join(os.getcwd(), "dist", "ai_machine_universal.zip")
    
    if os.path.exists(zip_path):
        return FileResponse(
            path=zip_path, 
            filename="AI_Pitch_Machine_Universal.zip", 
            media_type="application/zip"
        )
    
    return JSONResponse(
        status_code=404, 
        content={"message": "AI Machine package not found. Please run the release packager."}
    )

# =====================================================
# STATIC FILES (Frontend) & ROOT ROUTE
# =====================================================
# Health check endpoint for Electron startup
@app.get("/health")
async def health_check():
    return {"status": "ok"}

frontend_path = os.path.join(os.getcwd(), "frontend")

@app.get("/")
async def serve_landing_page():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Landing page not found"})

if os.path.exists(UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads_dir")
    app.mount("/assets/uploads", StaticFiles(directory=UPLOAD_DIR), name="assets_uploads_dir")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8001, reload=True)
