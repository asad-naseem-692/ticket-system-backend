# Feature: Role Assignment & Storage
**Owner:** Backend | **Module:** Authentication

## Goal
Store and enforce each user's role (customer / agent / admin).

## Scope
- `role` column on the `users` table, set at signup (default "customer" unless created by an admin).
- Role is only ever read from the verified JWT on the server — a request body claiming a different role is always ignored.
