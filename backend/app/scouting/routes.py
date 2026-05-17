from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.scouting.recommender import ScoutingRecommender
from backend.app.database.models import Player

from backend.app.auth.dependencies import get_current_user, RoleChecker

router = APIRouter(
    prefix="/scouting", 
    tags=["scouting"],
    dependencies=[Depends(RoleChecker(["SCOUT", "FERWAFA"]))]
)

@router.get("/recommendations")
def get_recommendations(position: str = None, min_rating: float = 7.0, db: Session = Depends(get_db)):
    """Advanced AI Recommendation Engine using Potential and Growth Curves."""
    query = db.query(Player).filter(Player.is_elite_prospect == True)
    if position:
        query = query.filter(Player.position == position)
    
    # Prioritize high potential and rapid growth curves
    players = query.order_by(Player.potential_score.desc(), Player.growth_curve.desc()).limit(10).all()
    
    results = []
    for p in players:
        # Determine tag (Hidden Gem if talent score is low but potential is high)
        tag = "Top Prospect"
        if p.potential_score > 85 and p.talent_score < 70:
            tag = "Hidden Gem"
        elif p.talent_score > 85:
            tag = "Elite Player"
            
        results.append({
            "player_id": p.id,
            "name": p.name,
            "position": p.position,
            "current_rating": p.talent_score,
            "potential_score": p.potential_score,
            "growth_trend": "Rapid" if p.growth_curve > 5 else "Steady",
            "tag": tag
        })
        
    return results

@router.get("/top-talents")
def get_top_talents(position: str = None, min_rating: float = 7.0, db: Session = Depends(get_db)):
    recommender = ScoutingRecommender(db)
    results = recommender.get_top_talents(position, min_rating)
    return [{"player": r[0].name, "rating": float(r[1])} for r in results]
