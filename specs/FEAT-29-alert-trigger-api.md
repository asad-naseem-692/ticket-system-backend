# Feature: Alert Trigger (API)
**Owner:** Backend | **Module:** SLA Timer & Alerts

## Goal
Notify the right people when a ticket is at risk or has breached its SLA.

## Scope
- Triggered from `breach-detection`: create a notification record (assigned agent + admins), optionally send an email/in-app push.
- Endpoint: `GET /notifications` for the frontend to poll/display (`alert-notification-ui`).
