# Feature: Password Reset (API)
**Owner:** Backend | **Module:** Authentication

## Goal
Let a user securely reset a forgotten password.

## Scope
- Endpoint: `POST /auth/request-reset`
  - Input: `{ "email": string }`
  - Generates a short-lived (15-minute), single-use JWT reset token (`type: "password_reset"`).
  - Returns generic message to prevent email enumeration: `{ "detail": "Password reset instructions have been generated if an account exists for this email.", "reset_token": string | null }` (token included in dev environment for testing).
- Endpoint: `POST /auth/confirm-reset`
  - Input: `{ "token": string, "new_password": string }`
  - Verifies reset token signature, type, and expiration.
  - Hashes new password with bcrypt and updates `users` record.
  - Returns `{ "detail": "Password has been reset successfully" }`.
