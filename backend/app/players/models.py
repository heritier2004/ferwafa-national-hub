from sqlalchemy import Column, Integer, String, ForeignKey, Float, Date, Text
from sqlalchemy.orm import relationship
from backend.app.config.database import Base

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
