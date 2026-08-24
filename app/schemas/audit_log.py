from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse

class AuditLogResponse(BaseModel):
    id: str
    ticket_id: str
    actor_id: str
    action: str
    details: Optional[str] = None
    timestamp: datetime
    actor: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
