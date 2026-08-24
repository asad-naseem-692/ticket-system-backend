from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import generate_uuid, get_utc_now

class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    url = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="attachments")
    uploader = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "uploaded_by": self.uploaded_by,
            "filename": self.filename,
            "url": self.url,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
