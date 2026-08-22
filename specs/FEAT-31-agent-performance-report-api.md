# Feature: Agent Performance Report (API)
**Owner:** Backend | **Module:** Reporting

## Goal
Provide per-agent stats for the reporting dashboard.

## Scope
- Endpoint: `GET /reports/agent-performance` (admin only).
- For each agent: tickets resolved, average resolution time, current open ticket count — computed via aggregate DB queries.
