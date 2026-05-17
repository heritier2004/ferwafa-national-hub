from backend.app.config.database import SessionLocal
from backend.app.database.models import Season, AIAnalysis, Transfer, Player, Institution
from datetime import datetime, date

def seed():
    db = SessionLocal()
    
    # 1. Seasons
    if not db.query(Season).filter(Season.name == '2026/2027').first():
        s1 = Season(name='2025/2026', start_date=date(2025, 8, 1), end_date=date(2026, 5, 30), status='COMPLETED')
        s2 = Season(name='2026/2027', start_date=date(2026, 8, 1), end_date=date(2027, 5, 30), status='ACTIVE')
        db.add_all([s1, s2])
    
    # 2. AI Ratings
    players = db.query(Player).all()
    for i, p in enumerate(players[:5]):
        if not db.query(AIAnalysis).filter(AIAnalysis.player_id == p.id).first():
            rating = 7.5 + (i * 0.4)
            ai = AIAnalysis(
                player_id=p.id, 
                star_rating=rating if rating <= 9.8 else 9.8,
                analysis_notes="Top performer"
            )
            db.add(ai)
            
    # 3. Some Transfers
    if players and len(players) > 1:
        t = Transfer(
            player_id=players[0].id,
            from_institution_id=2, # Rayon
            to_institution_id=1,   # APR
            fee=50000000.0,
            status="APPROVED"
        )
        db.add(t)

    db.commit()
    db.close()
    print("National Hub seeded successfully.")

if __name__ == "__main__":
    seed()
