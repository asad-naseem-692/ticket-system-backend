# Feature: JWT Token Generation & Verification
**Owner:** Backend | **Module:** Authentication

## Goal
Issue and verify signed tokens used to authenticate every request.

## Scope
- `app/core/security.py`: `create_access_token(user_id, role)` and `decode_access_token(token)`.
- Payload includes: `sub` (user id), `role`, `exp` (expiry).
- Signed using `JWT_SECRET_KEY` + `JWT_ALGORITHM` from environment (`app/core/config.py`) — never hardcoded.
- A FastAPI dependency (`get_current_user`) decodes the token on every protected route and rejects invalid/expired tokens with 401.
