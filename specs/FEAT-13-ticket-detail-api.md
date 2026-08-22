# Feature: Ticket Detail (API)
**Owner:** Backend | **Module:** Ticket Management

## Goal
Return everything needed to render one ticket's full detail page.

## Scope
- Endpoint: `GET /tickets/{id}`
- Returns ticket fields + comments + attachments + audit log entries, joined in one response.
- Permission check: customer can only fetch their own ticket; agent only their assigned ticket; admin any ticket.
