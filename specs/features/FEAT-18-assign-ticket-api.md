# Feature: Assign Ticket to Agent (API)
**Owner:** Backend | **Module:** Assignment & RBAC

## Goal
Let an admin assign a ticket to a specific agent.

## Scope
- Endpoint: `POST /tickets/{id}/assign` (admin only).
- Input: `agent_id`. Validate the id actually belongs to a user with role "agent".
- Set `assigned_agent_id` on the ticket, log the action in the audit trail.
