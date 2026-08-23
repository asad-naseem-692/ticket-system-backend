from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, ConfigDict

class UserBase(BaseModel):
    name: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Literal["customer", "agent", "admin"] = "customer"

class UserResponse(UserBase):
    id: str
    role: Literal["customer", "agent", "admin"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
