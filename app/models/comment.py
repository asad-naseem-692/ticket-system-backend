from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import generate_uuid, get_utc_now

class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    ticket_id = Column(String, ForeignKey("tickets.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    visibility = Column(String, nullable=False, default="public")  # 'internal' or 'public'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author_id": self.author_id,
            "visibility": self.visibility,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
