# Feature: Background SLA Monitor
**Owner:** Backend | **Module:** SLA Timer & Alerts

## Goal
Continuously watch open tickets for approaching or passed deadlines, even with no user online.

## Scope
- `app/workers/sla_monitor_worker.py`: an async background task started on app startup, running on an interval (e.g. every 60 seconds).
- Checks all non-closed tickets' `deadline_at` against current time.
- Uses the same SQLAlchemy models as the rest of the app — no separate raw SQL.
