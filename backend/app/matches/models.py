from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from backend.app.config.database import Base
from datetime import datetime

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    home_team_id = Column(Integer, ForeignKey("institutions.id"))
    away_team_id = Column(Integer, ForeignKey("institutions.id"))
    stadium = Column(String)
    match_date = Column(DateTime)
    status = Column(String, default="SCHEDULED") # SCHEDULED, LIVE, COMPLETED
    round = Column(String)
    score_home = Column(Integer, default=0)
    score_away = Column(Integer, default=0)

    events = relationship("MatchEvent", back_populates="match")
    ai_analysis = relationship("AIAnalysis", back_populates="match")

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
