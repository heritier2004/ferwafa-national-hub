from sqlalchemy.orm import Session
from backend.app.players.models import Player
from backend.app.matches.models import AIAnalysis, PlayerStat
from sqlalchemy import func

class ScoutingRecommender:
    def __init__(self, db: Session):
        self.db = db

    def get_top_talents(self, position: str = None, min_rating: float = 7.0, limit: int = 10):
        """
        Recommends players based on average AI star rating.
        """
        query = self.db.query(
            Player,
            func.avg(AIAnalysis.star_rating).label('avg_rating')
        ).join(AIAnalysis, Player.id == AIAnalysis.player_id)
        
        if position:
            query = query.filter(Player.position == position)
            
        recommendations = query.group_by(Player.id)\
            .having(func.avg(AIAnalysis.star_rating) >= min_rating)\
            .order_by(func.avg(AIAnalysis.star_rating).desc())\
            .limit(limit)\
            .all()
            
        return recommendations
