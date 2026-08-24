import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.ticket import Ticket
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)

@pytest.fixture
def slice5_fixtures():
    """Sets up two customers, an agent, an admin, and tickets for each, with complete teardown."""
    db = SessionLocal()

    # Create users
    cust1 = User(
        name="Customer One",
        email=f"cust1_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    cust2 = User(
        name="Customer Two",
        email=f"cust2_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    agent = User(
        name="Agent Support",
        email=f"agent_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    admin = User(
        name="Admin Boss",
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="admin",
    )

    db.add_all([cust1, cust2, agent, admin])
    db.commit()
    for u in [cust1, cust2, agent, admin]:
        db.refresh(u)

    now = datetime.now(timezone.utc)

    # Create tickets
    t1 = Ticket(
        title="Cust1 Ticket Alpha",
        description="First customer ticket",
        category="Billing",
        status="open",
        priority="high",
        customer_id=cust1.id,
        assigned_agent_id=agent.id,
        created_at=now,
        deadline_at=now + timedelta(hours=8),
        sla_breached=False,
    )
    t2 = Ticket(
        title="Cust1 Ticket Beta",
        description="Second customer ticket",
        category="General Inquiry",
        status="resolved",
        priority="low",
        customer_id=cust1.id,
        assigned_agent_id=None,
        created_at=now,
        deadline_at=now + timedelta(hours=72),
        sla_breached=False,
    )
    t3 = Ticket(
        title="Cust2 Ticket Gamma",
        description="Another customer ticket",
        category="Emergency",
        status="open",
        priority="critical",
        customer_id=cust2.id,
        assigned_agent_id=None,
        created_at=now,
        deadline_at=now + timedelta(hours=2),
        sla_breached=False,
    )

    db.add_all([t1, t2, t3])
    db.commit()

    user_ids = [cust1.id, cust2.id, agent.id, admin.id]
    ticket_ids = [t1.id, t2.id, t3.id]

    tokens = {
        "cust1": create_access_token(user_id=cust1.id, role=cust1.role),
        "cust2": create_access_token(user_id=cust2.id, role=cust2.role),
        "agent": create_access_token(user_id=agent.id, role=agent.role),
        "admin": create_access_token(user_id=admin.id, role=admin.role),
    }

    db.close()

    yield {
        "tokens": tokens,
        "cust1_id": cust1.id,
        "cust2_id": cust2.id,
        "agent_id": agent.id,
        "admin_id": admin.id,
        "ticket_ids": ticket_ids,
        "t1_id": t1.id,
        "t2_id": t2.id,
        "t3_id": t3.id,
    }

    # Teardown
    clean_db = SessionLocal()
    try:
        clean_db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_customer_view_my_tickets(slice5_fixtures):
    headers = {"Authorization": f"Bearer {slice5_fixtures['tokens']['cust1']}"}
    response = client.get("/tickets/mine", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    titles = [t["title"] for t in data]
    assert "Cust1 Ticket Alpha" in titles
    assert "Cust1 Ticket Beta" in titles
    assert "Cust2 Ticket Gamma" not in titles

def test_agent_view_assigned_tickets(slice5_fixtures):
    headers = {"Authorization": f"Bearer {slice5_fixtures['tokens']['agent']}"}
    response = client.get("/tickets/assigned", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Cust1 Ticket Alpha"
    assert data[0]["assigned_agent_id"] == slice5_fixtures["agent_id"]

def test_customer_cannot_view_assigned_tickets(slice5_fixtures):
    headers = {"Authorization": f"Bearer {slice5_fixtures['tokens']['cust1']}"}
    response = client.get("/tickets/assigned", headers=headers)
    assert response.status_code == 403

def test_admin_view_all_tickets_and_filtering(slice5_fixtures):
    headers = {"Authorization": f"Bearer {slice5_fixtures['tokens']['admin']}"}
    
    # 1. All tickets
    response = client.get("/tickets", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

    # 2. Filter by status=open
    filtered_res = client.get("/tickets?status=open", headers=headers)
    assert filtered_res.status_code == 200
    open_tickets = filtered_res.json()
    for t in open_tickets:
        assert t["status"] == "open"
