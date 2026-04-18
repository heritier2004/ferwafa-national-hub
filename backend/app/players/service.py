from sqlalchemy.orm import Session
from backend.app.players.models import Player
from backend.app.database.models import Institution

class PlayerService:
    @staticmethod
    def get_all_players(db: Session, institution_id: int = None):
        query = db.query(Player)
        if institution_id:
            query = query.filter(Player.institution_id == institution_id)
        return query.all()

    @staticmethod
    def create_player(db: Session, player_data: dict):
        new_player = Player(**player_data)
        db.add(new_player)
        db.commit()
        db.refresh(new_player)
        return new_player

    @staticmethod
    def generate_player_code(db: Session, institution_id: int):
        inst = db.query(Institution).filter(Institution.id == institution_id).first()
        prefix = inst.code if inst else "PLR"
        count = db.query(Player).filter(Player.institution_id == institution_id).count()
        return f"{prefix}-{str(count + 1).zfill(3)}"
