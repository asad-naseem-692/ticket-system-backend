from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse
from app.schemas.comment import CommentResponse
from app.schemas.attachment import AttachmentResponse

TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
TicketPriority = Literal["critical", "high", "medium", "low"]

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    category: str = Field(..., min_length=2, max_length=100)

class TicketStatusUpdate(BaseModel):
    status: TicketStatus

class TicketPriorityUpdate(BaseModel):
    priority: TicketPriority

class TicketAssignRequest(BaseModel):
    agent_id: str

class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    status: TicketStatus
    priority: TicketPriority
    customer_id: str
    assigned_agent_id: Optional[str] = None
    created_at: datetime
    deadline_at: datetime
    sla_breached: bool

    model_config = ConfigDict(from_attributes=True)

class TicketDetailResponse(TicketResponse):
    customer: Optional[UserResponse] = None
    assigned_agent: Optional[UserResponse] = None
    comments: List[CommentResponse] = []
    attachments: List[AttachmentResponse] = []
