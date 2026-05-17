from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Date, Text
from sqlalchemy.orm import relationship
from backend.app.config.database import Base
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False) # SUPER_ADMIN, FERWAFA, CLUB, SCHOOL, ACADEMY, SCOUT
    full_name = Column(String)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    photo_url = Column(Text) # For scouts and other officials
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_token = Column(String, unique=True, index=True, nullable=False)
    ip_address = Column(String)
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)

class Institution(Base):
    __tablename__ = "institutions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # club, school, academy
    code = Column(String, unique=True, index=True, nullable=False)
    location = Column(String)
    logo_url = Column(Text)
    has_floodlights = Column(Boolean, default=False)
    pitch_type = Column(String, default="Natural Grass")
    capacity = Column(Integer, default=5000)
    division = Column(String, default="Premier League")
    
    # --- New Production Fields ---
    stadium_name = Column(String)
    province = Column(String)
    district = Column(String)
    sector = Column(String)
    cell = Column(String)
    
    # --- National Ranking ---
    national_ranking = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    contact = Column(String) # Phone or email contact for the institution
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    players = relationship("Player", back_populates="institution")

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    player_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    position = Column(String)
    height = Column(Float)
    weight = Column(Float)
    nationality = Column(String, default="Rwandan")
    date_of_birth = Column(Date)
    photo_url = Column(Text)
    jersey_number = Column(Integer)
    secondary_position = Column(String)
    preferred_foot = Column(String) # Left, Right, Both
    phone_number = Column(String)
    
    # --- Physical & Medical ---
    fitness_status = Column(String, default="Fit") # Fit, Recovering, Injured
    injury_status = Column(String, default="None") # None, Minor, Major
    
    # --- Youth Intelligence Fields ---
    age = Column(Integer)
    team_category = Column(String) # Senior, U17, U15, Academy, etc.
    location_id = Column(String)
    region = Column(String)
    district = Column(String)
    talent_score = Column(Float, default=0.0)
    is_elite_prospect = Column(Boolean, default=False)
    
    # --- Guardian & Medical ---
    guardian_name = Column(String)
    guardian_contact = Column(String)
    blood_group = Column(String)
    medical_conditions = Column(Text)
    last_medical_check = Column(Date)
    
    # --- AI Talent Prediction Engine ---
    potential_score = Column(Float, default=0.0)
    growth_curve = Column(Float, default=0.0)
    injury_risk = Column(Float, default=0.0)
    fatigue_index = Column(Float, default=0.0)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

    institution = relationship("Institution", back_populates="players")
    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerStat", back_populates="player", cascade="all, delete-orphan")
    ai_rankings = relationship("AIAnalysis", back_populates="player", cascade="all, delete-orphan")

class Team(Base):
    """Institutional Sub-teams (U15, U17, Senior)"""
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    name = Column(String, nullable=False) # e.g., "U17 Elite"
    category = Column(String) # U15, U17, U20, Senior
    coach_name = Column(String)
    kit_colors = Column(String)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    players = relationship("Player", back_populates="team")

class TrainingSession(Base):
    """Training schedule and technical focus"""
    __tablename__ = "training_sessions"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    topic = Column(String) # Tactical, Technical, Physical
    notes = Column(Text)
    attendance_rate = Column(Float)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class MedicalRecord(Base):
    """Player health and injury tracking"""
    __tablename__ = "medical_records"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    injury_type = Column(String)
    status = Column(String, default="ACTIVE") # ACTIVE, RECOVERED
    start_date = Column(Date)
    expected_return = Column(Date)
    notes = Column(Text)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class Attendance(Base):
    """Daily training attendance record for Schools and Academies"""
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    training_session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=True)
    date = Column(Date, default=datetime.utcnow().date())
    status = Column(String, default="PRESENT") # PRESENT, ABSENT, EXCUSED, INJURED
    notes = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

    player = relationship("Player")

class SystemSetting(Base):
    """Global system configuration (Footers, Branding, Maintenance Mode)"""
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class Season(Base):
    """National Season Lifecycle"""
    __tablename__ = "seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # e.g. "2026/2027"
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String, default="ACTIVE") # ACTIVE, COMPLETED, ARCHIVED
    created_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class Transfer(Base):
    """National Player Transfer Registry"""
    __tablename__ = "transfers"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    from_institution_id = Column(Integer, ForeignKey("institutions.id"))
    to_institution_id = Column(Integer, ForeignKey("institutions.id"))
    transfer_date = Column(DateTime, default=datetime.utcnow)
    fee = Column(Float, default=0.0)
    status = Column(String, default="APPROVED") # PENDING, APPROVED, REJECTED
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    player = relationship("Player")
    from_institution = relationship("Institution", foreign_keys=[from_institution_id])
    to_institution = relationship("Institution", foreign_keys=[to_institution_id])

class Award(Base):
    """National Honors and Recognition"""
    __tablename__ = "awards"
    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    award_type = Column(String) # POTM, POM, MVP, GOLDEN_BOOT
    season = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    player = relationship("Player")
    competition = relationship("Competition")

