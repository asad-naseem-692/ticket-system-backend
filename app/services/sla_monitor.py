from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.user import User
from app.models.notification import Notification

def check_sla_breaches_and_warnings(db: Session) -> Dict[str, Any]:
    """
    Scans all active (open/in_progress) tickets to detect SLA breaches and at-risk warnings (FEAT-27, FEAT-28, FEAT-29):
    - Sets ticket.sla_breached = True when deadline_at is passed.
    - Generates 'sla_breach' notifications for assigned agent and admins.
    - Generates 'sla_warning' notifications for tickets with < 15 minutes remaining.
    """
    now = datetime.now(timezone.utc)
    active_tickets = (
        db.query(Ticket)
        .filter(Ticket.status.in_(["open", "in_progress"]))
        .all()
    )

    admins = db.query(User).filter(User.role == "admin").all()

    breaches_count = 0
    warnings_count = 0

    for ticket in active_tickets:
        ticket_deadline = ticket.deadline_at
        if ticket_deadline.tzinfo is None:
            ticket_deadline = ticket_deadline.replace(tzinfo=timezone.utc)

        # Identify recipient users (assigned agent + all admins)
        recipients: List[User] = list(admins)
        if ticket.assigned_agent_id:
            assigned_agent = db.query(User).filter(User.id == ticket.assigned_agent_id).first()
            if assigned_agent and assigned_agent not in recipients:
                recipients.append(assigned_agent)

        # 1. Hard SLA Breach Check (deadline passed)
        if now > ticket_deadline:
            if not ticket.sla_breached:
                ticket.sla_breached = True
                breaches_count += 1

            # Dispatch breach notification if not already sent
            for recipient in recipients:
                exists = (
                    db.query(Notification)
                    .filter(
                        Notification.user_id == recipient.id,
                        Notification.ticket_id == ticket.id,
                        Notification.type == "sla_breach",
                    )
                    .first()
                )
                if not exists:
                    notif = Notification(
                        user_id=recipient.id,
                        ticket_id=ticket.id,
                        type="sla_breach",
                        message=f"SLA Breached on ticket #{ticket.id[:8]}: '{ticket.title}'",
                    )
                    db.add(notif)

        # 2. At-Risk Warning Check (under 15 minutes remaining)
        else:
            remaining_seconds = (ticket_deadline - now).total_seconds()
            if 0 < remaining_seconds <= 900:  # 15 minutes
                for recipient in recipients:
                    exists = (
                        db.query(Notification)
                        .filter(
                            Notification.user_id == recipient.id,
                            Notification.ticket_id == ticket.id,
                            Notification.type == "sla_warning",
                        )
                        .first()
                    )
                    if not exists:
                        mins_left = max(1, round(remaining_seconds / 60))
                        notif = Notification(
                            user_id=recipient.id,
                            ticket_id=ticket.id,
                            type="sla_warning",
                            message=f"SLA Warning: ~{mins_left}m remaining on ticket #{ticket.id[:8]}: '{ticket.title}'",
                        )
                        db.add(notif)
                        warnings_count += 1

    db.commit()

    return {
        "checked_tickets": len(active_tickets),
        "new_breaches": breaches_count,
        "new_warnings": warnings_count,
        "timestamp": now.isoformat(),
    }
