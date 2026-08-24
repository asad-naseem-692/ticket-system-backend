# Feature: Sign In (API)
**Owner:** Backend | **Module:** Authentication

## Goal
Verify credentials and issue an access token.

## Scope
- Endpoint: `POST /auth/login`
- Input: `email`, `password` (`LoginRequest` schema).
- Look up user by email, verify password against stored bcrypt hash.
- On success: issue a signed JWT containing user id (`sub`) and `role`.
- Response shape: `{ "access_token": string, "token_type": "bearer", "user": User }` matching Data Dictionary.
- On failure: generic 401 error (`{ "detail": "Invalid email or password" }`) — never reveal which field was wrong.
