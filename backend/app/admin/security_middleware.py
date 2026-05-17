import time
import uuid
import hashlib
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from backend.app.config.database import SessionLocal
from backend.app.database.models import BlockedIP, InfrastructureLog, SecurityRule

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        client_ip = request.client.host
        start_time = time.time()
        
        # 1. Check for Blocked IPs
        db: Session = SessionLocal()
        try:
            is_blocked = db.query(BlockedIP).filter(BlockedIP.ip_address == client_ip).first()
            if is_blocked:
                return Response(content="ACCESS_DENIED: Infrastructure Quarantine", status_code=403)
            
            # 2. Basic Rate Limiting (Global Threshold)
            # This is a simplified version; in production, use Redis.
            rule = db.query(SecurityRule).filter(SecurityRule.rule_name == "global_rate_limit").first()
            # If we had a counter, we would check it here.

        finally:
            db.close()

        # 3. Process Request
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 4. Infrastructure Logging & Threat Detection
        db = SessionLocal()
        try:
            # Generate a hash of the path/method for tamper-proofing logs
            payload_str = f"{request.method}:{request.url.path}"
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            
            # Determine severity
            severity = "INFO"
            if response.status_code >= 500:
                severity = "ERROR"
            elif response.status_code >= 400:
                severity = "WARNING"
            
            # Threat Detection: Log suspicious activity
            action_type = request.method
            if response.status_code in [401, 403, 404, 429]:
                # For now, we flag as a potential threat if it's a security-related failure.
                if response.status_code in [401, 403]:
                    severity = "CRITICAL"
                    action_type = "AUTH_FAILURE_THREAT"
                else:
                    severity = "WARNING"

            log = InfrastructureLog(
                service="API_GATEWAY",
                action=action_type,
                severity=severity,
                actor_id=client_ip,
                payload_hash=payload_hash,
                description=f"Request {request.url.path} processed in {process_time:.4f}s - Status: {response.status_code}",
                status_code=response.status_code,
                request_id=request_id
            )
            db.add(log)
            db.commit()
            
            # Auto-block if critical (simulated threshold)
            # if severity == "CRITICAL":
            #    new_block = BlockedIP(ip_address=client_ip, reason="Automated Security Block: Multiple Auth Failures")
            #    db.add(new_block)
            #    db.commit()

        except Exception as e:
            print(f"FAILED TO LOG INFRASTRUCTURE ACTION: {e}")
        finally:
            db.close()

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response
