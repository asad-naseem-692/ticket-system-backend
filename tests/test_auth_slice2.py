import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

client = TestClient(app)

@pytest.fixture
def created_user():
    """Creates a temporary test user and guarantees cleanup."""
    db = SessionLocal()
    email = f"test_login_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "TestSecretPassword123!"
    user = User(
        name="Slice2 Test User",
        email=email,
        hashed_password=get_password_hash(pwd),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    user_info = {
        "id": user.id,
        "email": email,
        "password": pwd,
        "name": user.name,
        "role": user.role,
    }
    db.close()

    yield user_info

    # Cleanup
    clean_db = SessionLocal()
    try:
        clean_db.query(User).filter(User.email == email).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_login_success(created_user):
    response = client.post(
        "/auth/login",
        json={
            "email": created_user["email"],
            "password": created_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == created_user["email"]
    assert data["user"]["role"] == "customer"
    assert "hashed_password" not in data["user"]

def test_login_invalid_password(created_user):
    response = client.post(
        "/auth/login",
        json={
            "email": created_user["email"],
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_login_nonexistent_email():
    response = client.post(
        "/auth/login",
        json={
            "email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com",
            "password": "AnyPassword123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

def test_auth_me_with_valid_token(created_user):
    login_res = client.post(
        "/auth/login",
        json={
            "email": created_user["email"],
            "password": created_user["password"],
        },
    )
    token = login_res.json()["access_token"]

    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == created_user["id"]
    assert me_data["email"] == created_user["email"]
    assert me_data["role"] == created_user["role"]

def test_auth_me_without_token():
    res = client.get("/auth/me")
    assert res.status_code == 401
    assert res.json()["detail"] == "Not authenticated"

def test_logout_endpoint():
    res = client.post("/auth/logout")
    assert res.status_code == 200
    assert res.json()["detail"] == "Successfully logged out"
