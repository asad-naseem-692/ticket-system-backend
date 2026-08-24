from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
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
