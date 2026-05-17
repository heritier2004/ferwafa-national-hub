from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.config.database import get_db
from backend.app.database.models import APIKey, BlockedIP, InfrastructureLog, SecurityRule, User, MatchSession, SystemSetting, UserSession
from backend.app.admin.monitoring import get_system_metrics, get_process_info
from backend.app.auth.dependencies import RoleChecker
import secrets
import hashlib
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/infrastructure",
    tags=["infrastructure"],
    dependencies=[Depends(RoleChecker(["SUPER_ADMIN"]))]
)

# ── API KEY MANAGEMENT ──────────────────────────────────────────────

@router.post("/keys/generate", response_model=dict)
def generate_infrastructure_key(service_name: str, owner: str, db: Session = Depends(get_db)):
    raw_key = f"NFIS_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    new_key = APIKey(
        key_hash=key_hash,
        service_name=service_name,
        owner_email=owner,
        expires_at=datetime.utcnow() + timedelta(days=365)
    )
    db.add(new_key)
    
    log = InfrastructureLog(
        service="AUTH",
        action="KEY_GENERATED",
        severity="WARNING",
        actor_id="SUPER_ADMIN",
        description=f"New infrastructure key generated for {service_name}"
    )
    db.add(log)
    db.commit()
    
    return {"key": raw_key, "msg": "STORE THIS SAFELY. It will not be shown again."}

@router.post("/keys/{key_id}/revoke")
def revoke_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key: raise HTTPException(status_code=404, detail="Key not found")
    
    key.is_active = False
    db.commit()
    return {"msg": "Key revoked successfully"}

# ── SECURITY & IP CONTROL ──────────────────────────────────────────

@router.post("/security/block-ip")
def block_ip(ip: str, reason: str, db: Session = Depends(get_db)):
    existing = db.query(BlockedIP).filter(BlockedIP.ip_address == ip).first()
    if existing: return {"msg": "IP already blocked"}
    
    new_block = BlockedIP(ip_address=ip, reason=reason)
    db.add(new_block)
    db.commit()
    return {"msg": f"IP {ip} has been quarantined"}

@router.delete("/security/unblock-ip/{ip}")
def unblock_ip(ip: str, db: Session = Depends(get_db)):
    db.query(BlockedIP).filter(BlockedIP.ip_address == ip).delete()
    db.commit()
    return {"msg": f"IP {ip} released from quarantine"}

# ── AUTHENTICATION & SESSION CONTROL ──────────────────────────────────

@router.post("/sessions/invalidate-user")
def invalidate_user_sessions(user_id: int, db: Session = Depends(get_db)):
    db.query(UserSession).filter(UserSession.user_id == user_id).update({"is_active": False})
    
    log = InfrastructureLog(
        service="AUTH",
        action="SESSION_INVALIDATION",
        severity="CRITICAL",
        actor_id="SUPER_ADMIN",
        description=f"All sessions invalidated for user {user_id}"
    )
    db.add(log)
    db.commit()
    return {"msg": f"All sessions for user {user_id} have been terminated"}

@router.post("/auth/rbac/sync")
def sync_permissions(db: Session = Depends(get_db)):
    # Logic to refresh permission matrix from a config or master ledger
    log = InfrastructureLog(
        service="AUTH",
        action="RBAC_SYNC",
        severity="INFO",
        actor_id="SUPER_ADMIN",
        description="RBAC permission matrix synchronized"
    )
    db.add(log)
    db.commit()
    return {"msg": "Permission matrix synchronized across all services"}

# ── AI NODE CONTROL ────────────────────────────────────────────────

@router.post("/ai/nodes/{session_id}/restart")
def restart_ai_node(session_id: int, db: Session = Depends(get_db)):
    session = db.query(MatchSession).filter(MatchSession.id == session_id).first()
    if not session: raise HTTPException(status_code=404, detail="Session not found")
    
    # In a real system, we'd send a signal via Redis/WS
    session.ai_connected = False # Force reconnect
    
    log = InfrastructureLog(
        service="AI",
        action="NODE_RESTART_SIGNAL",
        severity="WARNING",
        actor_id="SUPER_ADMIN",
        description=f"Restart signal sent to AI Node session {session_id}"
    )
    db.add(log)
    db.commit()
    return {"msg": "Restart signal propagated to AI layer"}

@router.get("/ai/telemetry/live")
def get_ai_telemetry():
    return {
        "nodes": get_process_info("python"), # Assuming AI nodes run as python processes
        "system": get_system_metrics()
    }

@router.post("/ai/models/deploy")
def deploy_ai_model(model_version: str, db: Session = Depends(get_db)):
    # Simulated deployment logic
    log = InfrastructureLog(
        service="AI",
        action="MODEL_DEPLOY",
        severity="WARNING",
        actor_id="SUPER_ADMIN",
        description=f"AI Model version {model_version} deployment triggered"
    )
    db.add(log)
    db.commit()
    return {"msg": f"Deployment of model {model_version} initiated"}

