# Feature: Automatic Priority Scoring
**Owner:** Backend | **Module:** Priority & SLA

## Goal
Assign a priority (Critical/High/Medium/Low) to every new ticket automatically.

## Scope
- `app/services/priority_service.py`: takes ticket title/description/category, returns a priority level based on defined rules (e.g. keyword matching, category mapping).
- Runs once at ticket creation; result is stored on the ticket, not recalculated on every read.
