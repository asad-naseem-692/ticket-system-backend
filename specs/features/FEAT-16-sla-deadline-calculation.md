# Feature: SLA Deadline Calculation
**Owner:** Backend | **Module:** Priority & SLA

## Goal
Compute the exact deadline a ticket must be resolved by.

## Scope
- `app/services/sla_service.py`: pure function `calculate_deadline(priority, created_at)`.
- Fixed rule table (see `sla-rule-storage`) — never hardcode these numbers in multiple places.
- Result stored as `deadline_at` on the ticket at creation time (and recalculated only if priority changes).