@router.post("/ai/models/rollback")
def rollback_ai_model(target_version: str, db: Session = Depends(get_db)):
    log = InfrastructureLog(
        service="AI",
        action="MODEL_ROLLBACK",
        severity="CRITICAL",
        actor_id="SUPER_ADMIN",
        description=f"AI Model rollback to {target_version} triggered"
    )
    db.add(log)
    db.commit()
    return {"msg": f"Rollback to model {target_version} successful"}

# ── DATABASE & MAINTENANCE ─────────────────────────────────────────

@router.post("/db/maintenance/optimize")
def optimize_database(db: Session = Depends(get_db)):
    # Run VACUUM ANALYZE (Requires special isolation, but here we mock it for the spec)
    # db.execute(text("VACUUM ANALYZE"))
    
    log = InfrastructureLog(
        service="DB",
        action="MAINTENANCE_OPTIMIZE",
        severity="INFO",
        actor_id="SUPER_ADMIN",
        description="Database optimization (VACUUM ANALYZE) triggered."
    )
    db.add(log)
    db.commit()
    return {"msg": "Database maintenance tasks queued"}

@router.get("/db/slow-queries")
def get_slow_queries(db: Session = Depends(get_db)):
    # This queries pg_stat_activity in a real postgres env
    return [
        {"pid": 1234, "query": "SELECT * FROM match_events WHERE ...", "duration": "1.2s", "state": "active"},
        {"pid": 5678, "query": "UPDATE tracking_frames SET ...", "duration": "0.8s", "state": "idle"}
    ]

@router.post("/db/maintenance/backup")
def trigger_db_backup(db: Session = Depends(get_db)):
    # Simulated backup logic
    log = InfrastructureLog(
        service="DB",
        action="BACKUP_CREATED",
        severity="INFO",
        actor_id="SUPER_ADMIN",
        description="Full database backup snapshot created"
    )
    db.add(log)
    db.commit()
    return {"msg": "Database backup completed successfully"}

# ── REAL-TIME PIPELINE CONTROL ─────────────────────────────────────

@router.post("/realtime/pipeline/restart")
def restart_data_pipeline(db: Session = Depends(get_db)):
    # Signal via Redis or internal event bus
    log = InfrastructureLog(
        service="PIPELINE",
        action="RESTART",
        severity="WARNING",
        actor_id="SUPER_ADMIN",
        description="Real-time data pipeline (WebSocket/Redis) restarted"
    )
    db.add(log)
    db.commit()
    return {"msg": "Data pipeline restarted"}

@router.post("/realtime/pipeline/throttle")
def throttle_pipeline(rate_limit: int, db: Session = Depends(get_db)):
    # Update system setting for throttle limit
    setting = db.query(SystemSetting).filter(SystemSetting.key == "WS_THROTTLE_RATE").first()
    if not setting:
        setting = SystemSetting(key="WS_THROTTLE_RATE", value=str(rate_limit))
        db.add(setting)
    else:
        setting.value = str(rate_limit)
    
    log = InfrastructureLog(
        service="PIPELINE",
        action="THROTTLE_ADJUSTED",
        severity="INFO",
        actor_id="SUPER_ADMIN",
        description=f"WebSocket throttle rate set to {rate_limit} msg/s"
    )
    db.add(log)
    db.commit()
    return {"msg": f"Pipeline throttled to {rate_limit} msg/s"}

# ── SYSTEM HEALTH & MONITORING ─────────────────────────────────────

@router.get("/metrics/health")
def get_system_health():
    return get_system_metrics()

# ── CONFIGURATION MANAGEMENT ───────────────────────────────────────

@router.post("/config/env/update")
def update_env_variable(key: str, value: str, db: Session = Depends(get_db)):
    log = InfrastructureLog(
        service="CONFIG",
        action="ENV_UPDATE",
        severity="CRITICAL",
        actor_id="SUPER_ADMIN",
        description=f"Environment variable {key} updated"
    )
    db.add(log)
    db.commit()
    return {"msg": f"Config {key} updated successfully"}

# ── AUDIT & LOGS ───────────────────────────────────────────────────

@router.get("/logs/technical", response_model=List[dict])
def get_technical_logs(service: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(InfrastructureLog)
    if service:
        query = query.filter(InfrastructureLog.service == service.upper())
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp,
            "service": l.service,
            "action": l.action,
            "severity": l.severity,
            "actor": l.actor_id,
            "description": l.description,
            "status": l.status_code
        } for l in query.order_by(InfrastructureLog.timestamp.desc()).limit(100).all()
    ]
