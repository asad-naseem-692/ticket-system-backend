from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import generate_uuid, get_utc_now

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # 'sla_breach', 'sla_warning', 'status_change', 'assignment'
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    read = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User")
    ticket = relationship("Ticket")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticket_id": self.ticket_id,
            "type": self.type,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read": self.read,
        }
