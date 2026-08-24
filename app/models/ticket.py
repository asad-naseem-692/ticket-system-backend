import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import generate_uuid, get_utc_now

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")  # open, in_progress, resolved, closed
    priority = Column(String, nullable=False, default="medium")  # critical, high, medium, low
    customer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    assigned_agent_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    deadline_at = Column(DateTime(timezone=True), nullable=False)
    sla_breached = Column(Boolean, default=False, nullable=False)

    # Relationships
    customer = relationship("User", back_populates="customer_tickets", foreign_keys=[customer_id])
    assigned_agent = relationship("User", back_populates="assigned_tickets", foreign_keys=[assigned_agent_id])
    comments = relationship("Comment", back_populates="ticket", cascade="all, delete-orphan", order_by="Comment.created_at.asc()")
    attachments = relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan", order_by="Attachment.created_at.asc()")
    audit_logs = relationship("AuditLog", back_populates="ticket", cascade="all, delete-orphan", order_by="AuditLog.timestamp.asc()")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "priority": self.priority,
            "customer_id": self.customer_id,
            "assigned_agent_id": self.assigned_agent_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deadline_at": self.deadline_at.isoformat() if self.deadline_at else None,
            "sla_breached": self.sla_breached,
        }
