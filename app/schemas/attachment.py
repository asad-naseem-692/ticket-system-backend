from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse

class AttachmentResponse(BaseModel):
    id: str
    ticket_id: str
    uploaded_by: str
    filename: str
    url: str
    size_bytes: int
    created_at: datetime
    uploader: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
