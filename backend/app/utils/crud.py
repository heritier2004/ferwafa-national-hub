import contextlib
import json
import uuid
import traceback
from sqlalchemy.orm import Session
from backend.app.database.models import AuditLog, IdempotencyKey, SystemError
from datetime import datetime, timedelta
from typing import Optional, Any, Dict


def crud_error(message: str, code: int, module: str, request_id: str = None):
    """Standardised error payload for CRUD operations as per Global Standard Section 10."""
    return {
        "error_code": code,
        "error_message": message,
        "module": module,
        "request_id": request_id or "N/A",
        "timestamp": datetime.utcnow().isoformat(),
    }


@contextlib.contextmanager
def transactional(session: Session):
    """Wrap a SQLAlchemy session in a transaction (Global Standard Section 7).
    Supports nested transactions via Savepoints. Commits on success, rolls back on any exception.
    """
    # If not in a transaction, start one. 
    # Note: session.begin() returns a transaction object that can be used as a context manager.
    # But since we are already in a context manager, we'll manage it manually.
    
    is_top_level = not session.in_transaction()
    if is_top_level:
        session.begin()
    
    # Always use a savepoint for internal blocks to allow partial rollback if needed,
    # though here we usually want full rollback on any error.
    nested = session.begin_nested()
    
    try:
        yield session
        nested.commit()
        if is_top_level:
            session.commit()
    except Exception as e:
        nested.rollback()
        if is_top_level:
            session.rollback()
        
        # Log to SystemError for forensics using a separate session
        from backend.app.config.database import SessionLocal
        log_db = SessionLocal()
        try:
            error_log = SystemError(
                error_type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc(),
                request_id="N/A"
            )
            log_db.add(error_log)
            log_db.commit()
        except:
            pass
        finally:
            log_db.close()
        raise


