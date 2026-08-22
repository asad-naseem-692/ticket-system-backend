# Feature: View Attachment (API)
**Owner:** Backend | **Module:** Comments & Attachments

## Goal
Serve attachment files only to people allowed to see that ticket.

## Scope
- Endpoint: `GET /attachments/{id}`
- Re-check permission (same rule as ticket detail access) before streaming the file back.
