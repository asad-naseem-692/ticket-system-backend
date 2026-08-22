# Feature: Breach Detection
**Owner:** Backend | **Module:** SLA Timer & Alerts

## Goal
Flag a ticket the moment its SLA deadline passes.

## Scope
- Runs inside `background-sla-monitor`: if `deadline_at < now()` and status is not Resolved/Closed, set `sla_breached = true`.
- Also flag an "at risk" state (e.g. under 15 minutes remaining) for early warning, separate from a hard breach.
