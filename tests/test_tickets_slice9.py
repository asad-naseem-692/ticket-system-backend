import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.ticket import Ticket
from app.models.notification import Notification
from app.core.security import get_password_hash, create_access_token
from app.services.sla_monitor import check_sla_breaches_and_warnings

client = TestClient(app)

@pytest.fixture
def slice9_fixtures():
    """Sets up users and tickets for Slice 9 SLA monitoring and alerts testing."""
    db = SessionLocal()

    cust = User(
        name="Slice9 Customer",
        email=f"s9_cust_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    agent = User(
        name="Slice9 Agent",
        email=f"s9_agent_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    admin = User(
        name="Slice9 Admin",
        email=f"s9_admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="admin",
    )

    db.add_all([cust, agent, admin])
    db.commit()
    for u in [cust, agent, admin]:
        db.refresh(u)

    now = datetime.now(timezone.utc)

    # 1. Overdue ticket (breached)
    t_breached = Ticket(
        title="Slice 9 Overdue Ticket",
        description="Ticket whose deadline has already passed",
        category="Technical Issue",
        status="open",
        priority="critical",
        customer_id=cust.id,
        assigned_agent_id=agent.id,
        created_at=now - timedelta(hours=3),
        deadline_at=now - timedelta(hours=1),
        sla_breached=False,
    )

    # 2. At-risk ticket (10 minutes remaining)
    t_warning = Ticket(
        title="Slice 9 At-Risk Ticket",
        description="Ticket expiring in 10 minutes",
        category="Billing",
        status="in_progress",
        priority="high",
        customer_id=cust.id,
        assigned_agent_id=agent.id,
        created_at=now - timedelta(hours=7, minutes=50),
        deadline_at=now + timedelta(minutes=10),
        sla_breached=False,
    )

    db.add_all([t_breached, t_warning])
    db.commit()
    db.refresh(t_breached)
    db.refresh(t_warning)

    user_ids = [cust.id, agent.id, admin.id]
    ticket_ids = [t_breached.id, t_warning.id]

    tokens = {
        "cust": create_access_token(user_id=cust.id, role=cust.role),
        "agent": create_access_token(user_id=agent.id, role=agent.role),
        "admin": create_access_token(user_id=admin.id, role=admin.role),
    }

    db.close()

    yield {
        "tokens": tokens,
        "t_breached_id": t_breached.id,
        "t_warning_id": t_warning.id,
        "agent_id": agent.id,
        "admin_id": admin.id,
        "cust_id": cust.id,
        "ticket_ids": ticket_ids,
        "user_ids": user_ids,
    }

    # Teardown
    clean_db = SessionLocal()
    try:
        clean_db.query(Notification).filter(
            (Notification.ticket_id.in_(ticket_ids)) | (Notification.user_id.in_(user_ids))
        ).delete(synchronize_session=False)
        clean_db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_sla_breach_detection_and_warning(slice9_fixtures):
    db = SessionLocal()
    try:
        # Run SLA check
        results = check_sla_breaches_and_warnings(db)
        assert results["checked_tickets"] >= 2

        # Verify overdue ticket marked as breached
        t_breached = db.query(Ticket).filter(Ticket.id == slice9_fixtures["t_breached_id"]).first()
        assert t_breached.sla_breached is True

        # Verify notifications created for agent
        agent_notifs = db.query(Notification).filter(Notification.user_id == slice9_fixtures["agent_id"]).all()
        types = [n.type for n in agent_notifs]
        assert "sla_breach" in types
        assert "sla_warning" in types
    finally:
        db.close()

def test_notifications_api_endpoints(slice9_fixtures):
    agent_token = slice9_fixtures["tokens"]["agent"]

    # Trigger SLA check first
    db = SessionLocal()
    try:
        check_sla_breaches_and_warnings(db)
    finally:
        db.close()

    # 1. Fetch unread notifications
    res_list = client.get("/notifications", headers={"Authorization": f"Bearer {agent_token}"})
    assert res_list.status_code == 200
    notifs = res_list.json()
    assert len(notifs) >= 2
    first_notif_id = notifs[0]["id"]

    # 2. Mark single notification as read
    res_read = client.patch(f"/notifications/{first_notif_id}/read", headers={"Authorization": f"Bearer {agent_token}"})
    assert res_read.status_code == 200
    assert res_read.json()["read"] is True

    # 3. Mark all as read
    res_read_all = client.post("/notifications/read-all", headers={"Authorization": f"Bearer {agent_token}"})
    assert res_read_all.status_code == 200

    # 4. Check unread notifications count is now 0
    res_unread = client.get("/notifications?unread_only=true", headers={"Authorization": f"Bearer {agent_token}"})
    assert res_unread.status_code == 200
    assert len(res_unread.json()) == 0
