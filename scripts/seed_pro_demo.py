import sys
import os
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from backend.app.config.database import SessionLocal, engine, Base
from backend.app.database.models import (
    User, Institution, Player, Match, MatchSquad, 
    MatchSession, Competition, Attendance, PlayerStat, AIAnalysis
)
from backend.app.auth.security import get_password_hash

def seed_demo():
    print("Starting Professional Demo Seeding...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # 1. Competitions
    league = db.query(Competition).filter(Competition.name == "Rwanda Pro Demo League").first()
    if not league:
        league = Competition(
            name="Rwanda Pro Demo League",
            type="LEAGUE",
            season="2026/2027",
            status="ACTIVE"
        )
        db.add(league)
        db.flush()

    # 2. Institutions
    apr = db.query(Institution).filter(Institution.code == "APR").first()
    if not apr:
        apr = Institution(
            name="APR FC (Professional)",
            type="club",
            code="APR",
            location="Kigali",
            division="Premier League",
            stadium_name="Kigali Pelé Stadium"
        )
        db.add(apr)

    rayon = db.query(Institution).filter(Institution.code == "RAYON").first()
    if not rayon:
        rayon = Institution(
            name="RAYON SPORTS (Elite)",
            type="club",
            code="RAYON",
            location="Kigali",
            division="Premier League",
            stadium_name="Nyamirambo Stadium"
        )
        db.add(rayon)
    
    db.flush()

    # 3. Players (11 for each)
    def create_squad(inst, prefix):
        players = []
        for i in range(1, 12):
            p_code = f"{prefix}-{str(i).zfill(3)}"
            p = db.query(Player).filter(Player.player_code == p_code).first()
            if not p:
                p = Player(
                    name=f"Player {prefix} {i}",
                    player_code=p_code,
                    position="GK" if i==1 else ("DEF" if i<6 else ("MID" if i<10 else "FWD")),
                    institution_id=inst.id,
                    jersey_number=i
                )
                db.add(p)
            players.append(p)
        return players

    apr_players = create_squad(apr, "APR")
    rayon_players = create_squad(rayon, "RAYON")
    db.flush()

    # 4. A Live Match Session
    api_key = "FWFA-APR-2026-893A"
    token = "MATCH-2026-DEMO"
    
    demo_match = db.query(Match).filter(Match.match_token == token).first()
    if not demo_match:
        demo_match = Match(
            competition_id=league.id,
            home_team_id=apr.id,
            away_team_id=rayon.id,
            stadium="Kigali Pelé Stadium",
            match_date=datetime.utcnow() + timedelta(hours=2),
            status="SCHEDULED",
            api_key=api_key,
            match_token=token,
            opponent_name="RAYON SPORTS (Elite)",
            competition_type="League",
            kit_home_color="#FF0000", # Red
            kit_away_color="#0000FF"  # Blue
        )
        db.add(demo_match)
        db.flush()

        # Add Squad to Match
        for i, p in enumerate(apr_players):
            db.add(MatchSquad(
                match_id=demo_match.id,
                player_id=p.id,
                role="starting",
                position=p.position,
                jersey_number=p.jersey_number
            ))
        
        # Create Session Record
        session = MatchSession(
            match_id=demo_match.id,
            match_token=token,
            ai_connected=False
        )
        db.add(session)

    # 5. Attendance History (Past 7 days)
    today = date.today()
    for i in range(7):
        d = today - timedelta(days=i)
        for p in apr_players[:5]: # just some players
            if not db.query(Attendance).filter(Attendance.player_id==p.id, Attendance.date==d).first():
                db.add(Attendance(
                    institution_id=apr.id,
                    player_id=p.id,
                    date=d,
                    status="PRESENT" if i % 4 != 0 else "ABSENT"
                ))

    # 6. Some initial stats for the dashboard
    for p in apr_players:
        if not db.query(PlayerStat).filter(PlayerStat.player_id==p.id).first():
            db.add(PlayerStat(
                player_id=p.id,
                match_id=demo_match.id,
                rating=7.2,
                speed=28.5,
                distance=5.4
            ))

    db.commit()
    db.close()
    print("Demo Environment Seeding Complete.")
    print(f"   API_KEY: {api_key}")
    print(f"   TOKEN:   {token}")

if __name__ == "__main__":
    seed_demo()
