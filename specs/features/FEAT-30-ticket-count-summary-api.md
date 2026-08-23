# Feature: Ticket Count Summary (API)
**Owner:** Backend | **Module:** Reporting

## Goal
Provide aggregate counts for the reporting dashboard.

## Scope
- Endpoint: `GET /reports/summary` (admin only).
- Returns counts by status (open/in-progress/resolved/closed) and by priority.
