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
def slice6_fixtures():
    """Sets up users and tickets for Slice 6 status and detail testing."""
    db = SessionLocal()

    cust1 = User(
        name="Slice6 Customer 1",
        email=f"s6_cust1_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    cust2 = User(
        name="Slice6 Customer 2",
        email=f"s6_cust2_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    agent1 = User(
        name="Slice6 Agent 1",
        email=f"s6_agent1_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    agent2 = User(
        name="Slice6 Agent 2",
        email=f"s6_agent2_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    admin = User(
        name="Slice6 Admin",
        email=f"s6_admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="admin",
    )

    db.add_all([cust1, cust2, agent1, agent2, admin])
    db.commit()
    for u in [cust1, cust2, agent1, agent2, admin]:
        db.refresh(u)

    now = datetime.now(timezone.utc)

    # Ticket assigned to Agent 1
    t1 = Ticket(
        title="Slice6 Ticket Alpha",
        description="Assigned to Agent 1",
        category="Technical Issue",
        status="open",
        priority="high",
        customer_id=cust1.id,
        assigned_agent_id=agent1.id,
        created_at=now,
        deadline_at=now + timedelta(hours=8),
        sla_breached=False,
    )
    db.add(t1)
    db.commit()
    db.refresh(t1)

    user_ids = [cust1.id, cust2.id, agent1.id, agent2.id, admin.id]
    ticket_ids = [t1.id]

    tokens = {
        "cust1": create_access_token(user_id=cust1.id, role=cust1.role),
        "cust2": create_access_token(user_id=cust2.id, role=cust2.role),
        "agent1": create_access_token(user_id=agent1.id, role=agent1.role),
        "agent2": create_access_token(user_id=agent2.id, role=agent2.role),
        "admin": create_access_token(user_id=admin.id, role=admin.role),
    }

    db.close()

    yield {
        "tokens": tokens,
        "t1_id": t1.id,
        "cust1_id": cust1.id,
        "agent1_id": agent1.id,
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

def test_ticket_detail_access_rules(slice6_fixtures):
    t1_id = slice6_fixtures["t1_id"]
    tokens = slice6_fixtures["tokens"]

    # 1. Customer 1 can view own ticket
    res_cust1 = client.get(f"/tickets/{t1_id}", headers={"Authorization": f"Bearer {tokens['cust1']}"})
    assert res_cust1.status_code == 200
    assert res_cust1.json()["id"] == t1_id

    # 2. Customer 2 forbidden from viewing Customer 1's ticket
    res_cust2 = client.get(f"/tickets/{t1_id}", headers={"Authorization": f"Bearer {tokens['cust2']}"})
    assert res_cust2.status_code == 403

    # 3. Assigned Agent 1 can view ticket
    res_agent1 = client.get(f"/tickets/{t1_id}", headers={"Authorization": f"Bearer {tokens['agent1']}"})
    assert res_agent1.status_code == 200

    # 4. Unassigned Agent 2 restricted (FEAT-21)
    res_agent2 = client.get(f"/tickets/{t1_id}", headers={"Authorization": f"Bearer {tokens['agent2']}"})
    assert res_agent2.status_code == 403

    # 5. Admin can view any ticket
    res_admin = client.get(f"/tickets/{t1_id}", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert res_admin.status_code == 200

def test_forward_only_status_lifecycle_and_permissions(slice6_fixtures):
    t1_id = slice6_fixtures["t1_id"]
    tokens = slice6_fixtures["tokens"]

    # Customer cannot update status
    cust_patch = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['cust1']}"},
        json={"status": "in_progress"},
    )
    assert cust_patch.status_code == 403

    # Unassigned agent cannot update status
    agent2_patch = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['agent2']}"},
        json={"status": "in_progress"},
    )
    assert agent2_patch.status_code == 403

    # Invalid jump: open -> closed directly (rejected)
    invalid_jump = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['agent1']}"},
        json={"status": "closed"},
    )
    assert invalid_jump.status_code == 400
    assert "Invalid status transition" in invalid_jump.json()["detail"]

    # Valid step 1: open -> in_progress
    step1 = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['agent1']}"},
        json={"status": "in_progress"},
    )
    assert step1.status_code == 200
    assert step1.json()["status"] == "in_progress"

    # Valid step 2: in_progress -> resolved
    step2 = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['agent1']}"},
        json={"status": "resolved"},
    )
    assert step2.status_code == 200
    assert step2.json()["status"] == "resolved"

    # Valid step 3: resolved -> closed (Admin can also do it)
    step3 = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"status": "closed"},
    )
    assert step3.status_code == 200
    assert step3.json()["status"] == "closed"

    # Backward transition: closed -> in_progress (rejected)
    backward = client.patch(
        f"/tickets/{t1_id}/status",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"status": "in_progress"},
    )
    assert backward.status_code == 400
