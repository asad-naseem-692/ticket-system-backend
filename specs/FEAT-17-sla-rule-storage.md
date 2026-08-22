# Feature: SLA Rule Storage
**Owner:** Backend | **Module:** Priority & SLA

## Goal
Keep the SLA time limits in exactly one place, safe from accidental edits.

## Scope
- Constant lookup table (e.g. in `app/services/sla_service.py` or `app/core/config.py`):
  - Critical → 2 hours
  - High → 8 hours
  - Medium → 24 hours
  - Low → 72 hours
- No API endpoint modifies these values — they are a fixed business rule, changeable only via a code/spec update.
