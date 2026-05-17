import sys
import os
from datetime import datetime
import uuid

# Ensure we can import from backend
sys.path.append(os.getcwd())

from backend.app.config.database import SessionLocal
from backend.app.database.models import Match, MatchEvent, Institution
from backend.app.live.intelligence import IntelligenceService

def test_session_isolation():
    db = SessionLocal()
    print("--- STARTING SESSION ISOLATION TEST ---")
    
    try:
        # 1. SETUP: Find or Create two institutions
        insts = db.query(Institution).limit(2).all()
        if len(insts) < 2:
            print("Creating test institutions...")
            inst1 = Institution(name="Test Alpha", type="club", code="ALPHA", location="Kigali")
            inst2 = Institution(name="Test Beta", type="club", code="BETA", location="Kigali")
            db.add_all([inst1, inst2])
            db.commit()
            insts = [inst1, inst2]
        
        # 2. CREATE MATCH ALPHA
        match_a = Match(
            home_team_id=insts[0].id,
            opponent_name="Opponent A",
            stadium="Alpha Stadium",
            match_date=datetime.utcnow(),
            status="LIVE",
            match_token=f"TOKEN-ALPHA-{uuid.uuid4().hex[:8]}",
            api_key=f"KEY-ALPHA-{uuid.uuid4().hex[:8]}",
            score_home=0,
            score_away=0
        )
        db.add(match_a)
        
        # 3. CREATE MATCH BETA
        match_b = Match(
            home_team_id=insts[1].id,
            opponent_name="Opponent B",
            stadium="Beta Stadium",
            match_date=datetime.utcnow(),
            status="LIVE",
            match_token=f"TOKEN-BETA-{uuid.uuid4().hex[:8]}",
            api_key=f"KEY-BETA-{uuid.uuid4().hex[:8]}",
            score_home=0,
            score_away=0
        )
        db.add(match_b)
        db.commit()
        
        print(f"Match Alpha ID: {match_a.id}")
        print(f"Match Beta ID:  {match_b.id}")

        # 4. SIMULATE AI EVENTS FOR ALPHA
        print("\nStep 4: Simulating GOAL for Match Alpha...")
        IntelligenceService.process_ai_event(db, match_a.id, {
            "event_type": "goal",
            "team": "home",
            "ai_confidence": 0.95,
            "source_event_id": f"evt_a_{uuid.uuid4().hex}"
        })
        
        # 5. SIMULATE AI EVENTS FOR BETA
        print("Step 5: Simulating YELLOW_CARD for Match Beta...")
        IntelligenceService.process_ai_event(db, match_b.id, {
            "event_type": "yellow_card",
            "team": "home",
            "ai_confidence": 0.90,
            "source_event_id": f"evt_b_{uuid.uuid4().hex}"
        })
        
        db.commit()

        # 6. VERIFICATION
        print("\n--- VERIFYING ISOLATION ---")
        
        # Check Alpha Events
        alpha_events = db.query(MatchEvent).filter(MatchEvent.match_id == match_a.id).all()
        print(f"Match Alpha Events: {[e.event_type for e in alpha_events]}")
        if len(alpha_events) != 1 or alpha_events[0].event_type != "goal":
            raise Exception("Match Alpha event mismatch!")
        
        # Check Beta Events
        beta_events = db.query(MatchEvent).filter(MatchEvent.match_id == match_b.id).all()
        print(f"Match Beta Events:  {[e.event_type for e in beta_events]}")
        if len(beta_events) != 1 or beta_events[0].event_type != "yellow_card":
            raise Exception("Match Beta event mismatch!")
        
        # Check Scores
        db.refresh(match_a)
        db.refresh(match_b)
        print(f"Match Alpha Score: {match_a.score_home}-{match_a.score_away}")
        print(f"Match Beta Score:  {match_b.score_home}-{match_b.score_away}")
        
        if match_a.score_home != 1 or match_b.score_home != 0:
            raise Exception("Match Score isolation failed!")
        
        print("\n[SUCCESS] ISOLATION VERIFIED: Data is strictly separated by match_id.")

    except Exception as e:
        print(f"\n[FAIL] Test Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 7. CLEANUP
        print("\nCleaning up test matches...")
        try:
            if 'match_a' in locals(): db.delete(match_a)
            if 'match_b' in locals(): db.delete(match_b)
            db.commit()
        except:
            pass
        db.close()

if __name__ == "__main__":
    test_session_isolation()
