# Feature: Sign Out (API)
**Owner:** Backend | **Module:** Authentication

## Goal
Optionally invalidate a session server-side.

## Scope
- Since JWTs are stateless by default, true server-side sign-out needs a token blocklist/short expiry strategy.
- Minimum viable: rely on short `ACCESS_TOKEN_EXPIRE_MINUTES` + client discarding the token.
- If a blocklist is added later: `POST /auth/logout` stores the token's jti until it naturally expires.
