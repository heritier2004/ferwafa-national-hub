from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import Institution, Match, Player, AIAnalysis, User, SystemActivity, MatchSession, Competition
from backend.app.auth.security import get_password_hash
from sqlalchemy import text
import random
from datetime import datetime, timedelta

from backend.app.auth.dependencies import get_current_user, RoleChecker
from backend.app.utils.crud import CrudMixin, transactional
from pydantic import BaseModel
from typing import List, Optional

class FixtureGenerateRequest(BaseModel):
    institution_ids: List[int]
    start_date: str
    end_date: str
    division_name: str

class InstitutionCreate(BaseModel):
    name: str
    type: str # club, school, academy, scout_org, regional_fa
    code: str
    stadium_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    sector: Optional[str] = None
    cell: Optional[str] = None
    logo_url: Optional[str] = None
    has_floodlights: bool = False
    pitch_type: str = "Natural Grass"
    capacity: int = 5000
    contact: Optional[str] = None

class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    stadium_name: Optional[str] = None
    capacity: Optional[int] = None
    pitch_type: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    sector: Optional[str] = None
    cell: Optional[str] = None
    contact: Optional[str] = None
    is_active: Optional[bool] = None

class OnboardRequest(BaseModel):
    name: str
    type: str # club, school, academy
    code: str
    admin_email: str
    admin_name: str
    admin_pass: str
    stadium_name: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    sector: Optional[str] = None
    cell: Optional[str] = None
    contact: Optional[str] = None
    logo_url: Optional[str] = None
    capacity: int = 5000

router = APIRouter(
    prefix="/api/ferwafa", 
    tags=["ferwafa"]
)

