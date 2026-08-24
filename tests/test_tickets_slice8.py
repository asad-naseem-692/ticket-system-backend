import io
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.attachment import Attachment
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)

@pytest.fixture
def slice8_fixtures():
    """Sets up users and tickets for Slice 8 comments and attachments testing."""
    db = SessionLocal()

    cust1 = User(
        name="Slice8 Customer 1",
        email=f"s8_cust1_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    cust2 = User(
        name="Slice8 Customer 2",
        email=f"s8_cust2_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="customer",
    )
    agent = User(
        name="Slice8 Agent",
        email=f"s8_agent_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="agent",
    )
    admin = User(
        name="Slice8 Admin",
        email=f"s8_admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="admin",
    )

    db.add_all([cust1, cust2, agent, admin])
    db.commit()
    for u in [cust1, cust2, agent, admin]:
        db.refresh(u)

    now = datetime.now(timezone.utc)

    # Ticket assigned to Agent
    t1 = Ticket(
        title="Slice 8 Communication Ticket",
        description="Testing public replies, internal notes, and attachments",
        category="Technical Issue",
        status="in_progress",
        priority="high",
        customer_id=cust1.id,
        assigned_agent_id=agent.id,
        created_at=now,
        deadline_at=now + timedelta(hours=8),
        sla_breached=False,
    )
    db.add(t1)
    db.commit()
    db.refresh(t1)

    user_ids = [cust1.id, cust2.id, agent.id, admin.id]
    ticket_ids = [t1.id]

    tokens = {
        "cust1": create_access_token(user_id=cust1.id, role=cust1.role),
        "cust2": create_access_token(user_id=cust2.id, role=cust2.role),
        "agent": create_access_token(user_id=agent.id, role=agent.role),
        "admin": create_access_token(user_id=admin.id, role=admin.role),
    }

    db.close()

    yield {
        "tokens": tokens,
        "t1_id": t1.id,
        "cust1_id": cust1.id,
        "cust2_id": cust2.id,
        "agent_id": agent.id,
        "admin_id": admin.id,
        "ticket_ids": ticket_ids,
        "user_ids": user_ids,
    }

    # Teardown
    clean_db = SessionLocal()
    try:
        clean_db.query(Comment).filter(Comment.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(Attachment).filter(Attachment.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(Ticket).filter(Ticket.id.in_(ticket_ids)).delete(synchronize_session=False)
        clean_db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
        clean_db.commit()
    finally:
        clean_db.close()

def test_public_reply_flow(slice8_fixtures):
    t1_id = slice8_fixtures["t1_id"]
    tokens = slice8_fixtures["tokens"]

    # Customer 1 posts public reply
    res_cust = client.post(
        f"/tickets/{t1_id}/comments",
        headers={"Authorization": f"Bearer {tokens['cust1']}"},
        json={"content": "Hello, I am having issues with my login.", "visibility": "public"},
    )
    assert res_cust.status_code == 201
    assert res_cust.json()["visibility"] == "public"

    # Agent posts public reply
    res_agent = client.post(
        f"/tickets/{t1_id}/comments",
        headers={"Authorization": f"Bearer {tokens['agent']}"},
        json={"content": "We are looking into this for you right now.", "visibility": "public"},
    )
    assert res_agent.status_code == 201

    # Verify both public comments appear in list
    res_list = client.get(f"/tickets/{t1_id}/comments", headers={"Authorization": f"Bearer {tokens['cust1']}"})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2

def test_internal_notes_isolation(slice8_fixtures):
    t1_id = slice8_fixtures["t1_id"]
    tokens = slice8_fixtures["tokens"]

    # 1. Customer cannot post internal note (403 Forbidden)
    res_cust_fail = client.post(
        f"/tickets/{t1_id}/comments",
        headers={"Authorization": f"Bearer {tokens['cust1']}"},
        json={"content": "Trying to make internal note", "visibility": "internal"},
    )
    assert res_cust_fail.status_code == 403

    # 2. Agent posts internal note
    res_agent_internal = client.post(
        f"/tickets/{t1_id}/comments",
        headers={"Authorization": f"Bearer {tokens['agent']}"},
        json={"content": "Internal note: Server db pool is congested.", "visibility": "internal"},
    )
    assert res_agent_internal.status_code == 201

    # 3. Customer fetching comments should NOT see the internal note
    res_cust_view = client.get(f"/tickets/{t1_id}/comments", headers={"Authorization": f"Bearer {tokens['cust1']}"})
    assert res_cust_view.status_code == 200
    comments = res_cust_view.json()
    for c in comments:
        assert c["visibility"] == "public"

    # 4. Agent fetching comments DOES see the internal note
    res_agent_view = client.get(f"/tickets/{t1_id}/comments", headers={"Authorization": f"Bearer {tokens['agent']}"})
    assert res_agent_view.status_code == 200
    visibilities = [c["visibility"] for c in res_agent_view.json()]
    assert "internal" in visibilities

def test_attachment_upload_and_download(slice8_fixtures):
    t1_id = slice8_fixtures["t1_id"]
    tokens = slice8_fixtures["tokens"]

    # 1. Reject invalid file extension (.exe)
    bad_file = io.BytesIO(b"malicious content")
    res_bad_ext = client.post(
        f"/tickets/{t1_id}/attachments",
        headers={"Authorization": f"Bearer {tokens['cust1']}"},
        files={"file": ("virus.exe", bad_file, "application/octet-stream")},
    )
    assert res_bad_ext.status_code == 400
    assert "extension" in res_bad_ext.json()["detail"]

    # 2. Valid image upload by Customer
    valid_file = io.BytesIO(b"fake image data")
    res_upload = client.post(
        f"/tickets/{t1_id}/attachments",
        headers={"Authorization": f"Bearer {tokens['cust1']}"},
        files={"file": ("screenshot.png", valid_file, "image/png")},
    )
    assert res_upload.status_code == 201
    attachment_data = res_upload.json()
    attachment_id = attachment_data["id"]
    assert attachment_data["filename"] == "screenshot.png"

    # 3. Download by authorized customer
    res_dl_cust = client.get(f"/attachments/{attachment_id}", headers={"Authorization": f"Bearer {tokens['cust1']}"})
    assert res_dl_cust.status_code == 200
    assert res_dl_cust.content == b"fake image data"

    # 4. Download by unauthorized Customer 2 rejected with 403
    res_dl_unauth = client.get(f"/attachments/{attachment_id}", headers={"Authorization": f"Bearer {tokens['cust2']}"})
    assert res_dl_unauth.status_code == 403
