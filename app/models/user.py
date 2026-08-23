import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")  # "customer", "agent", "admin"
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    customer_tickets = relationship("Ticket", back_populates="customer", foreign_keys="[Ticket.customer_id]")
    assigned_tickets = relationship("Ticket", back_populates="assigned_agent", foreign_keys="[Ticket.assigned_agent_id]")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
