# Feature: Password Reset (API)
**Owner:** Backend | **Module:** Authentication

## Goal
Let a user securely reset a forgotten password.

## Scope
- `POST /auth/request-reset` — generate a short-lived, single-use reset token, (email it in production; for dev, return/log it).
- `POST /auth/confirm-reset` — verify the reset token, hash the new password, update the user record, invalidate the token.
