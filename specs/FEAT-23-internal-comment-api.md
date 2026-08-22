# Feature: Internal Comment (API)
**Owner:** Backend | **Module:** Comments & Attachments

## Goal
Store staff-only notes on a ticket that customers must never see.

## Scope
- Endpoint: `POST /tickets/{id}/comments` with `visibility: "internal"`.
- Only agent/admin roles can create internal comments.
- When a customer fetches ticket details, internal comments are filtered out at the query level, not just hidden in the UI.
