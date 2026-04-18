from sqlalchemy.orm import Session
from backend.app.config.database import SessionLocal, engine, Base
from backend.app.database.models import User, Institution
from backend.app.players.models import Player
from backend.app.matches.models import Match, MatchEvent, PlayerStat, AIAnalysis
from backend.app.database.additional_models import Fixture, LiveSession
from backend.app.auth.security import get_password_hash
from datetime import date

def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    # 1. Create Super Admin
    admin_email = "admin@ferwafa.rw"
    db_admin = db.query(User).filter(User.email == admin_email).first()
    if not db_admin:
        new_admin = User(
            email=admin_email,
            password_hash=get_password_hash("ANGEU"),
            role="SUPER_ADMIN",
            full_name="National Football Admin"
        )
        db.add(new_admin)
        print("Super Admin created.")

    # 2. Create Institutions
    clubs = [
        {"name": "APR FC", "type": "club", "code": "APR", "location": "Kigali"},
        {"name": "RAYON SPORTS", "type": "club", "code": "RAYON", "location": "Nyanza/Kigali"},
        {"name": "AMAVUBI ACADEMY", "type": "academy", "code": "AMV", "location": "Rubavu"}
    ]
    
    for club_data in clubs:
        db_inst = db.query(Institution).filter(Institution.code == club_data["code"]).first()
        if not db_inst:
            new_inst = Institution(**club_data)
            db.add(new_inst)
            print(f"Institution {club_data['name']} created.")
    
    db.commit()

    # 3. Create initial players for APR
    apr = db.query(Institution).filter(Institution.code == "APR").first()
    if apr:
        players = [
            {"name": "Meddie Kagere", "player_code": "APR-001", "position": "Forward", "institution_id": apr.id},
            {"name": "Jacques Tuyisenge", "player_code": "APR-002", "position": "Forward", "institution_id": apr.id}
        ]
        for p_data in players:
            db_plyr = db.query(Player).filter(Player.player_code == p_data["player_code"]).first()
            if not db_plyr:
                new_plyr = Player(**p_data)
                db.add(new_plyr)
                print(f"Player {p_data['name']} added.")
                
    db.commit()
    db.close()
    print("Seeding complete.")

if __name__ == "__main__":
    seed()
