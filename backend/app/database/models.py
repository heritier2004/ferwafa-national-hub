from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, Date, Text
from sqlalchemy.orm import relationship
from backend.app.config.database import Base
from datetime import datetime

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
    
    players = relationship("Player", back_populates="institution")

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"))
    player_code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    position = Column(String)
    height = Column(Float)
    weight = Column(Float)
    nationality = Column(String, default="Rwandan")
    date_of_birth = Column(Date)
    photo_url = Column(Text)

    institution = relationship("Institution", back_populates="players")
    stats = relationship("PlayerStat", back_populates="player")
    ai_rankings = relationship("AIAnalysis", back_populates="player")

class Competition(Base):
    """National Official Competition Ledger"""
    __tablename__ = "competitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    type = Column(String) # LEAGUE, CUP, YOUTH, ACADEMY
    season = Column(String) # e.g., "2026/2027"
    age_limit = Column(Integer, nullable=True)
    status = Column(String, default="ACTIVE") # ACTIVE, SUSPENDED, COMPLETED
    created_at = Column(DateTime, default=datetime.utcnow)

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
    # AI Match Control fields
    api_key = Column(String, unique=True, index=True)
    match_token = Column(String, unique=True, index=True)
    opponent_name = Column(String)
    competition_type = Column(String, default="League")
    kit_home_color = Column(String, default="#FF0000")
    kit_home_socks_color = Column(String, default="#FFFFFF")
    kit_away_color = Column(String, default="#0000FF")
    kit_away_socks_color = Column(String, default="#FFFFFF")

    competition = relationship("Competition", back_populates="matches")
    events = relationship("MatchEvent", back_populates="match")
    ai_analysis = relationship("AIAnalysis", back_populates="match")
    squad = relationship("MatchSquad", back_populates="match")
    session = relationship("MatchSession", back_populates="match", uselist=False)

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

class MatchEvent(Base):
    __tablename__ = "match_events"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
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

    match = relationship("Match", back_populates="events")

class PlayerStat(Base):
    __tablename__ = "player_stats"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    match_id = Column(Integer, ForeignKey("matches.id"))
    speed = Column(Float, default=0.0)
    distance = Column(Float, default=0.0)
    rating = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    player = relationship("Player", back_populates="stats")

class AIAnalysis(Base):
    __tablename__ = "ai_analysis"
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"))
    match_id = Column(Integer, ForeignKey("matches.id"))
    star_rating = Column(Float) # 3.5 - 9.5
    analysis_notes = Column(Text)
    last_updated = Column(DateTime, default=datetime.utcnow)

    player = relationship("Player", back_populates="ai_rankings")
    match = relationship("Match", back_populates="ai_analysis")

class Fixture(Base):
    __tablename__ = "fixtures"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    status = Column(String, default="PENDING")
    suggested_by_ai = Column(Boolean, default=True)
    approved_by_ferwafa = Column(Boolean, default=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"))

class LiveSession(Base):
    __tablename__ = "live_sessions"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    live_link = Column(String, unique=True, index=True)
    status = Column(String, default="INACTIVE")
    websocket_endpoint = Column(String)

class SystemActivity(Base):
    __tablename__ = "system_activity"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False) # e.g., "USER_CREATED", "DATABASE_BACKUP"
    description = Column(Text)
    actor_email = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class SystemError(Base):
    __tablename__ = "system_errors"
    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String) # e.g., "SQLAlchemyError", "ValueError"
    message = Column(Text)
    traceback = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

# =====================================================
# MATCH CONTROL SYSTEM MODELS
# =====================================================

class MatchSquad(Base):
    """Links players to a match session (18-man squad with positions)"""
    __tablename__ = "match_squads"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    player_id = Column(Integer, ForeignKey("players.id"))
    role = Column(String, default="bench")  # "starting", "bench"
    position = Column(String)               # GK, CB, CM, ST, etc.
    jersey_number = Column(Integer)

    match = relationship("Match", back_populates="squad")
    player = relationship("Player")

class MatchSession(Base):
    """Tracks AI Machine connection state per match token"""
    __tablename__ = "match_sessions"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), unique=True)
    match_token = Column(String, unique=True, index=True)
    ai_connected = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="session")

class SystemSetting(Base):
    """Global system configuration (Footers, Branding, Maintenance Mode)"""
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text)
    description = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