class PlayerVote(Base):
    """Human & Statistical Voting System"""
    __tablename__ = "player_votes"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    voter_id = Column(Integer, ForeignKey("users.id"))
    voter_role = Column(String) # FERWAFA, COACH, SCOUT
    award_category = Column(String) # MVP, POTM, YOUNG_TALENT, TOP_SCORER
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=True)
    ai_validation_score = Column(Float, default=0.0) # Backed by statistical merit
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    player = relationship("Player")

# --- RESTORED MODELS ---

class Competition(Base):
    """National Official Competition Ledger"""
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    type = Column(String) # LEAGUE, CUP, YOUTH, ACADEMY, SCHOOL
    season = Column(String) # e.g., "2026/2027"
    category = Column(String) # U15, U17, Senior, etc
    rules = Column(Text, nullable=True) # Custom competition rules
    age_limit = Column(Integer, nullable=True)
    status = Column(String, default="ACTIVE") # ACTIVE, SUSPENDED, COMPLETED
    created_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

    matches = relationship("Match", back_populates="competition")

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=True)
    home_team_id = Column(Integer, ForeignKey("institutions.id"))
    away_team_id = Column(Integer, ForeignKey("institutions.id"))
    stadium = Column(String)
    match_date = Column(DateTime)
    status = Column(String, default="SCHEDULED") # SCHEDULED, LIVE, PAUSED, COMPLETED
    round = Column(String)
    is_finalized = Column(Boolean, default=False) # True when history is locked
    score_home = Column(Integer, default=0)
    score_away = Column(Integer, default=0)
    
    # --- SECURE CREDENTIALS ---
    match_token = Column(String, unique=True, index=True, nullable=True)
    api_key = Column(String, unique=True, index=True, nullable=True)
    session_status = Column(String, default="INACTIVE") # INACTIVE, WAITING, ACTIVE, EXPIRED
    expires_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    # existing columns above remain unchanged    
    opponent_name = Column(String)
    competition_type = Column(String, default="League")
    kit_home_color = Column(String, default="#FF0000")
    kit_home_shorts_color = Column(String, default="#FFFFFF")
    kit_home_socks_color = Column(String, default="#FFFFFF")
    kit_away_color = Column(String, default="#0000FF")
    kit_away_shorts_color = Column(String, default="#FFFFFF")
    kit_away_socks_color = Column(String, default="#FFFFFF")
    division_name = Column(String)
    formation = Column(String, default="4-3-3")
    
    # --- Location Intelligence ---
    location_id = Column(String)
    region = Column(String)
    district = Column(String)
    venue_quality = Column(Float, default=1.0) # 1.0 to 5.0

    competition = relationship("Competition", back_populates="matches")
    events = relationship("MatchEvent", back_populates="match", cascade="all, delete-orphan")
    ai_analysis = relationship("AIAnalysis", back_populates="match", cascade="all, delete-orphan")
    squad = relationship("MatchSquad", back_populates="match", cascade="all, delete-orphan")
    session = relationship("MatchSession", back_populates="match", uselist=False, cascade="all, delete-orphan")

