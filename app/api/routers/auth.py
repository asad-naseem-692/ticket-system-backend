import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token,
    get_current_user,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import (
    LoginRequest,
    AuthResponse,
    RequestResetRequest,
    RequestResetResponse,
    ConfirmResetRequest,
    ConfirmResetResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user account with hashed password and role assignment.
    Rejects registration if the email is already in use.
    """
    existing_user = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed_pwd = get_password_hash(user_in.password)
    assigned_role = user_in.role if user_in.role in ["customer", "agent", "admin"] else "customer"

    new_user = User(
        name=user_in.name.strip(),
        email=user_in.email.lower().strip(),
        hashed_password=hashed_pwd,
        role=assigned_role,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User sign in and token issuance",
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Verifies user credentials and issues a signed JWT token containing user id and role.
    Returns generic 401 error on invalid credentials without exposing which field failed.
    """
    user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user_id=user.id, role=user.role)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }

@router.post(
    "/logout",
    summary="User sign out",
)
def logout():
    """
    Client-side session termination endpoint. Returns confirmation message.
    """
    return {"detail": "Successfully logged out"}

@router.post(
    "/request-reset",
    response_model=RequestResetResponse,
    summary="Request a password reset token",
)
def request_password_reset(req: RequestResetRequest, db: Session = Depends(get_db)):
    """
    Generates a short-lived single-use password reset token for the specified user.
    Always returns a generic confirmation message to prevent email enumeration.
    """
    norm_email = req.email.lower().strip()
    user = db.query(User).filter(User.email == norm_email).first()

    reset_token = None
    if user:
        reset_token = create_password_reset_token(email=user.email, expires_minutes=15)
        logger.info(f"Password reset token requested for {user.email}: {reset_token}")

    return {
        "detail": "Password reset instructions have been generated if an account exists for this email.",
        "reset_token": reset_token,
    }

@router.post(
    "/confirm-reset",
    response_model=ConfirmResetResponse,
    summary="Confirm password reset with valid token",
)
def confirm_password_reset(req: ConfirmResetRequest, db: Session = Depends(get_db)):
    """
    Verifies reset token, hashes the new password, and updates user credentials.
    """
    email = verify_password_reset_token(req.token)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found",
        )

    user.hashed_password = get_password_hash(req.new_password)
    db.commit()

    return {"detail": "Password has been reset successfully"}

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current logged-in user profile",
)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns the authenticated user details matching the verified JWT token.
    """
    return current_user
