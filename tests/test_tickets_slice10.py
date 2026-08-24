import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.comment import Comment
from app.models.attachment import Attachment
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)

@pytest.fixture
def slice10_fixtures():
    """Sets up users and tickets for Slice 10 reporting and audit trail testing."""
    db = SessionLocal()

    cust = User(
        name="Slice10 Customer",
        email=f"s10_cust_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    agent1 = User(
        name="Slice10 Agent 1",
        email=f"s10_agent1_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    agent2 = User(
        name="Slice10 Agent 2",
        email=f"s10_agent2_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    admin = User(
        name="Slice10 Admin",
        email=f"s10_admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="admin",
    )

    db.add_all([cust, agent1, agent2, admin])
    db.commit()
    for u in [cust, agent1, agent2, admin]:
        db.refresh(u)

    user_ids = [cust.id, agent1.id, agent2.id, admin.id]
    ticket_ids = []

    tokens = {
        "cust": create_access_token(user_id=cust.id, role=cust.role),
        "agent1": create_access_token(user_id=agent1.id, role=agent1.role),
        "agent2": create_access_token(user_id=agent2.id, role=agent2.role),
        "admin": create_access_token(user_id=admin.id, role=admin.role),
    }

    db.close()

    yield {
        "tokens": tokens,
        "agent1_id": agent1.id,
        "agent2_id": agent2.id,
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
        clean_db.query(AuditLog).filter(
            (AuditLog.ticket_id.in_(ticket_ids)) | (AuditLog.actor_id.in_(user_ids))
        ).delete(synchronize_session=False)
        clean_db.query(Comment).filter(Comment.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(Attachment).filter(Attachment.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_closure_and_state_audit_trail(slice10_fixtures):
    tokens = slice10_fixtures["tokens"]
    agent1_id = slice10_fixtures["agent1_id"]
    agent2_id = slice10_fixtures["agent2_id"]

    # 1. Customer creates ticket
    res_create = client.post(
        "/tickets",
        headers={"Authorization": f"Bearer {tokens['cust']}"},
        json={
            "title": "Audit Trail Test Ticket",
            "category": "Technical Issue",
            "description": "Lifecycle actions to test audit logging.",
        },
    )
    assert res_create.status_code == 201
    ticket_id = res_create.json()["id"]
    slice10_fixtures["ticket_ids"].append(ticket_id)

    # 2. Admin assigns ticket to Agent 1
    res_assign = client.post(
        f"/tickets/{ticket_id}/assign",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"agent_id": agent1_id},
    )
    assert res_assign.status_code == 200

    # 3. Admin reassigns ticket to Agent 2
    res_reassign = client.patch(
        f"/tickets/{ticket_id}/reassign",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"agent_id": agent2_id},
    )
    assert res_reassign.status_code == 200

    # 4. Admin overrides priority to critical
    res_prio = client.patch(
        f"/tickets/{ticket_id}/priority",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"priority": "critical"},
    )
    assert res_prio.status_code == 200

    # 5. Agent 2 updates status to in_progress -> resolved
    res_s1 = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {tokens['agent2']}"},
        json={"status": "in_progress"},
    )
    assert res_s1.status_code == 200

    res_s2 = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {tokens['agent2']}"},
        json={"status": "resolved"},
    )
    assert res_s2.status_code == 200

    # 6. Admin closes ticket
    res_close = client.patch(
        f"/tickets/{ticket_id}/status",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
        json={"status": "closed"},
    )
    assert res_close.status_code == 200

    # 7. Fetch audit trail (FEAT-33)
    res_audit = client.get(
        f"/tickets/{ticket_id}/audit-log",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    assert res_audit.status_code == 200
    logs = res_audit.json()
    assert len(logs) >= 6

    actions = [l["action"] for l in logs]
    assert "created" in actions
    assert "assigned" in actions
    assert "reassigned" in actions
    assert "priority_override" in actions
    assert "status_change" in actions
    assert "closed" in actions

def test_reports_endpoints_and_rbac(slice10_fixtures):
    tokens = slice10_fixtures["tokens"]

    # 1. Customer and Agent forbidden on all reporting endpoints (403)
    for endpoint in ["/reports/summary", "/reports/agent-performance", "/reports/sla-breaches"]:
        assert client.get(endpoint, headers={"Authorization": f"Bearer {tokens['cust']}"}).status_code == 403
        assert client.get(endpoint, headers={"Authorization": f"Bearer {tokens['agent1']}"}).status_code == 403

    # 2. Admin access to Summary Report (FEAT-30)
    res_summary = client.get("/reports/summary", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert "total_tickets" in summary_data
    assert "by_status" in summary_data
    assert "by_priority" in summary_data
    assert "breach_rate_percent" in summary_data

    # 3. Admin access to Agent Performance Report (FEAT-31)
    res_perf = client.get("/reports/agent-performance", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert res_perf.status_code == 200
    perf_data = res_perf.json()
    assert isinstance(perf_data, list)
    assert len(perf_data) >= 2

    # 4. Admin access to SLA Breach Report (FEAT-32)
    res_breach = client.get("/reports/sla-breaches", headers={"Authorization": f"Bearer {tokens['admin']}"})
    assert res_breach.status_code == 200
    breach_data = res_breach.json()
    assert isinstance(breach_data, list)
