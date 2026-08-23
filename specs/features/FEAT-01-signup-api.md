# Feature: Sign Up (API)
**Owner:** Backend | **Module:** Authentication

## Goal
Create a new user account securely.

## Scope
- Endpoint: `POST /auth/signup`
- Input (Pydantic schema): name, email, password, role.
- Check email isn't already registered → reject with clear error if it is.
- Hash password with bcrypt before saving — never store or log plain text passwords.
- Save to `users` table: id, name, email, hashed_password, role, created_at.
- Return the created user (never return the password hash).
- Complementary endpoint: `GET /auth/me` returns current user profile for verified JWT.
