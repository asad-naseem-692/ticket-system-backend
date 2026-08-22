# Feature: SLA Breach Report (API)
**Owner:** Backend | **Module:** Reporting

## Goal
List every ticket that missed its SLA deadline.

## Scope
- Endpoint: `GET /reports/sla-breaches` (admin only).
- Returns tickets where `sla_breached = true`, with priority, deadline, how late, and assigned agent.
