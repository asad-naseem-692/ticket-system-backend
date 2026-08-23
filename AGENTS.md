# AGENTS.md — Backend (FastAPI)

## Scope
This file applies to the `backend/` folder only. This is its own GitHub
repo, deployed to **Railway** with a **Railway Postgres** plugin attached
in the same project. A sibling `frontend/AGENTS.md` covers the frontend —
do not build any UI here.

## Tech stack (do not substitute)
Python, FastAPI, Pydantic v2, SQLAlchemy + Alembic, PostgreSQL,
python-jose (JWT), passlib[bcrypt] (password hashing).

## Build order — full-stack, one feature at a time
This project is built as **vertical slices** together with the frontend,
not backend-then-frontend. For each feature:
1. Look at `specs/features/` in this folder for the next unbuilt backend
   feature, in `FEAT-XX` numeric order.
2. Implement ONLY that feature's backend part — don't get ahead.
3. Give a short summary: feature name, files created/changed, any new
   migration, any assumptions — especially anything affecting the API
   contract the frontend depends on.
4. **Stop and wait for explicit approval** before starting the next
   feature. If changes are requested, make them and stop again for
   approval.
5. Once approved, update that feature's spec `.md` file if the real
   implementation differs from the original plan — the spec must always
   describe current behavior, not just what was originally planned.

## Core architectural invariant
This backend is the single source of truth for business logic and data.
All authorization, validation, and business rules (SLA timing, status
transitions, permissions) are enforced here on every request — never
trust that the frontend already checked something, regardless of what it
hides or disables in its UI.

## Hard rules
- Fixed SLA table, defined once and referenced everywhere — never
  duplicated: Critical=2h, High=8h, Medium=24h, Low=72h.
- Ticket status only moves forward: Open → In Progress → Resolved →
  Closed. Reject any other transition.
- Passwords always hashed with bcrypt — never stored, logged, or returned
  in plain text anywhere, including error messages.
- Every ticket-mutating endpoint depends on a permission check from
  `app/core/permissions.py`. Role is always read from the verified JWT,
  never from the request body.
- `DATABASE_URL` and `CORS_ORIGINS` are read once through a central
  `app/core/config.py` — never via scattered `os.getenv()` calls, never
  hardcoded.
- Never combine `allow_origins=["*"]` with `allow_credentials=True` in
  CORS setup — this silently breaks auth for real deployed traffic.

## Database — read this carefully
There is only **one** Postgres database for this entire project, hosted
on Railway — not a separate local database. It's reached two different
ways depending on where the code is running:
- **From inside Railway** (once this service is deployed there): use the
  internal reference `${{Postgres.DATABASE_URL}}` in Railway's variable
  settings — fast, free, not publicly exposed. This is what production
  uses.
- **From outside Railway** (local development, before this service is
  deployed): use the **public** connection string — Railway → Postgres
  service → Networking → Public Access → `DATABASE_PUBLIC_URL` in the
  Variables tab. I will give you this value directly for the local
  `.env` file — never hardcode it in any file that gets committed.
Both addresses point to the exact same database and data. There is no
separate throwaway "dev" dataset — test data created during development
will persist in the real database, and that's expected for now.

## Data dictionary — return exactly these field names, always
Because frontend and backend are separate repos/sessions, matching field
names exactly is the only thing that makes them actually connect. Every
endpoint must return exactly the shapes below — never rename, abbreviate,
add wrapper objects, or reshape them for convenience.

**Conventions:** `snake_case` fields, ISO 8601 UTC timestamps (e.g.
`"2026-08-22T14:30:00Z"`), UUID string ids, errors as FastAPI's default
`{ "detail": "message" }` (don't build a custom error shape), list
endpoints return plain JSON arrays.

- **User**: `id, name, email, role ("customer"|"agent"|"admin"), created_at` — never include `hashed_password` in any response.
- **Auth response**: `{ "access_token": string, "token_type": "bearer", "user": User }`
- **Ticket**: `id, title, description, category, status ("open"|"in_progress"|"resolved"|"closed"), priority ("critical"|"high"|"medium"|"low"), customer_id, assigned_agent_id (nullable), created_at, deadline_at, sla_breached (boolean)`
- **Comment**: `id, ticket_id, author_id, visibility ("internal"|"public"), content, created_at`
- **Attachment**: `id, ticket_id, uploaded_by, filename, url, size_bytes, created_at`
- **Notification**: `id, user_id, ticket_id, type, message, created_at, read (boolean)`

If a feature needs a field not listed here, use the same conventions and
flag it clearly in your summary — it needs to be added to this same
dictionary in **both** `backend/AGENTS.md` and `frontend/AGENTS.md`.
Never invent or rename a field silently on just one side, and never
change an existing field's name or type here without flagging it —
everything already built against it would break.

## Never let a change to one feature break a feature it depends on
Many backend features build on each other (e.g. almost everything depends
on permission-check middleware and JWT generation). Before changing a
feature others rely on, check `specs/features/` for anything referencing
it. If a change is genuinely needed — including anything affecting the
API contract the frontend depends on — update that feature's spec
explicitly and confirm nothing else breaks. Never modify a dependency's
code, spec, or a fixed business rule (like the SLA table) silently as a
side effect of unrelated work.

## What you set up yourself (not covered by feature specs)
- `.env.example` and local `.env` with `DATABASE_URL` (I will provide the
  real value), `CORS_ORIGINS` (default `http://localhost:3000` for now),
  `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`),
  `ACCESS_TOKEN_EXPIRE_MINUTES` (default `60`), `ENVIRONMENT`.
- `.gitignore` for a Python project (`venv`, `__pycache__`, `.env*`,
  `*.db`, etc.) — `.env` must never be committed.
- `requirements.txt` with fastapi, uvicorn, sqlalchemy, alembic,
  psycopg2-binary, pydantic, python-jose, passlib[bcrypt], python-dotenv.
- `Dockerfile` that Railway will build directly — must listen on the
  `$PORT` environment variable Railway injects at runtime, not a
  hardcoded port.
- A central `app/core/config.py` that loads every env var above once, so
  nothing else in the codebase calls `os.getenv()` directly.
- A `/health` endpoint returning basic status — used for Railway's health
  checks and for manually verifying the deployed backend is alive.

## Deployment target
Railway, connected to the `backend/` GitHub repo, alongside a Railway
Postgres plugin in the same project. `CORS_ORIGINS` will need the
deployed frontend's Vercel URL added once that's known — that's a config
change in Railway's dashboard, not a code change.
