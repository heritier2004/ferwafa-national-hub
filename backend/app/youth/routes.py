from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from backend.app.config.database import get_db
from backend.app.database.models import Player, Institution, Match, PlayerStat, MatchSquad
from backend.app.auth.dependencies import get_current_user, RoleChecker
from backend.app.utils.crud import CrudMixin, transactional
import os, uuid, shutil, random
from datetime import datetime

router = APIRouter(prefix="/api/youth", tags=["youth"])

# RBAC: Only School and Academy roles can access these endpoints
youth_access = RoleChecker(["SCHOOL", "ACADEMY", "FERWAFA"])

@router.post("/player/create", dependencies=[Depends(youth_access)])
def create_youth_player(data: dict, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Player registration with mandatory photo check."""
    if not data.get("photo_url"):
        raise HTTPException(status_code=400, detail="Player photo is mandatory for youth registration.")
    
    inst_id = current_user.get("institution_id")
    if not inst_id and current_user["role"] != "FERWAFA":
        raise HTTPException(status_code=403, detail="User not linked to any institution.")

    # Use specified institution_id if FERWAFA, else use current_user's
    target_inst_id = data.get("institution_id", inst_id) if current_user["role"] == "FERWAFA" else inst_id
    
    inst = db.query(Institution).filter(Institution.id == target_inst_id).first()
    
    player_payload = {
        "name": data.get("name"),
        "position": data.get("position"),
        "age": data.get("age"),
        "jersey_number": data.get("jersey_number"),
        "institution_id": target_inst_id,
        "photo_url": data.get("photo_url"),
        "player_code": f"YTH-{random.randint(10000, 99999)}",
        "location_id": inst.code if inst else None,
        "region": inst.province if inst else None,
        "district": inst.district if inst else None
    }
    
    new_player = CrudMixin.create(Player, db, player_payload, actor_id=current_user["id"])
    return new_player

@router.get("/player/list", dependencies=[Depends(youth_access)])
def list_youth_players(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """List players with location-based enforcement."""
    inst_id = current_user.get("institution_id")
    if current_user["role"] == "FERWAFA":
        return db.query(Player).filter(Player.is_deleted == False).all()
    
    return db.query(Player).filter(Player.institution_id == inst_id, Player.is_deleted == False).all()

@router.get("/player/{id}", dependencies=[Depends(youth_access)])
def get_youth_player(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    player = db.query(Player).filter(Player.id == id, Player.is_deleted == False).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Location enforcement
    if current_user["role"] != "FERWAFA" and player.institution_id != current_user["institution_id"]:
        raise HTTPException(status_code=403, detail="Access denied to players outside your institution.")
    
    return player

@router.get("/matches/local", dependencies=[Depends(youth_access)])
def get_local_matches(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Fetch matches in the same District/Province."""
    inst_id = current_user.get("institution_id")
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: return []
    
    return db.query(Match).filter(
        (Match.district == inst.district) | (Match.region == inst.province),
        Match.is_deleted == False
    ).all()

@router.post("/team/lineup", dependencies=[Depends(youth_access)])
def set_youth_lineup(match_id: int, players: List[dict], db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Set the squad for a specific youth fixture."""
    with transactional(db):
        # 1. Clear existing squad for this match (Hard delete as lineups are transient until match starts)
        db.execute(text("DELETE FROM match_squads WHERE match_id = :mid"), {"mid": match_id})
        
        # 2. Assign new players
        for p in players:
            payload = {
                "match_id": match_id,
                "player_id": p["player_id"],
                "role": p.get("role", "bench"),
                "jersey_number": p.get("jersey"),
                "position": p.get("position")
            }
            # Use CrudMixin for auditing the lineup change
            CrudMixin.create(MatchSquad, db, payload, actor_id=current_user["id"])
            
    return {"status": "Youth lineup saved and audited."}
