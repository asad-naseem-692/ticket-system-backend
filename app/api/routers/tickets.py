from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate, TicketResponse
from app.services.priority_service import calculate_priority
from app.services.sla_service import calculate_deadline

router = APIRouter(prefix="/tickets", tags=["Tickets"])

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
    Returns only tickets assigned to the logged-in agent/admin (FEAT-10).
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
