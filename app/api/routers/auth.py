from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

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
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash the password
    hashed_pwd = get_password_hash(user_in.password)

    # Enforce role assignment (default: customer)
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
