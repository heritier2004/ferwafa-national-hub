from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.database.models import Player, PlayerStat, AIAnalysis
from backend.app.analytics.analysis_engine import AnalysisEngine
from backend.app.utils.crud import CrudMixin
from sqlalchemy import func

from backend.app.auth.dependencies import get_current_user, RoleChecker

router = APIRouter(
    prefix="/api/analytics", 
    tags=["analytics"],
    dependencies=[Depends(RoleChecker(["CLUB", "SCHOOL", "ACADEMY", "FERWAFA", "SCOUT"]))]
)

@router.get("/player/{player_id}")
def get_player_performance(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Get latest stats
    latest_stats = db.query(PlayerStat).filter(PlayerStat.player_id == player_id).order_by(PlayerStat.timestamp.desc()).first()
    
    # Get AI Analysis
    ai = db.query(AIAnalysis).filter(AIAnalysis.player_id == player_id).order_by(AIAnalysis.last_updated.desc()).first()
    
    # If no AI rating exists yet, calculate a dynamic one using the engine
    if not ai and latest_stats:
        stats_dict = {
            "speed": latest_stats.speed,
            "distance": latest_stats.distance,
            "passes": latest_stats.passes,
            "goals": db.query(func.count(PlayerStat.id)).filter(PlayerStat.player_id == player_id).scalar(), # Simplified
            "assists": latest_stats.assists,
            "shots": latest_stats.shots
        }
        rating = AnalysisEngine.calculate_player_rating(stats_dict)
    else:
        rating = ai.star_rating if ai else 5.0
        
    return {
        "player_id": player_id,
        "name": player.name,
        "rating": rating,
        "rank": AnalysisEngine.get_star_ranking(rating),
        "stats": {
            "assists": latest_stats.assists if latest_stats else 0,
            "shots": latest_stats.shots if latest_stats else 0,
            "passes": latest_stats.passes if latest_stats else 0,
            "tackles": latest_stats.tackles if latest_stats else 0,
            "saves": latest_stats.saves if latest_stats else 0,
            "speed": latest_stats.speed if latest_stats else 0,
            "distance": latest_stats.distance if latest_stats else 0
        }
    }

@router.get("/player/{player_id}/predict")
def get_player_prediction(player_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """AI Talent Prediction Engine: Future Potential & Growth Curves."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
        
    # Mocking advanced AI prediction logic based on current stats and age
    age = player.age if player.age else 20
    base_potential = player.talent_score * 1.2 if player.talent_score > 0 else 75.0
    
    # Calculate age-based modifier
    if age < 18:
        growth_curve = 8.5 # Rapid development
        potential_ceiling = min(base_potential * 1.4, 99.0)
    elif age < 23:
        growth_curve = 5.0 # Steady development
        potential_ceiling = min(base_potential * 1.2, 99.0)
    elif age < 28:
        growth_curve = 1.0 # Peak
        potential_ceiling = base_potential
    else:
        growth_curve = -2.0 # Decline phase
        potential_ceiling = base_potential * 0.9
        
    # Calculate physiological metrics
    stats = db.query(PlayerStat).filter(PlayerStat.player_id == player_id).order_by(PlayerStat.timestamp.desc()).limit(5).all()
    minutes_played_recent = sum([s.minutes_played for s in stats]) if stats else 0
    
    fatigue_index = min(minutes_played_recent / 450.0, 1.0) # Assume 450 mins is 100% fatigued in short window
    injury_risk = min(0.1 + (fatigue_index * 0.5) + (1.0 if age > 30 else 0.0) * 0.2, 0.95)
    
    # Persist the predictions back to the player record using Safe CRUD
    update_data = {
        "potential_score": potential_ceiling,
        "growth_curve": growth_curve,
        "injury_risk": injury_risk,
        "fatigue_index": fatigue_index
    }
    updated_player = CrudMixin.update(Player, db, player_id, update_data, actor_id=current_user["id"])
    
    return {
        "player_id": player_id,
        "name": player.name,
        "current_ability": player.talent_score,
        "potential_ceiling": round(potential_ceiling, 1),
        "growth_curve_trend": round(growth_curve, 1),
        "physiological": {
            "fatigue_index": round(fatigue_index * 100, 1),
            "injury_risk": round(injury_risk * 100, 1),
            "status": "High Risk" if injury_risk > 0.6 else "Optimal"
        }
    }
