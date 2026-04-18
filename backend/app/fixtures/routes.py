from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.config.database import get_db
from backend.app.fixtures.generator import FixtureGenerator
from backend.app.database.models import Institution
from datetime import datetime

router = APIRouter(prefix="/fixtures", tags=["fixtures"])

@router.post("/generate")
def generate_fixtures(db: Session = Depends(get_db)):
    institutions = db.query(Institution).all()
    inst_ids = [inst.id for inst in institutions]
    if len(inst_ids) < 2 or len(inst_ids) % 2 != 0:
        raise HTTPException(status_code=400, detail="Requires even number of institutions (min 2)")
    
    generator = FixtureGenerator(db)
    fixtures = generator.generate_league_fixtures(inst_ids, datetime.utcnow())
    return {"message": f"Generated {len(fixtures)} fixtures across two rounds."}
