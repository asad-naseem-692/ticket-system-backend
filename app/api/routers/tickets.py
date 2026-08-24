from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.schemas.ticket import (
    TicketCreate,
    TicketResponse,
    TicketDetailResponse,
    TicketStatusUpdate,
    TicketPriorityUpdate,
    TicketAssignRequest,
)
from app.schemas.audit_log import AuditLogResponse
from app.services.priority_service import calculate_priority
from app.services.sla_service import calculate_deadline
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/tickets", tags=["Tickets"])

ALLOWED_TRANSITIONS = {
    "open": ["in_progress"],
    "in_progress": ["resolved"],
    "resolved": ["closed"],
    "closed": [],
}

@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket",
)
def create_ticket(
    ticket_in: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new support complaint (FEAT-07):
    - Binds customer_id to authenticated user from verified JWT (FEAT-08)
    - Automatically scores priority based on category/keywords (FEAT-14)
    - Computes SLA deadline from central fixed SLA table (FEAT-16, FEAT-17)
    - Sets initial status = 'open' and sla_breached = False
    - Writes creation audit log entry (FEAT-33)
    """
    now = datetime.now(timezone.utc)

    # 1. Automatic priority scoring
    priority = calculate_priority(
        title=ticket_in.title,
        description=ticket_in.description,
        category=ticket_in.category,
    )

    # 2. SLA deadline calculation
    deadline = calculate_deadline(priority=priority, created_at=now)

    # 3. Create ticket bound to current user
    new_ticket = Ticket(
        title=ticket_in.title.strip(),
        description=ticket_in.description.strip(),
        category=ticket_in.category.strip(),
        status="open",
        priority=priority,
        customer_id=current_user.id,
        assigned_agent_id=None,
        created_at=now,
        deadline_at=deadline,
        sla_breached=False,
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    # Audit Log
    log_audit_event(
        db,
        ticket_id=new_ticket.id,
        actor_id=current_user.id,
        action="created",
        details=f"Ticket created with priority '{new_ticket.priority}' and category '{new_ticket.category}'",
    )

    return new_ticket

@router.get(
    "/mine",
    response_model=List[TicketResponse],
    summary="View customer's own tickets",
)
@router.get(
    "/my",
    response_model=List[TicketResponse],
    include_in_schema=False,
)
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns only tickets submitted by the authenticated customer (FEAT-09).
    Filters at the database query level by customer_id.
    """
    tickets = (
        db.query(Ticket)
        .filter(Ticket.customer_id == current_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return tickets

@router.get(
    "/assigned",
    response_model=List[TicketResponse],
    summary="View tickets assigned to current agent",
)
def get_assigned_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns only tickets assigned to the logged-in agent/admin (FEAT-10, FEAT-21).
    """
    if current_user.role not in ["agent", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to support agents and administrators",
        )

    tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_agent_id == current_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return tickets

@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    summary="Get detailed information for a single ticket",
)
def get_ticket_detail(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns full details for a single ticket (FEAT-13).
    Strictly enforces role-based access restrictions (FEAT-21):
    - Customers can only view their own tickets (403 otherwise).
    - Agents can only view tickets assigned to them (403 otherwise).
    - Admins can view any ticket.
    - Filters comments: customers NEVER see internal comments (FEAT-23).
    """
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.customer),
            joinedload(Ticket.assigned_agent),
            joinedload(Ticket.attachments).joinedload(Attachment.uploader),
            joinedload(Ticket.comments).joinedload(Comment.author),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # RBAC Data Restriction Check
    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this ticket.",
        )
    elif current_user.role == "agent" and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: this ticket is not assigned to your queue.",
        )

    # Filter out internal comments for customer callers
    comments_list = ticket.comments
    if current_user.role == "customer":
        comments_list = [c for c in ticket.comments if c.visibility == "public"]

    return TicketDetailResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        customer_id=ticket.customer_id,
        assigned_agent_id=ticket.assigned_agent_id,
        created_at=ticket.created_at,
        deadline_at=ticket.deadline_at,
        sla_breached=ticket.sla_breached,
        customer=ticket.customer,
        assigned_agent=ticket.assigned_agent,
        comments=comments_list,
        attachments=ticket.attachments,
    )

@router.get(
    "/{ticket_id}/audit-log",
    response_model=List[AuditLogResponse],
    summary="Get chronological tamper-evident audit history for a ticket",
)
def get_ticket_audit_log(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns ordered audit trail history for accountability (FEAT-33).
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    if current_user.role == "customer" and ticket.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view audit history for this ticket.",
        )
    elif current_user.role == "agent" and ticket.assigned_agent_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: this ticket is not assigned to your queue.",
        )

    logs = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.actor))
        .filter(AuditLog.ticket_id == ticket_id)
        .order_by(AuditLog.timestamp.asc())
        .all()
    )
    return logs

