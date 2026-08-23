# Feature: View My Tickets (API)
**Owner:** Backend | **Module:** Ticket Management

## Goal
Return only the tickets belonging to the logged-in customer.

## Scope
- Endpoint: `GET /tickets/mine`
- Query filters `tickets` by `customer_id = current_user.id` — filtering happens in the query itself, not after fetching everything.
