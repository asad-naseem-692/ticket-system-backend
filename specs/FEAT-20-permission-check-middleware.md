# Feature: Permission Check Middleware
**Owner:** Backend | **Module:** Assignment & RBAC

## Goal
Guarantee every sensitive action is authorized server-side, regardless of what the frontend shows.

## Scope
- `app/core/permissions.py`: FastAPI dependency functions like `require_role("admin")`, `require_ticket_owner_or_agent(ticket_id)`.
- Every router that mutates data (status update, assignment, priority override, comments) depends on one of these.
- Role is always read from the verified JWT — never from the request body.