@router.post("/entities/create", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def create_entity(req: InstitutionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if req.type not in ["club", "school", "academy", "scout_org", "regional_fa"]:
        raise HTTPException(status_code=400, detail="Invalid entity type. Must be club, school, academy, scout_org, or regional_fa")
    
    try:
        new_inst = CrudMixin.create(Institution, db, req.dict(), actor_id=current_user["id"])
        return {"message": f"{req.type.capitalize()} '{req.name}' registered with full hosting profile.", "id": new_inst.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/entities")
def list_entities(type: Optional[str] = None, db: Session = Depends(get_db)):
    """List all institutions with optional type filter (club, academy, school)"""
    q = db.query(Institution).filter(Institution.is_deleted == False)
    if type:
        q = q.filter(Institution.type == type.lower())
    return q.order_by(Institution.id.desc()).all()

@router.get("/entities/all")
def get_entities(db: Session = Depends(get_db)):
    """Alias for /entities — returns all institutions"""
    return db.query(Institution).filter(Institution.is_deleted == False).order_by(Institution.id.desc()).all()

@router.post("/entities/{inst_id}/purge", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def purge_entity(inst_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    
    name = inst.name
    try:
        # Use a transaction to ensure atomic purge
        with transactional(db):
            # 1. Clean up dependencies that might not have ON DELETE CASCADE or need manual handling
            db.execute(text("DELETE FROM transfers WHERE from_institution_id = :id OR to_institution_id = :id"), {"id": inst_id})
            db.execute(text("DELETE FROM matches WHERE home_team_id = :id OR away_team_id = :id"), {"id": inst_id})
            db.execute(text("DELETE FROM players WHERE institution_id = :id"), {"id": inst_id})
            db.execute(text("DELETE FROM users WHERE institution_id = :id"), {"id": inst_id})
            db.execute(text("DELETE FROM attendance WHERE institution_id = :id"), {"id": inst_id})
            db.execute(text("DELETE FROM training_sessions WHERE institution_id = :id"), {"id": inst_id})
            
            # 2. Final removal
            db.execute(text("DELETE FROM institutions WHERE id = :id"), {"id": inst_id})
            
            # 3. Log the purge action for forensics
            from backend.app.database.models import AuditLog
            log = AuditLog(
                actor_email=current_user["username"],
                action="PURGE_ENTITY",
                description=f"PERMANENT REMOVAL: Institution '{name}' (ID: {inst_id}) and all associated records purged by National Authority.",
                timestamp=datetime.utcnow()
            )
            db.add(log)
            
        return {"message": f"Entity '{name}' and all associated data permanently purged from National Hub."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Purge failed: {str(e)}")

@router.put("/entities/{inst_id}/toggle-status", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def toggle_institution_status(inst_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    
    new_status = not inst.is_active
    CrudMixin.update(Institution, db, inst_id, {"is_active": new_status}, actor_id=current_user["id"])
    
    status_label = "ACTIVE" if new_status else "PAUSED"
    return {"message": f"Institution {inst.name} is now {status_label}.", "is_active": new_status}

@router.delete("/entities/{inst_id}", dependencies=[Depends(RoleChecker(["FERWAFA", "SUPER_ADMIN"]))])
def safe_delete_entity(inst_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    
    inst.is_deleted = True
    inst.status = "DELETED"
    inst.is_active = False
    
    # Cascade soft delete to users associated with this institution to prevent future logins
    users = db.query(User).filter(User.institution_id == inst_id).all()
    for u in users:
        u.is_active = False
        u.is_deleted = True
        
    db.commit()
    
    return {"message": f"Institution '{inst.name}' has been safely deleted."}

@router.get("/entities/pending", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_pending_entities(db: Session = Depends(get_db)):
    institutions = db.query(Institution).filter(Institution.status == "PENDING").order_by(Institution.id.desc()).all()
    results = []
    for inst in institutions:
        # Fetch the user associated with this institution to review admin info
        user = db.query(User).filter(User.institution_id == inst.id).first()
        inst_data = {
            "id": inst.id,
            "name": inst.name,
            "type": inst.type,
            "code": inst.code,
            "contact": inst.contact,
            "province": inst.province,
            "district": inst.district,
            "sector": inst.sector,
            "cell": inst.cell,
            "stadium_name": inst.stadium_name,
            "logo_url": inst.logo_url,
            "status": inst.status,
            "admin_email": user.email if user else None,
            "admin_name": user.full_name if user else None
        }
        results.append(inst_data)
    return results

@router.get("/entities/{inst_id}", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_entity_details(inst_id: int, db: Session = Depends(get_db)):
    """Fetch all details of a single institution, including admin user info for review."""
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    
    user = db.query(User).filter(User.institution_id == inst.id).first()
    
    return {
        "id": inst.id,
        "name": inst.name,
        "type": inst.type,
        "code": inst.code,
        "contact": inst.contact,
        "province": inst.province,
        "district": inst.district,
        "sector": inst.sector,
        "cell": inst.cell,
        "stadium_name": inst.stadium_name,
        "logo_url": inst.logo_url,
        "status": inst.status,
        "is_active": inst.is_active,
        "admin_email": user.email if user else None,
        "admin_name": user.full_name if user else None
    }

class ApprovalRequest(BaseModel):
    status: str # APPROVED, REJECTED, REQUEST_INFO

@router.put("/entities/{inst_id}/status", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def update_institution_status(inst_id: int, req: ApprovalRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    
    if req.status not in ["APPROVED", "REJECTED", "REQUEST_INFO"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    try:
        inst.status = req.status
        user = db.query(User).filter(User.institution_id == inst_id).first()
        
        raw_key = None
        if req.status == "APPROVED":
            inst.is_active = True
            if user:
                user.is_active = True
                
            # Generate API key for Match Control
            from backend.app.database.models import APIKey
            import uuid
            raw_key = uuid.uuid4().hex
            new_key = APIKey(
                key_hash=get_password_hash(raw_key),
                service_name=f"{inst.type.upper()}_MATCH_NODE",
                owner_email=user.email if user else "unknown"
            )
            db.add(new_key)
            
        elif req.status == "REJECTED":
            inst.is_active = False
            if user:
                user.is_active = False
                
        db.commit()
        if req.status == "APPROVED" and raw_key:
            return {"message": f"Institution {inst.name} APPROVED. System access granted.", "raw_api_key": raw_key}
            
        return {"message": f"Institution {inst.name} marked as {req.status}."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during status update: {str(e)}")

# 🏃 PLAYER REGISTRY MANAGEMENT (CLUB HUD)
@router.post("/players", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def create_player(req: PlayerCreateReq, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    p_code = f"PLY-{random.randint(10000, 99999)}"
    dob = None
    if req.date_of_birth:
        try: dob = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
        except: pass

    payload = req.dict()
    payload["player_code"] = p_code
    payload["date_of_birth"] = dob
    
    new_p = CrudMixin.create(Player, db, payload, actor_id=current_user["id"])
    return {"message": f"Player {req.name} registered to squad perfectly.", "id": new_p.id}

@router.get("/players/{institution_id}", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def get_club_players(institution_id: int, db: Session = Depends(get_db)):
    return db.query(Player).filter(Player.institution_id == institution_id).order_by(Player.jersey_number.asc()).all()

@router.put("/players/{player_id}", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def update_player(player_id: int, name: str = None, position: str = None, jersey_number: int = None, nationality: str = None, date_of_birth: str = None, photo_url: str = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    payload = {}
    if name: payload["name"] = name
    if position: payload["position"] = position
    if jersey_number is not None: payload["jersey_number"] = jersey_number
    if nationality: payload["nationality"] = nationality
    if photo_url: payload["photo_url"] = photo_url
    if date_of_birth:
        try: payload["date_of_birth"] = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except: pass
        
    try:
        updated = CrudMixin.update(Player, db, player_id, payload, actor_id=current_user["id"])
        return {"message": f"Player profile for {updated.name} updated successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.delete("/players/{player_id}", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def delete_player(player_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        CrudMixin.soft_delete(Player, db, player_id, actor_id=current_user["id"])
        return {"message": "Player released from squad."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.get("/matches/{match_id}/squad", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def get_match_squad(match_id: int, db: Session = Depends(get_db)):
    from backend.app.database.models import MatchSquad
    squad = db.query(MatchSquad).filter(MatchSquad.match_id == match_id).all()
    results = []
    for s in squad:
        player = db.query(Player).filter(Player.id == s.player_id).first()
        results.append({
            "player_id": s.player_id,
            "player_name": player.name if player else "Unknown",
            "jersey_number": s.jersey_number,
            "role": s.role,
            "position": s.position
        })
    return results

# 🏆 ELITE ROUND-ROBIN MIXER (v5.0 - Governance Spec)
@router.post("/fixtures/auto-generate", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def auto_generate_league(req: FixtureGenerateRequest, db: Session = Depends(get_db)):
    institution_ids = req.institution_ids
    start_date = req.start_date
    division_name = req.division_name
    
    teams = db.query(Institution).filter(Institution.id.in_(institution_ids)).all()
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams")

    # 🏛️ CREATE OFFICIAL COMPETITION SCABBARD
    comp = db.query(Competition).filter(Competition.name == division_name).first()
    if not comp:
        comp = Competition(name=division_name, type="LEAGUE", category="Senior", season="2026", status="ACTIVE")
        db.add(comp)
        db.flush()

    # Round Robin Circle Algorithm
    if len(teams) % 2 != 0:
        teams.append(None)

    random.shuffle(teams)
    num_rounds = len(teams) - 1
    matches_per_round = len(teams) // 2

    base_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    matches_created = 0
    t_list = list(teams)

    for r in range(num_rounds):
        match_week_date = base_date + timedelta(days=r * 7) # Weekly cadence by default
        week_label = f"Match Week {r+1}"

        for m in range(matches_per_round):
            home = t_list[m]
            away = t_list[len(t_list) - 1 - m]

            if home and away:
                kickoff_hour = 15
                if home.has_floodlights:
                    kickoff_hour = random.choice([15, 18, 20])
                
                match_time = match_week_date.replace(hour=kickoff_hour, minute=0)

                new_match = Match(
                    competition_id=comp.id, # 🛡️ GOVERNANCE LINK
                    home_team_id=home.id,
                    away_team_id=away.id,
                    stadium=home.stadium_name or home.location,
                    match_date=match_time,
                    round=week_label,
                    status="SCHEDULED"
                )
                db.add(new_match)
                db.flush() 

                matches_created += 1
                
                log = SystemActivity(
                    action="LEAGUE_MIXER", 
                    description=f"Strategic Mix {division_name} - Week {r+1}: {home.name} vs {away.name}", 
                    actor_email="FERWAFA_HQ"
                )
                db.add(log)

        t_list = [t_list[0]] + [t_list[-1]] + t_list[1:-1]

    db.commit()
    return {"message": f"Successfully generated {matches_created} professional fixtures for '{division_name}' linked to National Competition #{comp.id}.", "competition_id": comp.id}

@router.get("/competitions/all")
def get_competitions(db: Session = Depends(get_db)):
    return db.query(Competition).all()

@router.put("/entities/{inst_id}")
def update_entity(inst_id: int, req: InstitutionUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        updated = CrudMixin.update(Institution, db, inst_id, req.dict(exclude_unset=True), actor_id=current_user["id"])
        return {"message": f"Updated {updated.name} successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.get("/fixtures/all")
def get_all_matches(db: Session = Depends(get_db)):
    # Standard join to get team names
    matches = db.query(Match).order_by(Match.match_date.asc()).all()
    results = []
    for m in matches:
        home = db.query(Institution).filter(Institution.id == m.home_team_id).first()
        away = db.query(Institution).filter(Institution.id == m.away_team_id).first()
        results.append({
            "id": m.id,
            "home": home.name if home else "Unknown",
            "away": away.name if away else "Unknown",
            "date": m.match_date.strftime("%Y-%m-%d %H:%M"),
            "stadium": m.stadium,
            "status": m.status,
            "round": m.round or "General",
            "division": m.division_name or "National"
        })
    return results

@router.get("/fixtures/mine/{institution_id}", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def get_club_matches(institution_id: int, db: Session = Depends(get_db)):
    matches = db.query(Match).filter(
        (Match.home_team_id == institution_id) | (Match.away_team_id == institution_id)
    ).order_by(Match.match_date.asc()).all()
    
    results = []
    for m in matches:
        home = db.query(Institution).filter(Institution.id == m.home_team_id).first()
        away = db.query(Institution).filter(Institution.id == m.away_team_id).first()
        results.append({
            "id": m.id,
            "home": home.name if home else "Unknown",
            "away": away.name if away else "Unknown",
            "date": m.match_date.strftime("%Y-%m-%d %H:%M"),
            "stadium": m.stadium,
            "status": m.status,
            "round": m.round or "General",
            "is_home": m.home_team_id == institution_id
        })
    return results

# 🔐 NATIONAL USER MANAGEMENT
@router.post("/users/manage", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def create_member_user(email: str, full_name: str, password: str, role: str, institution_id: int = 0, photo_url: str = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    payload = {
        "email": email, "full_name": full_name, "password_hash": get_password_hash(password),
        "role": role, "institution_id": institution_id, "photo_url": photo_url
    }
    try:
        new_user = CrudMixin.create(User, db, payload, actor_id=current_user["id"])
        return {"message": f"Login created for {role} Official of institution #{institution_id}", "id": new_user.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/all", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_member_users(db: Session = Depends(get_db)):
    # Return users that are NOT super admins or ferwafa
    return db.query(User, Institution).outerjoin(Institution).filter(User.role.in_(['CLUB', 'SCHOOL', 'ACADEMY', 'SCOUT'])).all()

@router.get("/users/universal", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_universal_ledger(db: Session = Depends(get_db)):
    """Universal oversight for FERWAFA Boss mode"""
    users = db.query(User).filter(User.is_deleted == False).all()
    results = []
    for u in users:
        inst = db.query(Institution).filter(Institution.id == u.institution_id).first() if u.institution_id else None
        results.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "institution": inst.name if inst else "N/A",
            "is_active": u.is_active
        })
    return results

# 🗺️ NATIONAL FOOTBALL INTELLIGENCE HEATMAP
@router.get("/heatmap", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_national_heatmap(province: str = None, district: str = None, db: Session = Depends(get_db)):
    """Returns talent density and academy distribution by region."""
    from sqlalchemy import func
    
    # Base query for talent density
    query = db.query(Player.district, func.count(Player.id).label('player_count'), func.avg(Player.talent_score).label('avg_talent'))
    if province:
        query = query.filter(Player.region == province)
    if district:
        query = query.filter(Player.district == district)
        
    density_data = query.group_by(Player.district).all()
    
    # Base query for academies
    inst_query = db.query(Institution.district, func.count(Institution.id).label('academy_count')).filter(Institution.type == "academy")
    if province:
        inst_query = inst_query.filter(Institution.province == province)
    if district:
        inst_query = inst_query.filter(Institution.district == district)
        
    academy_data = inst_query.group_by(Institution.district).all()
    
    return {
        "density": [{"district": d[0], "count": d[1], "avg_talent": round(d[2] or 0.0, 1)} for d in density_data],
        "academies": [{"district": a[0], "count": a[1]} for a in academy_data]
    }

# 🏆 NATIONAL RANKING SYSTEM
@router.get("/rankings", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_national_rankings(category: str = "academies", db: Session = Depends(get_db)):
    """Automated national rankings based on match performance and AI analytics."""
    if category in ["academies", "schools", "clubs"]:
        # Strip trailing 's' for type matching
        ctype = category[:-1] if category.endswith("s") and category != "clubs" else ("club" if category == "clubs" else category)
        if category == "academies": ctype = "academy"
        
        institutions = db.query(Institution).filter(Institution.type == ctype).order_by(Institution.national_ranking.asc()).limit(20).all()
        return [{"id": i.id, "name": i.name, "ranking": i.national_ranking or 999, "district": i.district} for i in institutions]
        
    elif category == "talents":
        talents = db.query(Player).order_by(Player.potential_score.desc()).limit(20).all()
        return [{"id": p.id, "name": p.name, "potential": p.potential_score, "current": p.talent_score, "institution_id": p.institution_id} for p in talents]
        
    return []

@router.put("/users/{user_id}", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def update_user_authority(user_id: int, full_name: str = None, email: str = None, is_active: bool = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    payload = {}
    if full_name: payload["full_name"] = full_name
    if email: payload["email"] = email
    if is_active is not None: payload["is_active"] = is_active
    
    try:
        updated = CrudMixin.update(User, db, user_id, payload, actor_id=current_user["id"])
        return {"message": f"User {updated.email} updated by National Authority."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.delete("/users/{user_id}", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def delete_user_authority(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        CrudMixin.soft_delete(User, db, user_id, actor_id=current_user["id"])
        return {"message": "User permanently purged from national system."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/onboard/full-node", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def onboard_institutional_node(req: OnboardRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    try:
        with transactional(db):
            # 1. Create Institution
            inst_payload = {
                "name": req.name, "type": req.type, "code": req.code, "stadium_name": req.stadium_name,
                "province": req.province, "district": req.district, "sector": req.sector, "cell": req.cell,
                "contact": req.contact, "logo_url": req.logo_url, "is_active": True, "capacity": req.capacity
            }
            new_inst = CrudMixin.create(Institution, db, inst_payload, actor_id=current_user["id"])
            
            # 2. Create Admin User
            user_payload = {
                "email": req.admin_email, "full_name": req.admin_name, 
                "password_hash": get_password_hash(req.admin_pass), "role": req.type.upper(), 
                "institution_id": new_inst.id, "is_active": True
            }
            new_user = CrudMixin.create(User, db, user_payload, actor_id=current_user["id"])
            
            return {"message": f"Successfully onboarded {req.name} and created {req.admin_name}'s management account.", "id": new_inst.id}
    except Exception as e:
        # Catch integrity errors or other crud failures and return readable message
        error_msg = str(e)
        if "unique constraint" in error_msg.lower():
            if "email" in error_msg.lower():
                error_msg = "ADMIN EMAIL ALREADY REGISTERED: This email is already tied to another institution."
            elif "code" in error_msg.lower():
                error_msg = "FEDERATION CODE CONFLICT: This institutional code is already in use."
        
        raise HTTPException(status_code=400, detail=error_msg)

# 🕵️ NATIONAL SCOUTING INTELLIGENCE (v4.7 - Age Aware)
@router.get("/scouting/top-players")
def get_top_national_talent(institution_type: str = None, max_age: int = None, db: Session = Depends(get_db)):
    """Top talent filtered by institution type (club/school/academy) and age"""
    query = db.query(Player, AIAnalysis).join(AIAnalysis)
    
    if institution_type:
        query = query.join(Institution, Player.institution_id == Institution.id).filter(Institution.type == institution_type)
    
    top_talent = query.order_by(AIAnalysis.star_rating.desc()).limit(50).all()
    
    results = []
    for p, ai in top_talent:
        age = (datetime.now().date() - p.date_of_birth).days // 365 if p.date_of_birth else None
        
        # Age filter
        if max_age and age and age > max_age:
            continue
        
        results.append({
            "id": p.id,
            "name": p.name,
            "stars": ai.star_rating,
            "position": p.position,
            "age": age if age else "N/A",
            "height": p.height,
            "weight": p.weight,
            "nationality": p.nationality,
            "type": p.institution.type if p.institution else "unknown",
            "club": p.institution.name if p.institution else "Free Agent",
            "province": p.institution.province if p.institution else "N/A",
            "photo_url": p.photo_url,
            "notes": ai.analysis_notes
        })
    return results

@router.get("/scouting/by-institution/{inst_id}")
def get_institution_talent(inst_id: int, db: Session = Depends(get_db)):
    """Get all players and their AI ratings for a specific institution"""
    players = db.query(Player).filter(Player.institution_id == inst_id).all()
    results = []
    for p in players:
        ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).order_by(AIAnalysis.star_rating.desc()).first()
        age = (datetime.now().date() - p.date_of_birth).days // 365 if p.date_of_birth else None
        results.append({
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "age": age if age else "N/A",
            "stars": ai.star_rating if ai else 0,
            "photo_url": p.photo_url,
            "height": p.height,
            "weight": p.weight,
        })
    return results

@router.get("/scouting/stats")
def get_scouting_overview(db: Session = Depends(get_db)):
    """Overview stats for the talent intelligence hub"""
    total_players = db.query(Player).count()
    club_players = db.query(Player).join(Institution).filter(Institution.type == 'club').count()
    school_players = db.query(Player).join(Institution).filter(Institution.type == 'school').count()
    academy_players = db.query(Player).join(Institution).filter(Institution.type == 'academy').count()
    rated_players = db.query(AIAnalysis).count()
    
    return {
        "total_players": total_players,
        "club_players": club_players,
        "school_players": school_players,
        "academy_players": academy_players,
        "rated_players": rated_players,
        "clubs": db.query(Institution).filter(Institution.type == 'club').count(),
        "schools": db.query(Institution).filter(Institution.type == 'school').count(),
        "academies": db.query(Institution).filter(Institution.type == 'academy').count(),
    }

@router.get("/fixtures/history")
def get_match_history(db: Session = Depends(get_db)):
    # Return only completed matches for history tracking
    matches = db.query(Match).filter(Match.status == "COMPLETED").order_by(Match.match_date.desc()).all()
    results = []
    for m in matches:
        home = db.query(Institution).filter(Institution.id == m.home_team_id).first()
        away = db.query(Institution).filter(Institution.id == m.away_team_id).first()
        results.append({
            "id": m.id,
            "home": home.name if home else "Unknown",
            "away": away.name if away else "Unknown",
            "score": f"{m.score_home} - {m.score_away}",
            "date": m.match_date.strftime("%Y-%m-%d"),
            "stadium": m.stadium,
            "is_finalized": m.is_finalized
        })
    return results

@router.post("/fixtures/{match_id}/approve", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def approve_match_record(match_id: int, db: Session = Depends(get_db)):
    """FERWAFA official approval of match results to lock history"""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match: raise HTTPException(status_code=404, detail="Match not found")
    
    if match.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Match must be COMPLETED before approval")
        
    match.is_finalized = True
    db.commit()
    return {"message": "Match official record approved and locked."}

# 📝 ATTENDANCE TRACKING (TRAINING HUB)
@router.post("/attendance", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCHOOL", "ACADEMY"]))])
def record_attendance(institution_id: int, player_id: int, status: str, notes: str = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from backend.app.database.models import Attendance
    payload = {
        "institution_id": institution_id,
        "player_id": player_id,
        "status": status,
        "notes": notes,
        "date": datetime.utcnow().date()
    }
    CrudMixin.create(Attendance, db, payload, actor_id=current_user["id"])
    return {"message": "Attendance recorded for the cycle."}

@router.get("/attendance/{institution_id}")
def get_attendance(institution_id: int, date: str = None, db: Session = Depends(get_db)):
    from backend.app.database.models import Attendance
    query = db.query(Attendance).filter(Attendance.institution_id == institution_id)
    if date:
        query = query.filter(Attendance.date == datetime.strptime(date, "%Y-%m-%d").date())
    return query.all()

# 🕵️ FORENSIC NATIONAL OVERSIGHT
@router.get("/activity/global", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_global_forensics(db: Session = Depends(get_db)):
    # Monitor everything happened in the system
    return db.query(SystemActivity).order_by(SystemActivity.timestamp.desc()).limit(50).all()

# 🗄️ NATIONAL DATABASE EXPLORER
@router.get("/db/browse/{table_name}", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def browse_national_database(table_name: str, db: Session = Depends(get_db)):
    """Secure database browsing for FERWAFA National Authority"""
    SAFE_TABLES = {
        "players": Player,
        "institutions": Institution,
        "matches": Match,
        "users": User,
        "system_activity": SystemActivity,
    }
    
    if table_name not in SAFE_TABLES:
        raise HTTPException(status_code=403, detail=f"Access denied to table '{table_name}'")
    
    model = SAFE_TABLES[table_name]
    rows = db.query(model).limit(200).all()
    
    # Convert ORM objects to dicts
    results = []
    for row in rows:
        d = {}
        for col in row.__table__.columns:
            val = getattr(row, col.name)
            if hasattr(val, 'isoformat'):
                val = val.isoformat()
            d[col.name] = val
        results.append(d)
    
    return {"table": table_name, "count": len(results), "rows": results}

# 🗓️ SEASON MANAGEMENT
@router.get("/seasons/all", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_seasons(db: Session = Depends(get_db)):
    from backend.app.database.models import Season
    return db.query(Season).order_by(Season.start_date.desc()).all()

@router.post("/seasons/create", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def create_season(name: str, start_date: str, end_date: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from backend.app.database.models import Season
    payload = {
        "name": name,
        "start_date": datetime.strptime(start_date, "%Y-%m-%d").date(),
        "end_date": datetime.strptime(end_date, "%Y-%m-%d").date()
    }
    new_s = CrudMixin.create(Season, db, payload, actor_id=current_user["id"])
    return {"message": f"Football Season {new_s.name} successfully initialized."}

@router.put("/competitions/{comp_id}/rules", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def update_competition_rules(comp_id: int, category: str, rules_json: str, age_limit: int = None, db: Session = Depends(get_db)):
    """Advanced management of competition structure and rules"""
    comp = db.query(Competition).filter(Competition.id == comp_id).first()
    if not comp: raise HTTPException(status_code=404, detail="Competition not found")
    
    comp.category = category
    comp.rules = rules_json
    if age_limit: comp.age_limit = age_limit
    
    db.commit()
    return {"message": f"Rules and category updated for {comp.name}."}

# 💸 NATIONAL TRANSFER MARKET
@router.get("/transfers/all", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_transfers(db: Session = Depends(get_db)):
    from backend.app.database.models import Transfer
    transfers = db.query(Transfer).order_by(Transfer.transfer_date.desc()).all()
    results = []
    for t in transfers:
        results.append({
            "id": t.id,
            "player": t.player.name,
            "from": t.from_institution.name,
            "to": t.to_institution.name,
            "date": t.transfer_date.strftime("%Y-%m-%d"),
            "fee": t.fee,
            "status": t.status
        })
    return results

@router.post("/transfers/execute", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def execute_transfer(player_id: int, to_institution_id: int, fee: float = 0.0, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from backend.app.database.models import Transfer, Player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player: raise HTTPException(status_code=404, detail="Player not found")
    
    old_inst_id = player.institution_id
    
    # Update player institution via CRUD
    CrudMixin.update(Player, db, player_id, {"institution_id": to_institution_id}, actor_id=current_user["id"])
    
    # Log transfer record
    transfer_payload = {
        "player_id": player_id,
        "from_institution_id": old_inst_id,
        "to_institution_id": to_institution_id,
        "fee": fee,
        "transfer_date": datetime.utcnow()
    }
    CrudMixin.create(Transfer, db, transfer_payload, actor_id=current_user["id"])
    
    return {"message": f"Transfer of {player.name} authorized and recorded."}

# 🎖️ AI AWARDS & PERFORMANCE SUGGESTIONS (VOTING SYSTEM)
@router.get("/awards/suggested", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def suggest_awards(db: Session = Depends(get_db)):
    from backend.app.database.models import AIAnalysis, Player, PlayerStat
    
    # Best Player / MVP candidates (High AI Rating)
    top_overall = db.query(Player, AIAnalysis).join(AIAnalysis).order_by(AIAnalysis.star_rating.desc()).limit(3).all()
    
    # Top Scorers (using PlayerStat)
    top_scorers = db.query(Player, PlayerStat).join(PlayerStat).order_by(PlayerStat.xg.desc(), PlayerStat.shots.desc()).limit(3).all()
    
    # Best Young Talent (Age < 21)
    young_talent = db.query(Player, AIAnalysis).join(AIAnalysis).filter(Player.age < 21).order_by(AIAnalysis.star_rating.desc()).limit(3).all()
    
    return {
        "mvp_candidates": [{"player": p.name, "club": p.institution.name if p.institution else "N/A", "rating": ai.star_rating} for p, ai in top_overall],
        "top_scorer_candidates": [{"player": p.name, "club": p.institution.name if p.institution else "N/A", "xG": stat.xg} for p, stat in top_scorers],
        "young_talent_candidates": [{"player": p.name, "club": p.institution.name if p.institution else "N/A", "rating": ai.star_rating, "age": p.age} for p, ai in young_talent]
    }

@router.post("/awards/submit-vote", dependencies=[Depends(RoleChecker(["FERWAFA", "CLUB", "SCOUT"]))])
def submit_vote(player_id: int, award_category: str, competition_id: int = None, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Allow coaches, scouts, and FERWAFA to vote for awards."""
    from backend.app.database.models import PlayerVote, User, AIAnalysis
    
    user = db.query(User).filter(User.email == current_user["username"]).first()
    
    # Calculate an AI statistical score to back this vote
    ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == player_id).first()
    stat_score = ai.star_rating if ai else 0.0
    
    new_vote = PlayerVote(
        player_id=player_id,
        voter_id=user.id,
        voter_role=user.role,
        award_category=award_category,
        competition_id=competition_id,
        ai_validation_score=stat_score
    )
    db.add(new_vote)
    db.commit()
    return {"message": f"Vote cast for {award_category} successfully recorded."}

@router.get("/awards/voting-results", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_voting_results(award_category: str, db: Session = Depends(get_db)):
    """FERWAFA dashboard to see aggregated votes vs AI stats"""
    from backend.app.database.models import PlayerVote, Player
    from sqlalchemy import func
    
    votes = db.query(
        PlayerVote.player_id, 
        func.count(PlayerVote.id).label("total_votes"),
        func.avg(PlayerVote.ai_validation_score).label("avg_stat_score")
    ).filter(PlayerVote.award_category == award_category).group_by(PlayerVote.player_id).order_by(func.count(PlayerVote.id).desc()).all()
    
    results = []
    for v in votes:
        p = db.query(Player).filter(Player.id == v.player_id).first()
        results.append({
            "player": p.name if p else "Unknown",
            "club": p.institution.name if p and p.institution else "N/A",
            "total_votes": v.total_votes,
            "ai_validation_score": round(v.avg_stat_score, 2)
        })
    return results

# 📊 NATIONAL ANALYTICS OVERVIEW
@router.get("/analytics/national", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def get_national_analytics(db: Session = Depends(get_db)):
    from backend.app.database.models import Player, Institution, Match
    return {
        "overview": {
            "total_players": db.query(Player).count(),
            "active_clubs": db.query(Institution).filter(Institution.type == 'club').count(),
            "active_academies": db.query(Institution).filter(Institution.type == 'academy').count(),
            "active_schools": db.query(Institution).filter(Institution.type == 'school').count(),
            "scheduled_matches": db.query(Match).filter(Match.status == 'SCHEDULED').count()
        },
        "geographic_distribution": {
            "Kigali": db.query(Institution).filter(Institution.province == 'Kigali City').count(),
            "Northern": db.query(Institution).filter(Institution.province == 'Northern').count(),
            "Southern": db.query(Institution).filter(Institution.province == 'Southern').count(),
            "Eastern": db.query(Institution).filter(Institution.province == 'Eastern').count(),
            "Western": db.query(Institution).filter(Institution.province == 'Western').count(),
        }
    }

# =====================================================
# ELITE FOOTBALL OPERATIONS (FERWAFA SPEC)
# =====================================================

@router.get("/players/{player_id}/progression")
def get_player_progression(player_id: int, db: Session = Depends(get_db)):
    """Track youth talent growth over time (AI Performance History)"""
    from backend.app.database.models import AIAnalysis, PlayerStat
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player: raise HTTPException(status_code=404, detail="Player not found")
    
    # Mock progression data based on existing AI analyses
    analyses = db.query(AIAnalysis).filter(AIAnalysis.player_id == player_id).order_by(AIAnalysis.last_updated.asc()).all()
    
    return {
        "player": player.name,
        "history": [
            {"date": a.last_updated.strftime("%Y-%m-%d"), "rating": a.star_rating, "notes": a.analysis_notes}
            for a in analyses
        ]
    }

@router.get("/analytics/comparison")
def compare_players(player_ids: list[int] = Depends(lambda ids: [int(x) for x in ids.split(",")]), db: Session = Depends(get_db)):
    """Side-by-side comparison of national talents using AI metrics"""
    from backend.app.database.models import Player, AIAnalysis
    players = db.query(Player).filter(Player.id.in_(player_ids)).all()
    results = []
    for p in players:
        ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).order_by(AIAnalysis.star_rating.desc()).first()
        results.append({
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": ai.star_rating if ai else 0.0,
            "club": p.institution.name if p.institution else "N/A"
        })
    return results

@router.post("/awards/finalize")
def cast_official_vote(award_type: str, player_id: int, season: str, db: Session = Depends(get_db)):
    """FERWAFA officially declares the winner based on votes and AI data"""
    from backend.app.database.models import Award
    new_award = Award(
        player_id=player_id,
        award_type=award_type,
        season=season,
        timestamp=datetime.utcnow()
    )
    db.add(new_award)
    db.commit()
    return {"message": f"Official declaration for {award_type} successfully registered in National Ledger."}

@router.get("/rankings/institutions")
def get_national_rankings(type: str = "academy", db: Session = Depends(get_db)):
    """National rankings for clubs, schools, and academies based on AI performance"""
    # Logic to aggregate player ratings per institution
    institutions = db.query(Institution).filter(Institution.type == type).all()
    rankings = []
    for inst in institutions:
        players = db.query(Player).filter(Player.institution_id == inst.id).all()
        if not players: continue
        
        total_rating = 0
        count = 0
        for p in players:
            ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).first()
            if ai:
                total_rating += ai.star_rating
                count += 1
        
        avg_rating = total_rating / count if count > 0 else 0
        rankings.append({
            "name": inst.name,
            "avg_rating": round(avg_rating, 2),
            "player_count": len(players)
        })
    
    return sorted(rankings, key=lambda x: x["avg_rating"], reverse=True)

@router.get("/matches/{match_id}/oversight")
def get_match_oversight_data(match_id: int, db: Session = Depends(get_db)):
    """Detailed AI confidence and manual correction review for Match Oversight"""
    from backend.app.database.models import MatchEvent
    events = db.query(MatchEvent).filter(MatchEvent.match_id == match_id).all()
    
    return {
        "total_events": len(events),
        "ai_confidence_avg": round(sum(e.ai_confidence or 0 for e in events) / len(events), 2) if events else 0,
        "corrections": [e for e in events if e.source == "correction"],
        "low_confidence_events": [e for e in events if (e.ai_confidence or 1.0) < 0.7 and e.source == "ai"]
    }

@router.get("/live/monitor", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def monitor_live_matches(db: Session = Depends(get_db)):
    """National Command Center: Stream live match statuses and real-time AI states"""
    live_matches = db.query(Match).filter(Match.status == "LIVE").all()
    results = []
    
    for m in live_matches:
        home = db.query(Institution).filter(Institution.id == m.home_team_id).first()
        away = db.query(Institution).filter(Institution.id == m.away_team_id).first()
        
        # Check if AI Machine is actively connected
        session = db.query(MatchSession).filter(MatchSession.match_id == m.id).first()
        ai_active = session.ai_connected if session else False
        
        results.append({
            "match_id": m.id,
            "home": home.name if home else "Unknown",
            "away": away.name if away else "Unknown",
            "score": f"{m.score_home} - {m.score_away}",
            "ai_active": ai_active,
            "stadium": m.stadium
        })
        
    return {"active_live_matches": len(results), "matches": results}

# =====================================================
# YOUTH & DEVELOPMENT ARCHITECTURE (FERWAFA SPEC)
# =====================================================

@router.get("/youth/tournaments")
def get_youth_tournaments(db: Session = Depends(get_db)):
    """Retrieve all youth-specific competitions and festivals"""
    # Filter for competitions marked as 'Youth' or 'Development'
    from backend.app.database.models import Competition
    return db.query(Competition).filter(Competition.type.in_(["Youth", "U17", "U15", "Grassroots"])).all()

@router.get("/youth/prospects")
def get_youth_prospects(min_rating: float = 6.0, db: Session = Depends(get_db)):
    """Elite youth talent tracking based on AI Performance Intelligence"""
    from backend.app.database.models import Player, AIAnalysis
    # Join Players with AI Analysis where age < 19
    prospects = db.query(Player).filter(Player.age < 19).all()
    results = []
    for p in prospects:
        ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).first()
        if ai and ai.star_rating >= min_rating:
            results.append({
                "id": p.id,
                "name": p.name,
                "age": p.age,
                "position": p.position,
                "rating": ai.star_rating,
                "club": p.institution.name if p.institution else "Independent"
            })
    return sorted(results, key=lambda x: x["rating"], reverse=True)

@router.post("/youth/scout-report")
def submit_official_scout_report(player_id: int, technical_score: int, physical_score: int, potential: str, db: Session = Depends(get_db)):
    """Official FERWAFA technical report for national talent pool"""
    # Log the report in activity for now, could be a new model later
    from backend.app.database.models import SystemActivity
    report_desc = f"TECHNICAL EVALUATION: Player ID {player_id} | Tech: {technical_score}/10 | Phys: {physical_score}/10 | Potential: {potential}"
    activity = SystemActivity(
        action="YOUTH_TECHNICAL_REPORT",
        description=report_desc,
        actor_email="FERWAFA_TECHNICAL_DIRECTOR"
    )
    db.add(activity)
    db.commit()
    return {"message": "Technical scouting report successfully archived in National Talent Database."}
# =====================================================
# YOUTH LEAGUE HISTORY & RESULTS
# =====================================================

@router.get("/youth/history")
def get_youth_league_history(db: Session = Depends(get_db)):
    """Retrieve all historical youth league seasons and their final standings"""
    from backend.app.database.models import Competition, Match
    # Filter for completed youth leagues
    comps = db.query(Competition).filter(Competition.type.in_(["Youth", "U17", "U15"]), Competition.status == "COMPLETED").all()
    return comps

@router.get("/youth/results/{competition_id}")
def get_youth_league_results(competition_id: int, db: Session = Depends(get_db)):
    """Retrieve all match results for a specific historical youth competition"""
    from backend.app.database.models import Match, Institution
    matches = db.query(Match).filter(Match.competition_id == competition_id).order_by(Match.match_date.desc()).all()
    
    results = []
    for m in matches:
        home = db.query(Institution).filter(Institution.id == m.home_team_id).first()
        away = db.query(Institution).filter(Institution.id == m.away_team_id).first()
        results.append({
            "id": m.id,
            "home": home.name if home else "Unknown",
            "away": away.name if away else "Unknown",
            "score": f"{m.score_home} - {m.score_away}" if m.status == "COMPLETED" else "TBD",
            "date": m.match_date.strftime("%Y-%m-%d"),
            "round": m.round
        })
    return results

@router.get("/youth/standings/{competition_id}")
def get_youth_league_standings(competition_id: int, db: Session = Depends(get_db)):
    """Calculate and return standings for a youth competition"""
    from backend.app.database.models import Match, Institution
    matches = db.query(Match).filter(Match.competition_id == competition_id, Match.status == "COMPLETED").all()
    
    standings = {}
    for m in matches:
        for tid in [m.home_team_id, m.away_team_id]:
            if tid not in standings:
                inst = db.query(Institution).filter(Institution.id == tid).first()
                standings[tid] = {"name": inst.name if inst else "Unknown", "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
        
        # Update stats
        s_h = m.score_home or 0
        s_a = m.score_away or 0
        
        standings[m.home_team_id]["p"] += 1
        standings[m.away_team_id]["p"] += 1
        standings[m.home_team_id]["gf"] += s_h
        standings[m.home_team_id]["ga"] += s_a
        standings[m.away_team_id]["gf"] += s_a
        standings[m.away_team_id]["ga"] += s_h
        
        if s_h > s_a:
            standings[m.home_team_id]["w"] += 1
            standings[m.home_team_id]["pts"] += 3
            standings[m.away_team_id]["l"] += 1
        elif s_h < s_a:
            standings[m.away_team_id]["w"] += 1
            standings[m.away_team_id]["pts"] += 3
            standings[m.home_team_id]["l"] += 1
        else:
            standings[m.home_team_id]["d"] += 1
            standings[m.home_team_id]["pts"] += 1
            standings[m.away_team_id]["d"] += 1
            standings[m.away_team_id]["pts"] += 1
            
    return sorted(standings.values(), key=lambda x: (x["pts"], x["gf"] - x["ga"]), reverse=True)

# =====================================================
# 📊 NATIONAL REPORTING ENGINE (FERWAFA SPEC §12)
# =====================================================

@router.get("/reports/competitions", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def report_competitions(season: str = None, status: str = None, db: Session = Depends(get_db)):
    """Generate a competition report with match counts, team counts, and result summaries"""
    from backend.app.database.models import Competition, Match, Institution
    query = db.query(Competition)
    if season:
        query = query.filter(Competition.season == season)
    if status:
        query = query.filter(Competition.status == status)
    
    comps = query.order_by(Competition.created_at.desc()).all()
    rows = []
    for c in comps:
        matches = db.query(Match).filter(Match.competition_id == c.id).all()
        completed = [m for m in matches if m.status == "COMPLETED"]
        team_ids = set()
        total_goals = 0
        for m in matches:
            team_ids.add(m.home_team_id)
            team_ids.add(m.away_team_id)
            if m.status == "COMPLETED":
                total_goals += (m.score_home or 0) + (m.score_away or 0)
        
        rows.append({
            "id": c.id,
            "name": c.name,
            "type": c.type or "LEAGUE",
            "season": c.season or "2026",
            "category": c.category or "Senior",
            "status": c.status,
            "total_teams": len(team_ids),
            "total_matches": len(matches),
            "completed_matches": len(completed),
            "pending_matches": len(matches) - len(completed),
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / len(completed), 2) if completed else 0
        })
    
    return {
        "report_type": "COMPETITION SUMMARY",
        "generated_at": datetime.utcnow().isoformat(),
        "total_competitions": len(rows),
        "filters": {"season": season, "status": status},
        "rows": rows
    }

@router.get("/reports/players", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def report_players(institution_id: int = None, province: str = None, min_rating: float = None, max_age: int = None, db: Session = Depends(get_db)):
    """Generate a player report with AI ratings, stats, and institution info"""
    from backend.app.database.models import Player, AIAnalysis, PlayerStat, Institution
    
    query = db.query(Player).join(Institution, Player.institution_id == Institution.id)
    if institution_id:
        query = query.filter(Player.institution_id == institution_id)
    if province:
        query = query.filter(Institution.province == province)
    
    players = query.order_by(Player.name.asc()).all()
    rows = []
    for p in players:
        ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).order_by(AIAnalysis.star_rating.desc()).first()
        stat = db.query(PlayerStat).filter(PlayerStat.player_id == p.id).order_by(PlayerStat.timestamp.desc()).first()
        
        age = (datetime.now().date() - p.date_of_birth).days // 365 if p.date_of_birth else None
        rating = ai.star_rating if ai else 0
        
        # Apply filters
        if min_rating and rating < min_rating:
            continue
        if max_age and age and age > max_age:
            continue
        
        rows.append({
            "id": p.id,
            "player_code": p.player_code,
            "name": p.name,
            "position": p.position or "N/A",
            "age": age if age else "N/A",
            "nationality": p.nationality or "Rwandan",
            "institution": p.institution.name if p.institution else "Free Agent",
            "institution_type": p.institution.type if p.institution else "N/A",
            "province": p.institution.province if p.institution else "N/A",
            "district": p.institution.district if p.institution else "N/A",
            "ai_rating": rating,
            "matches_played": stat.minutes_played // 90 if stat and stat.minutes_played else 0,
            "goals": stat.shots if stat else 0,
            "assists": stat.assists if stat else 0,
            "xg": round(stat.xg, 2) if stat else 0,
            "pass_accuracy": round(stat.pass_accuracy, 1) if stat else 0
        })
    
    # Sort by AI rating descending
    rows.sort(key=lambda x: x["ai_rating"] if isinstance(x["ai_rating"], (int, float)) else 0, reverse=True)
    
    return {
        "report_type": "PLAYER INTELLIGENCE REPORT",
        "generated_at": datetime.utcnow().isoformat(),
        "total_players": len(rows),
        "filters": {"institution_id": institution_id, "province": province, "min_rating": min_rating, "max_age": max_age},
        "rows": rows
    }

@router.get("/reports/institutions", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def report_institutions(type: str = None, province: str = None, db: Session = Depends(get_db)):
    """Generate an institution report with player counts, match activity, and performance"""
    from backend.app.database.models import Player, AIAnalysis, Match, Institution
    
    query = db.query(Institution)
    if type:
        query = query.filter(Institution.type == type)
    if province:
        query = query.filter(Institution.province == province)
    
    institutions = query.order_by(Institution.name.asc()).all()
    rows = []
    for inst in institutions:
        players = db.query(Player).filter(Player.institution_id == inst.id).all()
        
        # Calculate avg AI rating
        total_rating = 0
        rated_count = 0
        for p in players:
            ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).first()
            if ai:
                total_rating += ai.star_rating
                rated_count += 1
        
        avg_rating = round(total_rating / rated_count, 2) if rated_count > 0 else 0
        
        # Count matches
        home_matches = db.query(Match).filter(Match.home_team_id == inst.id).count()
        away_matches = db.query(Match).filter(Match.away_team_id == inst.id).count()
        
        rows.append({
            "id": inst.id,
            "name": inst.name,
            "type": inst.type,
            "code": inst.code,
            "province": inst.province or "N/A",
            "district": inst.district or "N/A",
            "stadium": inst.stadium_name or "N/A",
            "capacity": inst.capacity or 0,
            "pitch_type": inst.pitch_type or "Natural Grass",
            "floodlights": "Yes" if inst.has_floodlights else "No",
            "total_players": len(players),
            "rated_players": rated_count,
            "avg_ai_rating": avg_rating,
            "total_matches": home_matches + away_matches,
            "home_matches": home_matches,
            "away_matches": away_matches
        })
    
    rows.sort(key=lambda x: x["avg_ai_rating"], reverse=True)
    
    return {
        "report_type": "INSTITUTION PERFORMANCE REPORT",
        "generated_at": datetime.utcnow().isoformat(),
        "total_institutions": len(rows),
        "filters": {"type": type, "province": province},
        "rows": rows
    }

@router.get("/reports/summary", dependencies=[Depends(RoleChecker(["FERWAFA"]))])
def report_national_summary(db: Session = Depends(get_db)):
    """Universal national football summary — high-level KPIs for executive briefing"""
    from backend.app.database.models import Player, Institution, Match, Competition, AIAnalysis, Transfer, Award
    
    total_players = db.query(Player).count()
    total_institutions = db.query(Institution).count()
    total_matches = db.query(Match).count()
    completed_matches = db.query(Match).filter(Match.status == "COMPLETED").count()
    live_matches = db.query(Match).filter(Match.status == "LIVE").count()
    scheduled_matches = db.query(Match).filter(Match.status == "SCHEDULED").count()
    total_competitions = db.query(Competition).count()
    active_competitions = db.query(Competition).filter(Competition.status == "ACTIVE").count()
    total_ai_analyses = db.query(AIAnalysis).count()
    
    # By type
    clubs = db.query(Institution).filter(Institution.type == "club").count()
    academies = db.query(Institution).filter(Institution.type == "academy").count()
    schools = db.query(Institution).filter(Institution.type == "school").count()
    
    # Goals
    all_completed = db.query(Match).filter(Match.status == "COMPLETED").all()
    total_goals = sum((m.score_home or 0) + (m.score_away or 0) for m in all_completed)
    
    # Geographic
    provinces = {}
    for inst in db.query(Institution).all():
        prov = inst.province or "Unknown"
        provinces[prov] = provinces.get(prov, 0) + 1
    
    return {
        "report_type": "NATIONAL EXECUTIVE SUMMARY",
        "generated_at": datetime.utcnow().isoformat(),
        "kpis": {
            "total_players": total_players,
            "total_institutions": total_institutions,
            "clubs": clubs,
            "academies": academies,
            "schools": schools,
            "total_matches": total_matches,
            "completed_matches": completed_matches,
            "live_matches": live_matches,
            "scheduled_matches": scheduled_matches,
            "total_goals": total_goals,
            "avg_goals_per_match": round(total_goals / completed_matches, 2) if completed_matches else 0,
            "total_competitions": total_competitions,
            "active_competitions": active_competitions,
            "ai_analyses_performed": total_ai_analyses
        },
        "geographic_distribution": provinces
    }
