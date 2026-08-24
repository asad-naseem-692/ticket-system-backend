from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import generate_uuid, get_utc_now

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)  # 'created', 'assigned', 'reassigned', 'priority_override', 'status_change', 'closed', 'comment_added'
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="audit_logs")
    actor = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
