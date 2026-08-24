from datetime import datetime, timezone
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog
from app.schemas.report import TicketSummaryReport, AgentPerformanceItem, SLABreachItem

router = APIRouter(prefix="/reports", tags=["Reports"])

def require_admin(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators.",
        )

@router.get(
    "/summary",
    response_model=TicketSummaryReport,
    summary="Ticket count summary metrics (FEAT-30)",
)
def get_ticket_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns aggregate counts for admin overview dashboard (FEAT-30):
    - Total tickets
    - Counts grouped by status
    - Counts grouped by priority
    - SLA breach count and breach rate %
    """
    require_admin(current_user)

    total_tickets = db.query(Ticket).count()

    status_counts_raw = (
        db.query(Ticket.status, func.count(Ticket.id))
        .group_by(Ticket.status)
        .all()
    )
    by_status: Dict[str, int] = {"open": 0, "in_progress": 0, "resolved": 0, "closed": 0}
    for st, count in status_counts_raw:
        by_status[st] = count

    priority_counts_raw = (
        db.query(Ticket.priority, func.count(Ticket.id))
        .group_by(Ticket.priority)
        .all()
    )
    by_priority: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for pr, count in priority_counts_raw:
        by_priority[pr] = count

    total_sla_breached = db.query(Ticket).filter(Ticket.sla_breached == True).count()
    breach_rate = round((total_sla_breached / total_tickets * 100), 1) if total_tickets > 0 else 0.0

    return TicketSummaryReport(
        total_tickets=total_tickets,
        by_status=by_status,
        by_priority=by_priority,
        total_sla_breached=total_sla_breached,
        breach_rate_percent=breach_rate,
    )

@router.get(
    "/agent-performance",
    response_model=List[AgentPerformanceItem],
    summary="Agent performance metrics report (FEAT-31)",
)
def get_agent_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns performance metrics for each support agent (FEAT-31):
    - Assigned tickets count
    - Open workload count
    - Resolved tickets count
    - Average resolution time (hours)
    """
    require_admin(current_user)

    agents = db.query(User).filter(User.role == "agent").order_by(User.name.asc()).all()
    performance_list: List[AgentPerformanceItem] = []

    for agent in agents:
        assigned_tickets = db.query(Ticket).filter(Ticket.assigned_agent_id == agent.id).all()
        assigned_count = len(assigned_tickets)
        open_count = sum(1 for t in assigned_tickets if t.status in ["open", "in_progress"])
        resolved_tickets = [t for t in assigned_tickets if t.status in ["resolved", "closed"]]
        resolved_count = len(resolved_tickets)

        # Calculate average resolution time
        avg_res_hours: Optional[float] = None
        if resolved_tickets:
            durations = []
            for t in resolved_tickets:
                # Find resolution audit log or fallback to deadline/now
                resolution_audit = (
                    db.query(AuditLog)
                    .filter(
                        AuditLog.ticket_id == t.id,
                        AuditLog.action.in_(["status_change", "closed"]),
                        AuditLog.details.ilike("%resolved%"),
                    )
                    .first()
                )
                res_time = resolution_audit.timestamp if resolution_audit else t.created_at
                created = t.created_at
                if res_time.tzinfo is None:
                    res_time = res_time.replace(tzinfo=timezone.utc)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                durations.append(max(0.1, (res_time - created).total_seconds() / 3600))

            if durations:
                avg_res_hours = round(sum(durations) / len(durations), 1)

        performance_list.append(
            AgentPerformanceItem(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_email=agent.email,
                assigned_count=assigned_count,
                open_count=open_count,
                resolved_count=resolved_count,
                avg_resolution_time_hours=avg_res_hours,
            )
        )

    return performance_list

@router.get(
    "/sla-breaches",
    response_model=List[SLABreachItem],
    summary="List tickets that missed SLA deadline (FEAT-32)",
)
def get_sla_breaches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all tickets where sla_breached is True with breach details (FEAT-32).
    """
    require_admin(current_user)

    now = datetime.now(timezone.utc)
    breached_tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.assigned_agent))
        .filter(Ticket.sla_breached == True)
        .order_by(Ticket.deadline_at.desc())
        .all()
    )

    items: List[SLABreachItem] = []
    for t in breached_tickets:
        deadline = t.deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        hours_overdue = round(max(0.0, (now - deadline).total_seconds() / 3600), 1)

        items.append(
            SLABreachItem(
                ticket_id=t.id,
                title=t.title,
                priority=t.priority,
                category=t.category,
                status=t.status,
                deadline_at=t.deadline_at,
                created_at=t.created_at,
                hours_overdue=hours_overdue,
                assigned_agent_name=t.assigned_agent.name if t.assigned_agent else "Unassigned",
            )
        )

    return items
