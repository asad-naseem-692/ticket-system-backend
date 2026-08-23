from typing import Literal, Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user import UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserResponse

class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int

class RequestResetRequest(BaseModel):
    email: EmailStr

class RequestResetResponse(BaseModel):
    detail: str
    reset_token: Optional[str] = None

class ConfirmResetRequest(BaseModel):
    token: str
    new_password: str

class ConfirmResetResponse(BaseModel):
    detail: str
