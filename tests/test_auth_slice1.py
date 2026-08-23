import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, decode_access_token, verify_password, get_password_hash

client = TestClient(app)

def test_signup_successful():
    email = f"testuser_{pytest.helpers_uuid()}@example.com" if hasattr(pytest, "helpers_uuid") else "test_signup_1@example.com"
    # Ensure fresh email
    import uuid
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
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

def test_signup_duplicate_email_rejected():
    import uuid
    email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
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
