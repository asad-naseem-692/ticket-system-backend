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
def slice7_fixtures():
    """Sets up users and ticket for assignment and priority override testing."""
    db = SessionLocal()

    cust = User(
        name="Slice7 Customer",
        email=f"s7_cust_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    agent1 = User(
        name="Slice7 Agent 1",
        email=f"s7_agent1_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    agent2 = User(
        name="Slice7 Agent 2",
        email=f"s7_agent2_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    admin = User(
        name="Slice7 Admin",
        email=f"s7_admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="admin",
    )

    db.add_all([cust, agent1, agent2, admin])
    db.commit()
    for u in [cust, agent1, agent2, admin]:
        db.refresh(u)

    now = datetime.now(timezone.utc)

    # Initial low priority unassigned ticket
    t1 = Ticket(
        title="Slice 7 Override & Assignment Ticket",
        description="Testing priority override and agent assignment",
        category="General Inquiry",
        status="open",
        priority="low",
        customer_id=cust.id,
        assigned_agent_id=None,
        created_at=now,
        deadline_at=now + timedelta(hours=72),
        sla_breached=False,
    )
    db.add(t1)
    db.commit()
    db.refresh(t1)

    user_ids = [cust.id, agent1.id, agent2.id, admin.id]
    ticket_ids = [t1.id]

    tokens = {
        "cust": create_access_token(user_id=cust.id, role=cust.role),
        "agent1": create_access_token(user_id=agent1.id, role=agent1.role),
        "agent2": create_access_token(user_id=agent2.id, role=agent2.role),
        "admin": create_access_token(user_id=admin.id, role=admin.role),
    }

    db.close()

    yield {
        "tokens": tokens,
        "t1_id": t1.id,
        "cust_id": cust.id,
        "agent1_id": agent1.id,
        "agent2_id": agent2.id,
        "admin_id": admin.id,
        "ticket_ids": ticket_ids,
        "user_ids": user_ids,
    }

    # Teardown
    clean_db = SessionLocal()
    try:
        clean_db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_priority_override_by_admin(slice7_fixtures):
    t1_id = slice7_fixtures["t1_id"]
    tokens = slice7_fixtures["tokens"]

    # Customer and Agent cannot override priority
    res_cust = client.patch(
        f"/tickets/{t1_id}/priority",
        headers={"Authorization": f"Bearer {tokens['cust']}"},
        json={"priority": "critical"},
    )
    assert res_cust.status_code == 403

    res_agent = client.patch(
        f"/tickets/{t1_id}/priority",
        headers={"Authorization": f"Bearer {tokens['agent1']}"},
        json={"priority": "critical"},
    )
    assert res_agent.status_code == 403

    # Admin overrides priority to critical
    res_admin = client.patch(
        f"/tickets/{t1_id}/priority",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"priority": "critical"},
    )
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["priority"] == "critical"

    # Verify deadline recalculation to 2 hours
    created_dt = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    deadline_dt = datetime.fromisoformat(data["deadline_at"].replace("Z", "+00:00"))
    diff_hours = (deadline_dt - created_dt).total_seconds() / 3600
    assert round(diff_hours) == 2

def test_ticket_assignment_and_reassignment(slice7_fixtures):
    t1_id = slice7_fixtures["t1_id"]
    tokens = slice7_fixtures["tokens"]
    agent1_id = slice7_fixtures["agent1_id"]
    agent2_id = slice7_fixtures["agent2_id"]
    cust_id = slice7_fixtures["cust_id"]

    # 1. Non-admin forbidden
    res_agent_assign = client.post(
        f"/tickets/{t1_id}/assign",
        headers={"Authorization": f"Bearer {tokens['agent1']}"},
        json={"agent_id": agent1_id},
    )
    assert res_agent_assign.status_code == 403

    # 2. Cannot assign to a customer
    res_invalid_role = client.post(
        f"/tickets/{t1_id}/assign",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"agent_id": cust_id},
    )
    assert res_invalid_role.status_code == 400
    assert "agent" in res_invalid_role.json()["detail"]

    # 3. Admin assigns to Agent 1
    res_assign = client.post(
        f"/tickets/{t1_id}/assign",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"agent_id": agent1_id},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_agent_id"] == agent1_id

    # 4. Admin reassigns to Agent 2
    res_reassign = client.patch(
        f"/tickets/{t1_id}/reassign",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"agent_id": agent2_id},
    )
    assert res_reassign.status_code == 200
    assert res_reassign.json()["assigned_agent_id"] == agent2_id

def test_list_agents_endpoint(slice7_fixtures):
    tokens = slice7_fixtures["tokens"]

    # Customer forbidden
    res_cust = client.get("/users/agents", headers={"Authorization": f"Bearer {tokens['cust']}"})
    assert res_cust.status_code == 403

    # Admin and Agent allowed
    res_admin = client.get("/users/agents", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert res_admin.status_code == 200
    agents = res_admin.json()
    assert len(agents) >= 2
    for a in agents:
        assert a["role"] == "agent"
