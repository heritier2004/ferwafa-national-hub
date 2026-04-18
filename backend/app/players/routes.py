from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.players.service import PlayerService
from pydantic import BaseModel

router = APIRouter(prefix="/players", tags=["players"])

class PlayerBase(BaseModel):
    name: str
    position: str
    institution_id: int

@router.get("/")
def list_players(institution_id: int = None, db: Session = Depends(get_db)):
    return PlayerService.get_all_players(db, institution_id)

@router.post("/")
def add_player(player: PlayerBase, db: Session = Depends(get_db)):
    code = PlayerService.generate_player_code(db, player.institution_id)
    return PlayerService.create_player(db, {**player.dict(), "player_code": code})
