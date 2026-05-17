from fastapi import APIRouter, Depends, HTTPException, status, Body, Header, Query
from sqlalchemy.orm import Session
from backend.app.auth.dependencies import get_current_user, RoleChecker
from backend.app.config.database import get_db
from backend.app.utils.crud import CrudMixin, crud_error
from backend.app.database import models as db_models

router = APIRouter(
    prefix="/api/admin/crud",
    tags=["admin-crud"],
    dependencies=[Depends(RoleChecker(["SUPER_ADMIN"]))]
)

def _get_model(entity: str):
    """Return the SQLAlchemy model class for a given entity name.
    Supported entities are the capitalized table names defined in `backend.app.database.models`.
    """
    model_name = entity.capitalize()
    if not hasattr(db_models, model_name):
        raise HTTPException(status_code=404, detail=f"Entity '{entity}' not found")
    return getattr(db_models, model_name)

@router.get("/{entity}")
def list_entities(entity: str, db: Session = Depends(get_db)):
    Model = _get_model(entity)
    return db.query(Model).filter(Model.is_deleted == False).all()

@router.post("/{entity}", status_code=status.HTTP_201_CREATED)
def create_entity(
    entity: str,
    payload: dict = Body(...),
    x_idempotency_key: str = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    Model = _get_model(entity)
    try:
        obj = CrudMixin.create(Model, db, payload, actor_id=current_user["id"], idempotency_key=x_idempotency_key)
        # If idempotency return was cached, 'obj' might be the response dict
        if isinstance(obj, dict):
            return obj
    except Exception as e:
        err = crud_error(str(e), 400, "GENERIC_CRUD")
        raise HTTPException(status_code=400, detail=err)
    return {"id": obj.id, "message": f"{entity.capitalize()} created successfully"}

@router.patch("/{entity}/{obj_id}")
def update_entity(
    entity: str,
    obj_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    Model = _get_model(entity)
    expected_version = payload.pop('expected_version', None)
    try:
        updated = CrudMixin.update(Model, db, obj_id, payload, actor_id=current_user["id"], expected_version=expected_version)
    except ValueError as ve:
        err = crud_error(str(ve), 409, "GENERIC_CRUD")
        raise HTTPException(status_code=409, detail=err)
    except Exception as e:
        err = crud_error(str(e), 400, "GENERIC_CRUD")
        raise HTTPException(status_code=400, detail=err)
    return {"id": updated.id, "message": f"{entity.capitalize()} updated successfully"}

@router.delete("/{entity}/{obj_id}")
def delete_entity(
    entity: str,
    obj_id: int,
    hard: bool = Query(False),
    confirmed: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    Model = _get_model(entity)
    try:
        if hard:
            CrudMixin.hard_delete(Model, db, obj_id, actor_id=current_user["id"], confirmed=confirmed)
            return {"message": f"{entity.capitalize()} PERMANENTLY deleted from system."}
        else:
            CrudMixin.soft_delete(Model, db, obj_id, actor_id=current_user["id"])
            return {"message": f"{entity.capitalize()} soft‑deleted successfully"}
    except ValueError as ve:
        err = crud_error(str(ve), 404, "GENERIC_CRUD")
        raise HTTPException(status_code=404, detail=err)
    except Exception as e:
        err = crud_error(str(e), 400, "GENERIC_CRUD")
        raise HTTPException(status_code=400, detail=err)
