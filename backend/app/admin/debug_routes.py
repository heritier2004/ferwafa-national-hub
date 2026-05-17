from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.auth.dependencies import RoleChecker, get_current_user
from backend.app.config.database import get_db
from backend.app.utils.crud import CrudMixin
from backend.app.database import models as db_models
from backend.app.admin import routes as admin_routes
from datetime import datetime

router = APIRouter(
    prefix="/debug",
    tags=["debug"],
    dependencies=[Depends(RoleChecker(["SUPER_ADMIN"]))]
)

@router.get("/all", response_model=dict)
def debug_all(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Return a comprehensive diagnostic summary for the whole system.
    Includes:
    * System health stats (CPU, RAM, DB latency, AI node status)
    * Database connectivity check
    * Recent error logs
    * Global statistics (clubs, schools, players)
    * Sample CRUD sanity check for each model (create → read → update → soft‑delete)
    """
    # 1. System health (reuse admin route logic)
    health = admin_routes.get_system_health()

    # 2. DB connectivity
    try:
        db.execute("SELECT 1")
        db_check = {"status": "HEALTHY"}
    except Exception as e:
        db_check = {"status": "UNHEALTHY", "error": str(e)}

    # 3. Recent error logs (limit 10)
    error_logs = db.query(db_models.SystemError).order_by(db_models.SystemError.timestamp.desc()).limit(10).all()

    # 4. Global stats
    stats = admin_routes.get_global_stats(db)

    # 5. Sample CRUD sanity check for a subset of models
    crud_check = {}
    sample_entities = ["user", "institution", "player", "match"]
    for entity in sample_entities:
        Model = getattr(db_models, entity.capitalize())
        # create
        payload = {}
        if entity == "user":
            payload = {"email": f"debug_{entity}_{Model.__name__}@example.com", "full_name": "Debug User", "password_hash": "dummy", "role": "SUPER_ADMIN"}
        elif entity == "institution":
            payload = {"name": f"Debug {entity}", "type": "club", "code": f"DBG-{entity.upper()}", "location": "Debug City"}
        elif entity == "player":
            # need an institution id – use first institution if exists
            inst = db.query(db_models.Institution).first()
            if not inst:
                continue
            payload = {"institution_id": inst.id, "player_code": f"DBG-PLY-{entity.upper()}", "name": "Debug Player", "position": "ST", "jersey_number": 99}
        elif entity == "match":
            # need two institution ids – use first two institutions if exist
            institutions = db.query(db_models.Institution).limit(2).all()
            if len(institutions) < 2:
                continue
            payload = {"home_team_id": institutions[0].id, "away_team_id": institutions[1].id, "stadium": "Debug Stadium", "match_date": "2026-12-31T15:00:00", "competition_id": None}
        try:
            obj = CrudMixin.create(Model, db, payload, actor_id=current_user["id"])
            # read
            read_obj = db.query(Model).filter(Model.id == obj.id, getattr(Model, "is_deleted", False) == False).first()
            # update (set a dummy flag if possible)
            update_data = {}
            if hasattr(obj, "full_name"):
                update_data["full_name"] = "Debug Updated"
            elif hasattr(obj, "name"):
                update_data["name"] = "Debug Updated"
            if update_data:
                CrudMixin.update(Model, db, obj.id, update_data, actor_id=current_user["id"])
            # soft‑delete
            CrudMixin.soft_delete(Model, db, obj.id, actor_id=current_user["id"])
            crud_check[entity] = {"status": "OK", "id": obj.id}
        except Exception as e:
            crud_check[entity] = {"status": "FAIL", "error": str(e)}

    return {
        "system_health": health,
        "db_check": db_check,
        "recent_errors": error_logs,
        "global_stats": stats,
        "crud_sanity": crud_check,
    }

@router.post("/system/repair")
def system_repair(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Global Standard Section 15: Auto-Repair System.
    Identifies and resolves data inconsistencies.
    """
    repairs = []
    
    # 1. ORPHANED RECORDS REPAIR (Parent deleted but children active)
    # Example: Player active but Institution soft-deleted
    orphans = db.query(db_models.Player).join(db_models.Institution).filter(
        db_models.Institution.is_deleted == True,
        db_models.Player.is_deleted == False
    ).all()
    
    for p in orphans:
        p.is_deleted = True
        p.version += 1
        repairs.append(f"Soft-deleted orphan Player {p.name} (ID: {p.id}) - Parent Institution was deleted.")

    # 2. MATCH CONSISTENCY (Match finished but scores missing?)
    # ... more logic could go here
    
    # 3. LOG RECOVERY (Standard Section 15)
    if repairs:
        log = db_models.AuditLog(
            actor_email=current_user.get("email", "SYSTEM"),
            action="AUTO_REPAIR",
            description=f"Auto-Repair executed. Changes: {'; '.join(repairs)}",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    
    return {
        "status": "REPAIR_COMPLETE",
        "repairs_made": len(repairs),
        "details": repairs
    }
