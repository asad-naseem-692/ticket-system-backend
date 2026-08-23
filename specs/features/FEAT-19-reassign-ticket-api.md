# Feature: Reassign Ticket (API)
**Owner:** Backend | **Module:** Assignment & RBAC

## Goal
Let an admin move a ticket from one agent to another.

## Scope
- Endpoint: `PATCH /tickets/{id}/reassign` (admin only).
- Same validation as `assign-ticket-api`, but also records the previous agent in the audit log for history.
