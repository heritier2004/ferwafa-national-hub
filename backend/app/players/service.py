from sqlalchemy.orm import Session
from backend.app.database.models import Player, Institution
from backend.app.utils.crud import CrudMixin

class PlayerService:
    @staticmethod
    def get_all_players(db: Session, institution_id: int = None):
        query = db.query(Player).filter(Player.is_deleted == False)
        if institution_id:
            query = query.filter(Player.institution_id == institution_id)
        return query.all()

    @staticmethod
    def create_player(db: Session, player_data: dict, actor_id: int):
        return CrudMixin.create(Player, db, player_data, actor_id=actor_id)

    @staticmethod
    def update_player(db: Session, player_id: int, player_data: dict, actor_id: int):
        expected_version = player_data.pop('expected_version', None)
        return CrudMixin.update(Player, db, player_id, player_data, actor_id=actor_id, expected_version=expected_version)

    @staticmethod
    def delete_player(db: Session, player_id: int, actor_id: int):
        try:
            return CrudMixin.soft_delete(Player, db, player_id, actor_id=actor_id)
        except ValueError:
            return False

    @staticmethod
    def generate_player_code(db: Session, institution_id: int):
        inst = db.query(Institution).filter(Institution.id == institution_id).first()
        prefix = inst.code if inst else "PLR"
        
        # Find the highest existing code for this institution to ensure absolute uniqueness
        last_player = db.query(Player).filter(Player.institution_id == institution_id).order_by(Player.id.desc()).first()
        
        if not last_player:
            new_num = 1
        else:
            try:
                # Try to extract the number from the last code (e.g., AMAV-2026-015 -> 15)
                parts = last_player.player_code.split('-')
                new_num = int(parts[-1]) + 1
            except:
                # Fallback to count if format is weird
                new_num = db.query(Player).filter(Player.institution_id == institution_id).count() + 1
        
        return f"{prefix}-{str(new_num).zfill(3)}"
