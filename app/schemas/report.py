from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

class TicketSummaryReport(BaseModel):
    total_tickets: int
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    total_sla_breached: int
    breach_rate_percent: float

class AgentPerformanceItem(BaseModel):
    agent_id: str
    agent_name: str
    agent_email: str
    assigned_count: int
    open_count: int
    resolved_count: int
    avg_resolution_time_hours: Optional[float] = None

class SLABreachItem(BaseModel):
    ticket_id: str
    title: str
    priority: str
    category: str
    status: str
    deadline_at: datetime
    created_at: datetime
    hours_overdue: float
    assigned_agent_name: Optional[str] = None
