from sqlalchemy.orm import Session
from backend.app.matches.models import Match
from backend.app.database.models import Institution
from datetime import datetime, timedelta
import random

class FixtureGenerator:
    def __init__(self, db: Session):
        self.db = db

    def generate_league_fixtures(self, institution_ids: list, start_date: datetime):
        """
        Generates a round-robin fixture list (First and Second Round).
        """
        fixtures = []
        n = len(institution_ids)
        if n % 2 != 0:
            return None # Requires even number for simple round robin
        
        # Round Robin Algorithm
        for round_num in range(n - 1):
            for i in range(n // 2):
                home = institution_ids[i]
                away = institution_ids[n - 1 - i]
                
                # First Round
                match_date = start_date + timedelta(days=round_num * 7)
                match = Match(
                    home_team_id=home,
                    away_team_id=away,
                    match_date=match_date,
                    round="First Round",
                    status="SCHEDULED"
                )
                fixtures.append(match)

                # Second Round (Reverse)
                match_date_rev = match_date + timedelta(days=20 * 7)
                match_rev = Match(
                    home_team_id=away,
                    away_team_id=home,
                    match_date=match_date_rev,
                    round="Second Round",
                    status="SCHEDULED"
                )
                fixtures.append(match_rev)
            
            # Rotate institution_ids
            institution_ids = [institution_ids[0]] + [institution_ids[-1]] + institution_ids[1:-1]
        
        for f in fixtures:
            self.db.add(f)
        self.db.commit()
        return fixtures
