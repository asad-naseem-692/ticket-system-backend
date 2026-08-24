# Feature: List Support Agents API
**Owner:** Backend | **Module:** Assignment & RBAC

## Goal
Provide a list of all active support agents to populate assignment dropdowns and triage selectors.

## Scope
- Endpoint: `GET /users/agents`
- Security: Requires authenticated user with `admin` role (returns `403 Forbidden` for customers and non-admin users).
- Returns: `List[UserResponse]` where each user has `role = "agent"` ordered by name.
- Used by: `frontend/specs/features/FEAT-15-assign-ticket-ui.md` and `frontend/specs/features/FEAT-16-reassign-ticket-ui.md`.
