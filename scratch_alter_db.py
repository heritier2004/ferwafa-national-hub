import sys
import os

# Ensure backend module can be resolved
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.config.database import engine
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError

def add_jersey_column():
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE players ADD COLUMN jersey_number INTEGER;"))
            print("Successfully added jersey_number column to players table.")
        except (ProgrammingError, OperationalError) as e:
            if "already exists" in str(e) or "duplicate column" in str(e):
                print("jersey_number column already exists, safe to proceed.")
            else:
                print(f"Error altering table: {e}")

if __name__ == "__main__":
    add_jersey_column()
