from datetime import datetime
from pydantic import BaseModel, ConfigDict

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    ticket_id: str
    type: str
    message: str
    created_at: datetime
    read: bool

    model_config = ConfigDict(from_attributes=True)

class NotificationMarkReadRequest(BaseModel):
    read: bool = True
