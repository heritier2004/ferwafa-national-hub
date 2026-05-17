
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to sys.path to import local modules
sys.path.append(os.getcwd())

DATABASE_URL = "postgresql://postgres:ANGEU@localhost:5432/football_intelligence"
engine = create_engine(DATABASE_URL)

_MATCH_MIGRATIONS = [
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS api_key VARCHAR UNIQUE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS match_token VARCHAR UNIQUE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS opponent_name VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_type VARCHAR DEFAULT 'League'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_home_color VARCHAR DEFAULT '#FF0000'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_home_socks_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_color VARCHAR DEFAULT '#0000FF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS kit_away_socks_color VARCHAR DEFAULT '#FFFFFF'",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_id INTEGER",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS is_finalized BOOLEAN DEFAULT FALSE",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS location_id VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS region VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS venue_quality FLOAT DEFAULT 1.0",
    "ALTER TABLE matches ADD COLUMN IF NOT EXISTS division_name VARCHAR",
]

_GLOBAL_MIGRATIONS = [
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS stadium_name VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS province VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS sector VARCHAR",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS cell VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS photo_url TEXT",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS age INTEGER",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS location_id VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS region VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS district VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS team_category VARCHAR",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS talent_score FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS is_elite_prospect BOOLEAN DEFAULT FALSE",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS potential_score FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS growth_curve FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS injury_risk FLOAT DEFAULT 0.0",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS fatigue_index FLOAT DEFAULT 0.0",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS national_ranking INTEGER",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS sprint_distance FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS stamina_index FLOAT DEFAULT 1.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS tactical_rating FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS xg FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS pass_accuracy FLOAT DEFAULT 0.0",
    "ALTER TABLE player_stats ADD COLUMN IF NOT EXISTS defensive_actions INTEGER DEFAULT 0",
    "ALTER TABLE institutions ADD COLUMN IF NOT EXISTS contact VARCHAR",
]

_EVENT_MIGRATIONS = [
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS ai_confidence FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS ocr_conf FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS det_conf FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS track_conf FLOAT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS is_confirmed BOOLEAN DEFAULT TRUE",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'manual'",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS is_voided BOOLEAN DEFAULT FALSE",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS parent_event_id INTEGER",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS original_ai_payload TEXT",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS source_event_id VARCHAR",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS server_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS value FLOAT DEFAULT 1.0",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS editor_id INTEGER",
    "ALTER TABLE match_events ADD COLUMN IF NOT EXISTS audit_reason VARCHAR",
]

_COMPETITION_MIGRATIONS = [
    "ALTER TABLE competitions ADD COLUMN IF NOT EXISTS category VARCHAR",
    "ALTER TABLE competitions ADD COLUMN IF NOT EXISTS rules TEXT",
]

def run_migrations():
    all_migrations = _MATCH_MIGRATIONS + _GLOBAL_MIGRATIONS + _EVENT_MIGRATIONS + _COMPETITION_MIGRATIONS
    
    with engine.connect() as conn:
        print(f"Applying {len(all_migrations)} migrations...")
        for sql in all_migrations:
            try:
                conn.execute(text(sql))
                print(f"SUCCESS: {sql}")
            except Exception as e:
                print(f"FAILED: {sql} | Error: {e}")
        conn.commit()
        print("Migrations complete.")

if __name__ == "__main__":
    run_migrations()
