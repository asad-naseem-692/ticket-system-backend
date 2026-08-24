import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.ticket import Ticket
from app.core.security import get_password_hash, create_access_token
from app.core.config import settings
from app.services.priority_service import calculate_priority
from app.services.sla_service import calculate_deadline

client = TestClient(app)

@pytest.fixture
def auth_customer():
    """Creates a temporary customer user and returns user info + JWT token with guaranteed cleanup."""
    db = SessionLocal()
    email = f"cust_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        name="Ticket Test Customer",
        email=email,
        hashed_password=get_password_hash("Password123!"),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    user_id = user.id
    token = create_access_token(user_id=user.id, role=user.role)
    db.close()

    yield {"id": user_id, "email": email, "token": token}

    # Teardown
    clean_db = SessionLocal()
    try:
        clean_db.query(Ticket).filter(Ticket.customer_id == user_id).delete(synchronize_session=False)
        clean_db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_priority_scoring_rules():
    assert calculate_priority("Server down", "All services offline", "General Inquiry") == "critical"
    assert calculate_priority("Normal request", "No issue", "Emergency") == "critical"
    assert calculate_priority("Payment failed", "Card declined", "General") == "high"
    assert calculate_priority("Invoice question", "Check details", "Billing") == "high"
    assert calculate_priority("UI glitch", "Button is misaligned", "General") == "medium"
    assert calculate_priority("System slow", "Taking 5 seconds", "Technical Issue") == "medium"
    assert calculate_priority("Question about pricing", "Where is the pricing table?", "General Inquiry") == "low"

def test_sla_deadline_calculation_rules():
    now = datetime.now(timezone.utc)
    critical_deadline = calculate_deadline("critical", now)
    assert critical_deadline == now + timedelta(hours=2)

    high_deadline = calculate_deadline("high", now)
    assert high_deadline == now + timedelta(hours=8)

    medium_deadline = calculate_deadline("medium", now)
    assert medium_deadline == now + timedelta(hours=24)

    low_deadline = calculate_deadline("low", now)
    assert low_deadline == now + timedelta(hours=72)

def test_create_ticket_api_critical(auth_customer):
    headers = {"Authorization": f"Bearer {auth_customer['token']}"}
    response = client.post(
        "/tickets",
        headers=headers,
        json={
            "title": "Major outage in production database",
            "description": "The database cluster has crashed and is returning 500s.",
            "category": "Emergency",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Major outage in production database"
    assert data["category"] == "Emergency"
    assert data["status"] == "open"
    assert data["priority"] == "critical"
    assert data["customer_id"] == auth_customer["id"]
    assert data["assigned_agent_id"] is None
    assert data["sla_breached"] is False
    assert "id" in data
    assert "created_at" in data
    assert "deadline_at" in data

    # Verify deadline is ~2 hours after created_at
    created_dt = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    deadline_dt = datetime.fromisoformat(data["deadline_at"].replace("Z", "+00:00"))
    diff_hours = (deadline_dt - created_dt).total_seconds() / 3600
    assert round(diff_hours) == 2

def test_create_ticket_api_medium(auth_customer):
    headers = {"Authorization": f"Bearer {auth_customer['token']}"}
    response = client.post(
        "/tickets",
        headers=headers,
        json={
            "title": "Minor styling glitch on mobile navigation",
            "description": "The hamburger menu icon wraps to the second line on small screens.",
            "category": "Technical Issue",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == "medium"
    assert data["status"] == "open"

    created_dt = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    deadline_dt = datetime.fromisoformat(data["deadline_at"].replace("Z", "+00:00"))
    diff_hours = (deadline_dt - created_dt).total_seconds() / 3600
    assert round(diff_hours) == 24

def test_create_ticket_unauthenticated():
    response = client.post(
        "/tickets",
        json={
            "title": "Anonymous ticket",
            "description": "Should fail with 401 unauthenticated",
            "category": "General Inquiry",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