class CrudMixin:
    """
    GLOBAL ERROR-FREE CRUD OPERATIONS ENGINE (Standard v6.0)
    Ensures ALL data operations are consistent, secure, atomic, and traceable.
    """

    @staticmethod
    def _check_idempotency(session: Session, key: str, user_id: int) -> Optional[Dict]:
        """Global Standard Section 14: Idempotency protection."""
        if not key:
            return None
        existing = session.query(IdempotencyKey).filter(
            IdempotencyKey.key == key,
            IdempotencyKey.user_id == user_id
        ).first()
        if existing and existing.response_body:
            return json.loads(existing.response_body)
        return None

    @staticmethod
    def _save_idempotency(session: Session, key: str, user_id: int, response: Dict, status_code: int = 200):
        if not key:
            return
        # Set expiration to 24 hours
        expires = datetime.utcnow() + timedelta(hours=24)
        new_key = IdempotencyKey(
            key=key,
            user_id=user_id,
            response_code=status_code,
            response_body=json.dumps(response),
            expires_at=expires
        )
        session.add(new_key)

    @staticmethod
    async def broadcast_sync(Model, action: str, entity_id: Any, data: Dict = None):
        """Global Standard Section 9: Real-time UI Synchronization."""
        # This hook should be implemented to talk to the WebSocket manager
        from backend.app.match_control.ai_ingest import manager
        payload = {
            "type": f"db_{action.lower()}",
            "entity": Model.__tablename__,
            "id": entity_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        # For now, we try to broadcast if it's a match-related entity
        # In a full implementation, this would broadcast to a global channel
        if Model.__tablename__ == "matches" or hasattr(Model, "match_id"):
            match_id = entity_id if Model.__tablename__ == "matches" else getattr(data, "match_id", None)
            if match_id:
                await manager.broadcast_match_event(match_id, payload)

    @staticmethod
    def create(Model, session: Session, data: dict, actor_id: int, idempotency_key: str = None):
        """Standard Section 3: SAFE INSERT"""
        # 1. Idempotency Check
        cached_resp = CrudMixin._check_idempotency(session, idempotency_key, actor_id)
        if cached_resp:
            return cached_resp

        with transactional(session) as tx:
            # 2. VALIDATE & EXECUTE
            obj = Model(**data)
            # Ensure UUID if model supports it (Standard Section 13)
            if hasattr(obj, 'uid') and not obj.uid:
                obj.uid = uuid.uuid4()
            
            tx.add(obj)
            tx.flush()
            
            # 3. LOG (Standard Section 11)
            log = AuditLog(
                actor_email=str(actor_id),
                action="CREATE",
                description=f"Standard Create: {Model.__tablename__} (id={obj.id}) | Data: {json.dumps(data, default=str)}",
                timestamp=datetime.utcnow()
            )
            tx.add(log)
            
            # 4. Idempotency Save
            resp = {"id": obj.id, "status": "CREATED"}
            CrudMixin._save_idempotency(tx, idempotency_key, actor_id, resp, 201)
            
        return obj

    @staticmethod
    def soft_delete(Model, session: Session, obj_id: int, actor_id: int):
        """Standard Section 6: SAFE REMOVAL (SOFT)"""
        with transactional(session) as tx:
            obj = tx.query(Model).filter(Model.id == obj_id, Model.is_deleted == False).first()
            if not obj:
                raise ValueError(f"{Model.__name__} not found or already deleted")
            
            old_data = str({k: getattr(obj, k) for k in obj.__dict__ if not k.startswith('_')})
            obj.is_deleted = True
            obj.version += 1
            
            # Audit log
            log = AuditLog(
                actor_email=str(actor_id),
                action="DELETE_SOFT",
                description=f"Standard Soft-Delete: {Model.__tablename__} (id={obj_id}) | Pre-state: {old_data}",
                timestamp=datetime.utcnow()
            )
            tx.add(log)
        return True

    @staticmethod
    def hard_delete(Model, session: Session, obj_id: int, actor_id: int, confirmed: bool = False):
        """Standard Section 6: SAFE REMOVAL (HARD - RESTRICTED)"""
        if not confirmed:
            raise ValueError("Hard-delete requires explicit double confirmation flag.")
            
        with transactional(session) as tx:
            obj = tx.query(Model).filter(Model.id == obj_id).first()
            if not obj:
                raise ValueError(f"{Model.__name__} not found")
            
            old_data = str({k: getattr(obj, k) for k in obj.__dict__ if not k.startswith('_')})
            tx.delete(obj)
            
            # Audit log
            log = AuditLog(
                actor_email=str(actor_id),
                action="DELETE_HARD",
                description=f"PERMANENT REMOVAL: {Model.__tablename__} (id={obj_id}) | Final State: {old_data}",
                timestamp=datetime.utcnow()
            )
            tx.add(log)
        return True

    @staticmethod
    def update(Model, session: Session, obj_id: int, updates: dict, actor_id: int, expected_version: int = None):
        """Standard Section 5: SAFE MODIFY"""
        with transactional(session) as tx:
            # 1. LOCK & CHECK (Optimistic Locking)
            obj = tx.query(Model).filter(Model.id == obj_id, Model.is_deleted == False).first()
            if not obj:
                raise ValueError(f"{Model.__name__} not found")
            
            if expected_version is not None and obj.version != expected_version:
                raise ValueError(f"CONCURRENCY CONFLICT: {Model.__name__} version {obj.version} does not match expected {expected_version}")
            
            old_state = {k: getattr(obj, k) for k in updates.keys() if hasattr(obj, k)}
            
            # 2. EXECUTE
            for key, value in updates.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            
            obj.version += 1
            
            # 3. LOG
            log = AuditLog(
                actor_email=str(actor_id),
                action="UPDATE",
                description=f"Standard Update: {Model.__tablename__} (id={obj_id}) | Diff: {json.dumps(updates, default=str)}",
                timestamp=datetime.utcnow()
            )
            tx.add(log)
        return obj
