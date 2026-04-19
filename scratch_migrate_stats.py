import sys
import os

# Ensure backend module can be resolved
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config.database import engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

def run_migration():
    """Safely adds new stat columns and the MatchAnalytics table."""
    with engine.connect() as conn:
        print("--- RUNNING ADVANCED STATS MIGRATION ---")
        
        # 1. Add columns to player_stats
        cols = [
            ("assists", "INTEGER DEFAULT 0"),
            ("shots", "INTEGER DEFAULT 0"),
            ("passes", "INTEGER DEFAULT 0"),
            ("tackles", "INTEGER DEFAULT 0"),
            ("saves", "INTEGER DEFAULT 0"),
            ("minutes_played", "INTEGER DEFAULT 0")
        ]
        
        for col_name, col_type in cols:
            try:
                conn.execute(text(f"ALTER TABLE player_stats ADD COLUMN {col_name} {col_type}"))
                print(f"Added column: {col_name}")
            except OperationalError:
                print(f"Column {col_name} already exists. Skipping.")
        
        # 2. Create MatchAnalytics table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS match_analytics (
                    id SERIAL PRIMARY KEY,
                    match_id INTEGER REFERENCES matches(id),
                    minute INTEGER,
                    possession_home REAL,
                    possession_away REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("Table 'match_analytics' verified/created.")
        except Exception as e:
            print(f"Error creating match_analytics: {e}")
            
        conn.commit()
        print("--- MIGRATION COMPLETE ---")

if __name__ == "__main__":
    run_migration()
