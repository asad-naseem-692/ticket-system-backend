# Feature: Sign In (API)
**Owner:** Backend | **Module:** Authentication

## Goal
Verify credentials and issue an access token.

## Scope
- Endpoint: `POST /auth/login`
- Look up user by email, verify password against stored hash.
- On success: issue a JWT (see `jwt-token-generation`) containing user id + role.
- On failure: generic "invalid email or password" error — never reveal which field was wrong.
