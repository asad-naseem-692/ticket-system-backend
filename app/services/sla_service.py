from datetime import datetime, timedelta, timezone
from app.core.config import settings

def calculate_deadline(priority: str, created_at: datetime) -> datetime:
    """
    Computes SLA deadline using the central fixed SLA lookup table (FEAT-16, FEAT-17):
    - critical: 2 hours
    - high: 8 hours
    - medium: 24 hours
    - low: 72 hours
    """
    p = priority.lower().strip() if priority else "medium"
    hours = settings.SLA_HOURS.get(p, settings.SLA_HOURS["medium"])

    # Ensure created_at is timezone-aware
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return created_at + timedelta(hours=hours)