@router.patch(
    "/{ticket_id}/status",
    response_model=TicketResponse,
    summary="Update ticket status lifecycle",
)
def update_ticket_status(
    ticket_id: str,
    status_in: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates the lifecycle status of a ticket (FEAT-12):
    - Enforces forward-only transitions: open -> in_progress -> resolved -> closed
    - Enforces permission checks: only the assigned agent or an admin can update status
    - Checks SLA breach state upon resolution
    - Records audit log entry (FEAT-33)
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    # 1. RBAC Permission Check
    is_assigned_agent = current_user.role == "agent" and ticket.assigned_agent_id == current_user.id
    is_admin = current_user.role == "admin"

    if not (is_assigned_agent or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned agent or an administrator can update the status of this ticket.",
        )

    # 2. Strict forward-only transition check
    current_status = ticket.status
    target_status = status_in.status

    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{current_status}' to '{target_status}'. Allowed next statuses: {allowed}",
        )

    # 3. Apply update
    now = datetime.now(timezone.utc)
    ticket.status = target_status

    # Check SLA breach if resolving
    if target_status in ["resolved", "closed"]:
        ticket_deadline = ticket.deadline_at
        if ticket_deadline.tzinfo is None:
            ticket_deadline = ticket_deadline.replace(tzinfo=timezone.utc)
        if now > ticket_deadline:
            ticket.sla_breached = True

    db.commit()
    db.refresh(ticket)

    # Audit Log
    action_name = "closed" if target_status == "closed" else "status_change"
    log_audit_event(
        db,
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action=action_name,
        details=f"Status changed from '{current_status}' to '{target_status}'",
    )

    return ticket

@router.patch(
    "/{ticket_id}/priority",
    response_model=TicketResponse,
    summary="Manual priority override (admin only)",
)
def override_ticket_priority(
    ticket_id: str,
    priority_in: TicketPriorityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually overrides ticket priority (FEAT-15, FEAT-22):
    - Admin only (403 for non-admins)
    - Recalculates deadline_at according to fixed SLA duration table
    - Recalculates sla_breached state
    - Records audit log entry (FEAT-33)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can override ticket priority.",
        )

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    old_priority = ticket.priority
    new_priority = priority_in.priority
    ticket.priority = new_priority

    # Recalculate deadline based on original created_at timestamp
    ticket.deadline_at = calculate_deadline(priority=new_priority, created_at=ticket.created_at)

    # Check if deadline passed
    now = datetime.now(timezone.utc)
    ticket_deadline = ticket.deadline_at
    if ticket_deadline.tzinfo is None:
        ticket_deadline = ticket_deadline.replace(tzinfo=timezone.utc)

    if ticket.status not in ["resolved", "closed"]:
        ticket.sla_breached = now > ticket_deadline

    db.commit()
    db.refresh(ticket)

    # Audit Log
    log_audit_event(
        db,
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action="priority_override",
        details=f"Priority overridden from '{old_priority}' to '{new_priority}'. Recalculated deadline.",
    )

    return ticket

@router.post(
    "/{ticket_id}/assign",
    response_model=TicketResponse,
    summary="Assign ticket to an agent (admin only)",
)
@router.patch(
    "/{ticket_id}/reassign",
    response_model=TicketResponse,
    summary="Reassign ticket to another agent (admin only)",
)
def assign_ticket(
    ticket_id: str,
    assign_in: TicketAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assigns or reassigns a support ticket to an agent (FEAT-18, FEAT-19, FEAT-22):
    - Admin only (403 for non-admins)
    - Validates target agent exists and has role 'agent'
    - Records audit log entry (FEAT-33)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can assign or reassign tickets.",
        )

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    target_agent = db.query(User).filter(User.id == assign_in.agent_id, User.role == "agent").first()
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target assigned user must exist and have the 'agent' role.",
        )

    is_reassign = ticket.assigned_agent_id is not None
    old_agent_id = ticket.assigned_agent_id
    ticket.assigned_agent_id = target_agent.id

    db.commit()
    db.refresh(ticket)

    # Audit Log
    action_name = "reassigned" if is_reassign else "assigned"
    detail_msg = (
        f"Reassigned to {target_agent.name} ({target_agent.email}) [Previous Agent ID: {old_agent_id}]"
        if is_reassign
        else f"Assigned to {target_agent.name} ({target_agent.email})"
    )
    log_audit_event(
        db,
        ticket_id=ticket.id,
        actor_id=current_user.id,
        action=action_name,
        details=detail_msg,
    )

    return ticket

@router.get(
    "",
    response_model=List[TicketResponse],
    summary="View all tickets (admin / filtered overview)",
)
def get_all_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    category_filter: Optional[str] = Query(None, alias="category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns ticket listings based on user role and optional filters (FEAT-11):
    - Admin: All tickets with optional filters
    - Agent: Assigned tickets
    - Customer: Customer's own tickets
    """
    query = db.query(Ticket)

    if current_user.role == "customer":
        query = query.filter(Ticket.customer_id == current_user.id)
    elif current_user.role == "agent":
        query = query.filter(
            (Ticket.assigned_agent_id == current_user.id) | (Ticket.assigned_agent_id.is_(None))
        )

    if status_filter:
        query = query.filter(Ticket.status == status_filter.lower().strip())
    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter.lower().strip())
    if category_filter:
        query = query.filter(Ticket.category.ilike(f"%{category_filter.strip()}%"))

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets
