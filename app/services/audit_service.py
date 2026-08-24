from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog

def log_audit_event(
    db: Session,
    ticket_id: str,
    actor_id: str,
    action: str,
    details: Optional[str] = None,
) -> AuditLog:
    """
    Creates an immutable audit log entry for any significant ticket state changes (FEAT-33).
    """
    entry = AuditLog(
        ticket_id=ticket_id,
        actor_id=actor_id,
        action=action,
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
