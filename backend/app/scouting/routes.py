from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.scouting.recommender import ScoutingRecommender

router = APIRouter(prefix="/scouting", tags=["scouting"])

@router.get("/recommendations")
def get_recommendations(position: str = None, min_rating: float = 7.0, db: Session = Depends(get_db)):
    recommender = ScoutingRecommender(db)
    results = recommender.get_top_talents(position, min_rating)
    # Format results for JSON response
    return [{"player": r[0].name, "rating": float(r[1])} for r in results]
