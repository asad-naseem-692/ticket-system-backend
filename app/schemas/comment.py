from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse

CommentVisibility = Literal["internal", "public"]

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    visibility: CommentVisibility = "public"

class CommentResponse(BaseModel):
    id: str
    ticket_id: str
    author_id: str
    visibility: CommentVisibility
    content: str
    created_at: datetime
    author: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
