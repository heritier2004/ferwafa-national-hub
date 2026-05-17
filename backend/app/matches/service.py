import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.database.models import Match, MatchSquad, AuditLog, Institution

class MatchService:
    @staticmethod
    def get_matches(db: Session, status: str = None):
        query = db.query(Match)
        if status:
            query = query.filter(Match.status == status)
        return query.all()

    @staticmethod
    def create_match(db: Session, match_data: dict):
        new_match = Match(**match_data)
        db.add(new_match)
        db.commit()
        db.refresh(new_match)
        return new_match

    @staticmethod
    def validate_and_generate_credentials(db: Session, match_id: int, actor_email: str = None):
        """
        Validates match readiness and generates secure Match Token and API Key.
        """
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match:
            return {"error": "Match not found"}, 404

        # 1. VALIDATION
        # Check Teams
        if not match.home_team_id or not match.away_team_id:
            if not match.opponent_name: # Some matches might have string opponent
                 return {"error": "Teams must be defined"}, 400
        
        # Check Venue
        if not match.stadium:
            return {"error": "Venue/Stadium must be defined"}, 400
            
        # Check Match Date
        if not match.match_date:
            return {"error": "Match date must be defined"}, 400

        # Check Squad (18 players)
        squad_count = db.query(MatchSquad).filter(MatchSquad.match_id == match_id).count()
        if squad_count < 18:
            return {"error": f"Complete 18-player squad required (Current: {squad_count})"}, 400
            
        # Check Starting XI (11 players)
        xi_count = db.query(MatchSquad).filter(MatchSquad.match_id == match_id, MatchSquad.role == 'starting').count()
        if xi_count != 11:
            return {"error": f"Starting XI must have exactly 11 players (Current: {xi_count})"}, 400

        # 2. GENERATION
        match_token = f"MCH-{uuid.uuid4().hex[:12].upper()}"
        raw_api_key = f"sk_live_{secrets.token_urlsafe(24)}"
        hashed_key = hashlib.sha256(raw_api_key.encode()).hexdigest()

        # Update Match
        match.match_token = match_token
        match.api_key_hash = hashed_key
        match.session_status = "WAITING"
        match.expires_at = datetime.utcnow() + timedelta(hours=6) # Expires in 6 hours
        
        # 3. AUDIT LOG
        log = AuditLog(
            action="GENERATION",
            match_id=match_id,
            description=f"Generated secure credentials for match {match_id}. Token: {match_token}",
            actor_email=actor_email
        )
        db.add(log)
        db.commit()
        db.refresh(match)

        return {
            "match_id": match.id,
            "match_token": match_token,
            "api_key": raw_api_key, # Return raw key ONLY once here
            "expires_at": match.expires_at.isoformat()
        }, 200

    @staticmethod
    def update_score(db: Session, match_id: int, score_home: int, score_away: int):
        match = db.query(Match).filter(Match.id == match_id).first()
        if match:
            match.score_home = score_home
            match.score_away = score_away
            db.commit()
            db.refresh(match)
        return match
    @staticmethod
    def auto_generate_squad(db: Session, match_id: int):
        from backend.app.database.models import Match, Player, MatchSquad
        match = db.query(Match).filter(Match.id == match_id).first()
        if not match: return {"error": "Match not found"}, 404
        
        # 1. Get Home Team Players
        players = db.query(Player).filter(Player.institution_id == match.home_team_id).limit(18).all()
        if len(players) < 18:
            return {"error": f"Insufficient players in institution (Need 18, have {len(players)})"}, 400
            
        # 2. Clear existing
        db.query(MatchSquad).filter(MatchSquad.match_id == match_id).delete()
        
        # 3. Add new
        for i, p in enumerate(players):
            role = "starting" if i < 11 else "substitute"
            new_squad = MatchSquad(
                match_id=match_id,
                player_id=p.id,
                team_id=match.home_team_id,
                role=role,
                jersey_number=p.jersey_number or (i+1)
            )
            db.add(new_squad)
            
        db.commit()
        return {"status": "success", "count": len(players)}
