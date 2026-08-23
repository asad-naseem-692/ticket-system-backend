# Feature: Closure Audit Log (API)
**Owner:** Backend | **Module:** Reporting

## Goal
Keep an ordered, tamper-evident history of everything that happened to a ticket.

## Scope
- `audit_log` table: ticket_id, actor_id, action, timestamp, optional detail (e.g. "status changed: open -> in_progress").
- A new row is written on every meaningful ticket event (created, assigned, reassigned, status changed, priority overridden, closed).
- Endpoint: `GET /tickets/{id}/audit-log` returns the ordered history for `closure-audit-log-ui`.
