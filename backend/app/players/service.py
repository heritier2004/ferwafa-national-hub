from sqlalchemy.orm import Session
from backend.app.database.models import Player, Institution
from backend.app.utils.crud import CrudMixin

def get_institution_prefix(name: str) -> str:
    """Generate a 3‑character uppercase prefix from the institution name.
    Rules:
    * Remove spaces and non‑alphanumeric characters.
    * Use the first three meaningful letters.
    * Fallback to 'PLR' if name is empty.
    """
    if not name:
        return "PLR"
    # Clean name: keep alphanumeric, uppercase
    cleaned = "".join([c for c in name if c.isalnum()]).upper()
    if len(cleaned) >= 3:
        return cleaned[:3]
    return cleaned.ljust(3, "X")

def generate_unique_institution_code(db: Session, prefix: str) -> str:
    """Return a unique institution code based on the prefix.
    If the prefix already exists, append a numeric suffix.
    """
    existing_codes = db.query(Institution.code).filter(Institution.code.like(f"{prefix}%")).all()
    if not existing_codes:
        return prefix
    suffix_numbers = []
    for (code,) in existing_codes:
        suffix = code[len(prefix):]
        if suffix.isdigit():
            suffix_numbers.append(int(suffix))
        else:
            suffix_numbers.append(0)
    next_suffix = max(suffix_numbers) + 1
    return f"{prefix}{next_suffix}"

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
        prefix = get_institution_prefix(inst.name) if inst else "PLR"
        
        # Find the highest existing code for this institution to ensure absolute uniqueness
        last_player = db.query(Player).filter(Player.institution_id == institution_id).order_by(Player.id.desc()).first()
        
        if not last_player:
            new_num = 1
        else:
            try:
                # Try to extract the number from the last code (e.g., AMAV-117 -> 117 or RYN-0001 -> 1)
                parts = last_player.player_code.split('-')
                new_num = int(parts[-1]) + 1
            except:
                # Fallback to count if format is weird
                new_num = db.query(Player).filter(Player.institution_id == institution_id).count() + 1
        
        return f"{prefix}-{str(new_num).zfill(4)}"
