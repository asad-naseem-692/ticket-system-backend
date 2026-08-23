import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import (
    create_access_token,
    decode_access_token,
    verify_password,
    get_password_hash,
)

client = TestClient(app)

@pytest.fixture
def created_emails():
    """Tracks test emails created during tests and guarantees database cleanup."""
    emails = []
    yield emails
    # Cleanup created test users from the database
    if emails:
        db = SessionLocal()
        try:
            db.query(User).filter(User.email.in_(emails)).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

def test_signup_successful(created_emails):
    email = f"test_signup_{uuid.uuid4().hex[:8]}@example.com"
    created_emails.append(email)

    response = client.post(
        "/auth/signup",
        json={
            "name": "Jane Customer",
            "email": email,
            "password": "Password123!",
            "role": "customer",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Customer"
    assert data["email"] == email
    assert data["role"] == "customer"
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data

def test_signup_duplicate_email_rejected(created_emails):
    email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
    created_emails.append(email)

    res1 = client.post(
        "/auth/signup",
        json={
            "name": "First User",
            "email": email,
            "password": "Password123!",
            "role": "customer",
        },
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/auth/signup",
        json={
            "name": "Second User",
            "email": email,
            "password": "Password456!",
            "role": "customer",
        },
    )
    assert res2.status_code == 400
    assert res2.json()["detail"] == "Email already registered"

def test_jwt_token_generation_and_decode():
    token = create_access_token(user_id="user-123", role="customer")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "customer"
    assert "exp" in payload

def test_password_hashing():
    pwd = "SecretPassword123!"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
