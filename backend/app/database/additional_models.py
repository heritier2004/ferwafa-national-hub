from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.config.database import Base

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
