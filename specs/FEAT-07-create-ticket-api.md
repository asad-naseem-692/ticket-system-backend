# Feature: Create Ticket (API)
**Owner:** Backend | **Module:** Ticket Management

## Goal
Save a new complaint with all required derived data.

## Scope
- Endpoint: `POST /tickets`
- Input: title, description, category.
- On save: bind to logged-in customer (`customer-account-binding`), run `automatic-priority-scoring`, compute `sla-deadline-calculation`, set status = "open".
- Return the created ticket including its id, priority, and deadline.