class DisciplinaryRecord(Base):
    """Permanent National Record of Infractions"""
    __tablename__ = "disciplinary_history"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    card_type = Column(String) # YELLOW, RED
    description = Column(String) # reason
    minute = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class MatchEvent(Base):
    __tablename__ = "match_events"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"))
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))

    event_type = Column(String, nullable=False) # goal, card, pass, movement
    timestamp_match = Column(Integer)
    x_pos = Column(Float)
    y_pos = Column(Float)
    value = Column(Float)
    ai_confidence = Column(Float, nullable=True)
    ocr_conf = Column(Float, nullable=True)
    det_conf = Column(Float, nullable=True)
    track_conf = Column(Float, nullable=True)
    is_confirmed = Column(Boolean, default=True) # True for manual/auto-confirmed, False for AI-low-conf
    source = Column(String, default="manual") # 'ai', 'manual', 'correction'
    is_voided = Column(Boolean, default=False) # True if this event was superseded by a correction
    parent_event_id = Column(Integer, ForeignKey("match_events.id"), nullable=True) # Links correction to original
    original_ai_payload = Column(String, nullable=True) # JSON dump of raw AI data if corrected
    source_event_id = Column(String, index=True, nullable=True) # For duplicate prevention
    server_timestamp = Column(DateTime, default=datetime.utcnow) # Authoritative server clock
    
    # --- Immutable Ledger & Audit ---
    editor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    audit_reason = Column(String, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    editor = relationship("User", foreign_keys=[editor_id])

    match = relationship("Match", back_populates="events")
    player = relationship("Player", cascade="all, delete")

class PlayerStat(Base):
    __tablename__ = "player_stats"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"))
    speed = Column(Float, default=0.0)
    distance = Column(Float, default=0.0)
    rating = Column(Float, default=0.0)
    assists = Column(Integer, default=0)
    shots = Column(Integer, default=0)
    passes = Column(Integer, default=0)
    tackles = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    
    # --- Advanced Performance Analytics ---
    xg = Column(Float, default=0.0) # Expected Goals
    pass_accuracy = Column(Float, default=0.0)
    defensive_actions = Column(Integer, default=0)
    sprint_distance = Column(Float, default=0.0)
    stamina_index = Column(Float, default=1.0)
    tactical_rating = Column(Float, default=0.0)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

    player = relationship("Player", back_populates="stats")

class AIAnalysis(Base):
    __tablename__ = "ai_analysis"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"))
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"))
    star_rating = Column(Float) # 3.5 - 9.5
    analysis_notes = Column(Text)
    last_updated = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

    player = relationship("Player", back_populates="ai_rankings")
    match = relationship("Match", back_populates="ai_analysis")

class MatchAnalytics(Base):
    """Historical snapshots for trend graphs"""
    __tablename__ = "match_analytics"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    minute = Column(Integer)
    possession_home = Column(Float)
    possession_away = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class Fixture(Base):
    __tablename__ = "fixtures"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    status = Column(String, default="PENDING")
    suggested_by_ai = Column(Boolean, default=True)
    approved_by_ferwafa = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"))
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class LiveSession(Base):
    __tablename__ = "live_sessions"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    live_link = Column(String, unique=True, index=True)
    status = Column(String, default="INACTIVE")
    websocket_endpoint = Column(String)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class SystemActivity(Base):
    __tablename__ = "system_activity"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False) # e.g., "USER_CREATED", "DATABASE_BACKUP"
    description = Column(Text)
    actor_email = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class SystemError(Base):
    __tablename__ = "system_errors"
    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String) # e.g., "SQLAlchemyError", "ValueError"
    message = Column(Text)
    traceback = Column(Text)
    request_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class MatchSquad(Base):
    """Links players to a match session (18-man squad with positions)"""
    __tablename__ = "match_squads"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    role = Column(String, default="bench")  # "starting", "bench"
    position = Column(String)               # GK, CB, CM, ST, etc.
    jersey_number = Column(Integer)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

    match = relationship("Match", back_populates="squad")
    player = relationship("Player", cascade="all, delete")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False) # GENERATION, CONNECTION, REJECTION, EXPIRATION, CLOSURE
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=True)
    description = Column(Text)
    actor_email = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class TrackingFrame(Base):
    """Raw high-frequency tracking data for analysis and replay"""
    __tablename__ = "tracking_frames"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True) # Null for ball
    tracking_id = Column(Integer) # ID from ByteTrack
    x_pos = Column(Float)
    y_pos = Column(Float)
    velocity = Column(Float, default=0.0)
    direction = Column(Float, default=0.0)
    is_ball = Column(Boolean, default=False)
    timestamp_match = Column(Integer) # In-match milliseconds
    server_timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class TacticalSnapshot(Base):
    """Team-level tactical analytics generated every minute or event"""
    __tablename__ = "tactical_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    minute = Column(Integer)
    possession_home = Column(Float)
    possession_away = Column(Float)
    home_formation = Column(String) # e.g. "4-3-3"
    away_formation = Column(String)
    home_compactness = Column(Float)
    away_compactness = Column(Float)
    attacking_intensity = Column(Float)
    pressure_zone = Column(String) # "high", "medium", "low"
    timestamp = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class MatchSession(Base):
    """Tracks AI Machine connection state per match token"""
    __tablename__ = "match_sessions"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True)
    match_token = Column(String, unique=True, index=True)
    ai_connected = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    match = relationship("Match", back_populates="session")

# =====================================================
# SUPERADMIN INFRASTRUCTURE MODELS
# =====================================================

class APIKey(Base):
    """Infrastructure-level API access keys"""
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    service_name = Column(String, nullable=False) # e.g. "AI_NODE_1", "EXTERNAL_SCOUT_API"
    owner_email = Column(String)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=1000) # req/hour
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class BlockedIP(Base):
    """Security Layer: IP Blacklist"""
    __tablename__ = "blocked_ips"
    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, unique=True, index=True, nullable=False)
    reason = Column(String)
    blocked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False)

class SecurityRule(Base):
    """Infrastructure Security Thresholds (DDoS, Rate Limits)"""
    __tablename__ = "security_rules"
    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String, unique=True, index=True)
    threshold = Column(Integer) # Value for the rule
    is_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InfrastructureLog(Base):
    """Deep Immutable Technical Logs (Forensic Audit)"""
    __tablename__ = "infrastructure_logs"
    id = Column(Integer, primary_key=True, index=True)
    service = Column(String, nullable=False) # API, AI, DB, SECURITY, AUTH
    action = Column(String, nullable=False)
    severity = Column(String, default="INFO") # INFO, WARNING, CRITICAL
    actor_id = Column(String) # Service ID or User Email
    payload_hash = Column(String) # Hash of the request payload for tamper-proofing
    description = Column(Text)
    status_code = Column(Integer)
    request_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    request_path = Column(String)
    response_code = Column(Integer)
    response_body = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
