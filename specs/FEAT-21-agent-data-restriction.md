# Feature: Agent Data Restriction
**Owner:** Backend | **Module:** Assignment & RBAC

## Goal
Make sure agents can only see/act on tickets assigned to them.

## Scope
- Applied at the query level in `view-assigned-tickets-api` and `ticket-detail-api`: `WHERE assigned_agent_id = current_user.id`.
- Not just a UI hide — an agent calling the API directly for another agent's ticket gets a 403.
