# Feature: Public Reply (API)
**Owner:** Backend | **Module:** Comments & Attachments

## Goal
Store replies visible to everyone on the ticket.

## Scope
- Endpoint: `POST /tickets/{id}/comments` with `visibility: "public"`.
- Any role on the ticket (customer, assigned agent, admin) can post one.
