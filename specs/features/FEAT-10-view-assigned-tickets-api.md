# Feature: View Assigned Tickets (API)
**Owner:** Backend | **Module:** Ticket Management

## Goal
Return only the tickets assigned to the logged-in agent.

## Scope
- Endpoint: `GET /tickets/assigned`
- Requires role = agent (or admin). Query filters `tickets` by `assigned_agent_id = current_user.id`.
