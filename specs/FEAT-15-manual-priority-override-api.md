# Feature: Manual Priority Override (API)
**Owner:** Backend | **Module:** Priority & SLA

## Goal
Let an admin correct an auto-assigned priority.

## Scope
- Endpoint: `PATCH /tickets/{id}/priority` (admin only).
- On change: also recalculate and update `deadline_at` using `sla-deadline-calculation`, since deadline depends on priority.
