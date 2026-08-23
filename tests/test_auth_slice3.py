import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash, create_password_reset_token

client = TestClient(app)

@pytest.fixture
def temp_user():
    """Creates a temporary test user and guarantees cleanup."""
    db = SessionLocal()
    email = f"reset_test_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "InitialPassword123!"
    user = User(
        name="Reset Test User",
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

def test_request_reset_existing_user(temp_user):
    response = client.post(
        "/auth/request-reset",
        json={"email": temp_user["email"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert data["reset_token"] is not None
    assert len(data["reset_token"]) > 20

def test_request_reset_nonexistent_user():
    response = client.post(
        "/auth/request-reset",
        json={"email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert data["reset_token"] is None

def test_confirm_reset_success(temp_user):
    # 1. Request reset token
    req_res = client.post(
        "/auth/request-reset",
        json={"email": temp_user["email"]},
    )
    token = req_res.json()["reset_token"]
    assert token is not None

    # 2. Confirm reset with new password
    new_password = "BrandNewPassword123!"
    confirm_res = client.post(
        "/auth/confirm-reset",
        json={
            "token": token,
            "new_password": new_password,
        },
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["detail"] == "Password has been reset successfully"

    # 3. Verify old password fails
    old_login = client.post(
        "/auth/login",
        json={
            "email": temp_user["email"],
            "password": temp_user["password"],
        },
    )
    assert old_login.status_code == 401

    # 4. Verify new password succeeds
    new_login = client.post(
        "/auth/login",
        json={
            "email": temp_user["email"],
            "password": new_password,
        },
    )
    assert new_login.status_code == 200
    assert new_login.json()["user"]["email"] == temp_user["email"]

def test_confirm_reset_invalid_token():
    response = client.post(
        "/auth/confirm-reset",
        json={
            "token": "invalid.jwt.token.123",
            "new_password": "NewPassword123!",
        },
    )
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"]
