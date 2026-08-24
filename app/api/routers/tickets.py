from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.schemas.ticket import (
    TicketCreate,
    TicketResponse,
    TicketDetailResponse,
    TicketStatusUpdate,
    TicketPriorityUpdate,
    TicketAssignRequest,
)
from app.services.priority_service import calculate_priority
from app.services.sla_service import calculate_deadline

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
    """
    ticket = (
        db.query(Ticket)
        .options(joinedload(Ticket.customer), joinedload(Ticket.assigned_agent))
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

    return ticket

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

    ticket.assigned_agent_id = target_agent.id
    db.commit()
    db.refresh(ticket)

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
