# Feature: Upload Attachment (API)
**Owner:** Backend | **Module:** Comments & Attachments

## Goal
Securely accept and store a file linked to a ticket.

## Scope
- Endpoint: `POST /tickets/{id}/attachments` (multipart upload).
- Validate file size and extension server-side (never trust client-side checks alone).
- Store file (disk/object storage) and save metadata (filename, size, uploader, ticket_id) in an `attachments` table.
