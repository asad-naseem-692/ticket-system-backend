# Feature: Update Ticket Status (API)
**Owner:** Backend | **Module:** Ticket Management

## Goal
Enforce the fixed ticket lifecycle and who can change it.

## Scope
- Endpoint: `PATCH /tickets/{id}/status`
- Allowed transitions only: Open → In Progress → Resolved → Closed (no skipping, no going backwards without an explicit reopen rule).
- Only the assigned agent or an admin can change status.
- Reject and return a clear error on any invalid transition or unauthorized attempt.
