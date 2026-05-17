from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.database.models import Match, PlayerStat, MatchEvent, TrackingFrame, TacticalSnapshot, MatchSquad, Player

class IntelligenceService:
    @staticmethod
    def process_tracking_frame(db: Session, match_id: int, frame_data: dict):
        """
        Processes a raw tracking frame from the AI Machine.
        """
        # 1. Store raw frame for potential replay/VAR
        new_frame = TrackingFrame(
            match_id=match_id,
            player_id=frame_data.get("player_id"),
            tracking_id=frame_data.get("tracking_id"),
            x_pos=frame_data["x"],
            y_pos=frame_data["y"],
            velocity=frame_data.get("velocity", 0.0),
            direction=frame_data.get("direction", 0.0),
            is_ball=frame_data.get("is_ball", False),
            timestamp_match=frame_data.get("timestamp_match", 0)
        )
        db.add(new_frame)
        
        # 2. Update real-time stats (Movement & Physicality)
        if frame_data.get("player_id") and frame_data.get("velocity"):
            stat = db.query(PlayerStat).filter(
                PlayerStat.match_id == match_id,
                PlayerStat.player_id == frame_data["player_id"]
            ).first()
            if not stat:
                stat = PlayerStat(match_id=match_id, player_id=frame_data["player_id"])
                db.add(stat)
            
            # Simple distance calculation (velocity * dt)
            dt = 0.033 # 30fps
            speed = frame_data["velocity"]
            stat.distance += speed * dt
            
            # Tracking Top Speed
            if speed > stat.speed:
                stat.speed = speed
                
            # Sprint Distance (Threshold: 7.0 m/s)
            if speed > 7.0:
                stat.sprint_distance += speed * dt
            
            # Movement Efficiency / Fatigue Index
            stat.stamina_index = max(0.1, 1.0 - (stat.distance / 12000.0)) # Drops towards 12km

        db.commit()

    @staticmethod
    def process_ai_event(db: Session, match_id: int, event_data: dict):
        """
        Processes an event detected by AI (Goal, Foul, Pass, Tackle, etc).
        """
        conf = event_data.get("ai_confidence", 0.0)
        is_confirmed = conf >= 0.80 # Auto-confirm threshold
        
        new_event = MatchEvent(
            match_id=match_id,
            player_id=event_data.get("player_id"),
            event_type=event_data["event_type"],
            x_pos=event_data.get("x") or event_data.get("x_pos"),
            y_pos=event_data.get("y") or event_data.get("y_pos"),
            ai_confidence=conf,
            is_confirmed=is_confirmed,
            source="ai",
            source_event_id=event_data.get("source_event_id")
        )
        db.add(new_event)
        
        if is_confirmed:
            IntelligenceService.apply_confirmed_event(db, match_id, event_data)
            
        db.commit()
        return new_event

    @staticmethod
    def apply_confirmed_event(db: Session, match_id: int, event_data: dict):
        etype = event_data["event_type"]
        pid = event_data.get("player_id")
        
        # 1. Match State Update
        if etype == "goal":
            match = db.query(Match).filter(Match.id == match_id).first()
            if match:
                if event_data.get("team") == "home": match.score_home += 1
                else: match.score_away += 1
        
        # 2. Player Stats Update
        if pid:
            stat = db.query(PlayerStat).filter(PlayerStat.match_id == match_id, PlayerStat.player_id == pid).first()
            if not stat:
                stat = PlayerStat(match_id=match_id, player_id=pid)
                db.add(stat)
            
            if etype == "goal":
                stat.shots += 1
                stat.xg += event_data.get("xg_value", 0.1)
            elif etype == "shot":
                stat.shots += 1
                stat.xg += event_data.get("xg_value", 0.05)
            elif etype == "pass":
                stat.passes += 1
                # Accuracy logic would need a 'pass_failed' event or flag
            elif etype == "tackle":
                stat.tackles += 1
                stat.defensive_actions += 1
            elif etype == "interception":
                stat.defensive_actions += 1
                
            # Recalculate Dynamic Performance Rating
            IntelligenceService.calculate_dynamic_rating(stat)

    @staticmethod
    def calculate_dynamic_rating(stat: PlayerStat):
        """
        AI-driven performance rating logic.
        Combines offensive output, defensive workrate, and physical intensity.
        """
        base = 6.0
        offensive = (stat.shots * 0.4) + (stat.xg * 2.0) + (stat.passes * 0.02)
        defensive = (stat.tackles * 0.3) + (stat.defensive_actions * 0.2)
        physical = (stat.speed * 0.05) + (stat.distance / 2000.0)
        
        stat.rating = min(10.0, base + offensive + defensive + physical)
        stat.tactical_rating = stat.rating # Sync for simplicity

    @staticmethod
    def update_tactical_state(db: Session, match_id: int, data: dict):
        """
        Stores tactical snapshots (Possession, Formation).
        """
        new_snap = TacticalSnapshot(
            match_id=match_id,
            minute=data.get("minute", 0),
            possession_home=data.get("possession_home", 50.0),
            possession_away=data.get("possession_away", 50.0),
            home_formation=data.get("home_formation"),
            away_formation=data.get("away_formation"),
            home_compactness=data.get("home_compactness", 1.0),
            attacking_intensity=data.get("attacking_intensity", 0.5)
        )
        db.add(new_snap)
        db.commit()
