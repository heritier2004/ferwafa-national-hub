from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import Institution, Match, Fixture, Player, AIAnalysis, User, SystemActivity, MatchSession
from backend.app.auth.security import get_password_hash
from sqlalchemy import text
import random
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/ferwafa", tags=["ferwafa"])

@router.post("/entities/create")
def create_entity(name: str, type: str, code: str, stadium_name: str, province: str, district: str, sector: str, cell: str, logo_url: str = None, has_floodlights: bool = False, pitch_type: str = "Natural Grass", capacity: int = 5000, db: Session = Depends(get_db)):
    if type not in ["club", "school", "academy"]:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    db_inst = db.query(Institution).filter(Institution.code == code).first()
    if db_inst:
        raise HTTPException(status_code=400, detail="Entity with this code already exists")
    
    new_inst = Institution(
        name=name,
        type=type,
        code=code,
        stadium_name=stadium_name,
        province=province,
        district=district,
        sector=sector,
        cell=cell,
        logo_url=logo_url,
        has_floodlights=has_floodlights,
        pitch_type=pitch_type,
        capacity=capacity
    )
    db.add(new_inst)
    db.commit()
    return {"message": f"{type.capitalize()} '{name}' registered with full hosting profile."}

@router.get("/entities/all")
def get_entities(db: Session = Depends(get_db)):
    return db.query(Institution).all()

# 🏃 PLAYER REGISTRY MANAGEMENT (CLUB HUD)
@router.post("/players")
def create_player(institution_id: int, name: str, position: str = None, jersey_number: int = None, nationality: str = "Rwandan", date_of_birth: str = None, photo_url: str = None, db: Session = Depends(get_db)):
    p_code = f"PLY-{random.randint(10000, 99999)}"
    dob = None
    if date_of_birth:
        try: dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        except: pass

    new_p = Player(
        institution_id=institution_id, player_code=p_code, name=name, position=position, 
        jersey_number=jersey_number, nationality=nationality, date_of_birth=dob, photo_url=photo_url
    )
    db.add(new_p)
    db.commit()
    return {"message": f"Player {name} registered to squad perfectly."}

@router.get("/players/{institution_id}")
def get_club_players(institution_id: int, db: Session = Depends(get_db)):
    return db.query(Player).filter(Player.institution_id == institution_id).order_by(Player.jersey_number.asc()).all()

@router.put("/players/{player_id}")
def update_player(player_id: int, position: str = None, jersey_number: int = None, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player: raise HTTPException(status_code=404, detail="Player not found")
    if position: player.position = position
    if jersey_number is not None: player.jersey_number = jersey_number
    db.commit()
    return {"message": f"Player profile for {player.name} updated."}

@router.delete("/players/{player_id}")
def delete_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player: raise HTTPException(status_code=404, detail="Player not found")
    db.delete(player)
    db.commit()
    return {"message": f"Player {player.name} released from squad."}

# 🏆 ELITE ROUND-ROBIN MIXER (v5.0 - Governance Spec)
@router.post("/fixtures/auto-generate")
def auto_generate_league(institution_ids: list[int], start_date: str, end_date: str, division_name: str, db: Session = Depends(get_db)):
    teams = db.query(Institution).filter(Institution.id.in_(institution_ids)).all()
    if len(teams) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams")

    # 🏛️ CREATE OFFICIAL COMPETITION SCABBARD
    comp = db.query(Competition).filter(Competition.name == division_name).first()
    if not comp:
        comp = Competition(name=division_name, type="LEAGUE", season="2026", status="ACTIVE")
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
def update_entity(inst_id: int, name: str = None, stadium_name: str = None, capacity: int = None, pitch_type: str = None, db: Session = Depends(get_db)):
    inst = db.query(Institution).filter(Institution.id == inst_id).first()
    if not inst: raise HTTPException(status_code=404, detail="Institution not found")
    if name: inst.name = name
    if stadium_name: inst.stadium_name = stadium_name
    if capacity: inst.capacity = capacity
    if pitch_type: inst.pitch_type = pitch_type
    db.commit()
    return {"message": f"Updated {inst.name} successfully."}

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

@router.get("/fixtures/mine/{institution_id}")
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
@router.post("/users/manage")
def create_member_user(email: str, full_name: str, password: str, role: str, institution_id: int, photo_url: str = None, db: Session = Depends(get_db)):
    hashed = get_password_hash(password)
    new_user = User(email=email, full_name=full_name, password_hash=hashed, role=role, institution_id=institution_id, photo_url=photo_url)
    db.add(new_user)
    db.commit()
    return {"message": f"Login created for {role} Official of institution #{institution_id}"}

@router.get("/users/all")
def get_member_users(db: Session = Depends(get_db)):
    # Return users that are NOT super admins or ferwafa
    return db.query(User, Institution).outerjoin(Institution).filter(User.role.in_(['CLUB', 'SCHOOL', 'ACADEMY', 'SCOUT'])).all()

@router.get("/users/universal")
def get_universal_ledger(db: Session = Depends(get_db)):
    """Universal oversight for FERWAFA Boss mode"""
    users = db.query(User).all()
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

@router.put("/users/{user_id}")
def update_user_authority(user_id: int, full_name: str = None, email: str = None, is_active: bool = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    if full_name: user.full_name = full_name
    if email: user.email = email
    if is_active is not None: user.is_active = is_active
    db.commit()
    return {"message": f"User {user.email} updated by National Authority."}

@router.delete("/users/{user_id}")
def delete_user_authority(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    email = user.email
    db.delete(user)
    db.commit()
    return {"message": f"User {email} permanently purged from national system."}

@router.post("/onboard/full-node")
def onboard_institutional_node(
    name: str, type: str, code: str, stadium_name: str, 
    province: str, district: str, sector: str, cell: str,
    admin_email: str, admin_name: str, admin_pass: str,
    logo_url: str = None, db: Session = Depends(get_db)
):
    # 1. Create Institution
    new_inst = Institution(
        name=name, type=type, code=code, stadium_name=stadium_name,
        province=province, district=district, sector=sector, cell=cell,
        logo_url=logo_url
    )
    db.add(new_inst)
    db.flush()
    
    # 2. Create Admin User
    role = type.upper()
    hashed = get_password_hash(admin_pass)
    new_user = User(
        email=admin_email, full_name=admin_name, 
        password_hash=hashed, role=role, institution_id=new_inst.id
    )
    db.add(new_user)
    
    db.commit()
    return {"message": f"Successfully onboarded {name} and created {admin_name}'s management account."}

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
            "stadium": m.stadium
        })
    return results

# 🕵️ FORENSIC NATIONAL OVERSIGHT
@router.get("/activity/global")
def get_global_forensics(db: Session = Depends(get_db)):
    # Monitor everything happened in the system
    return db.query(SystemActivity).order_by(SystemActivity.timestamp.desc()).limit(50).all()

# 🗄️ NATIONAL DATABASE EXPLORER
@router.get("/db/browse/{table_name}")
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
