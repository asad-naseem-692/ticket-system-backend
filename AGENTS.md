# AGENTS.md — Backend

## Who reads this
This file is instructions for the AI coding agent (Antigravity) building the
**backend only**. A sibling `frontend/AGENTS.md` exists for the frontend
build — do not build any UI here.

## What you're building
A FastAPI backend for a Customer Support Ticket & SLA Automation system.
Every business rule, endpoint, and background job this repo needs is
specified as a separate file under `docs/features/`. Build one feature at
a time, following its spec.

## Tech stack (do not substitute)
- Python, FastAPI, Pydantic v2 for request/response validation
- PostgreSQL via SQLAlchemy ORM, Alembic for migrations
- JWT for authentication (python-jose), bcrypt for password hashing (passlib)
- Asyncio-based background task for the SLA monitor

## Core architectural invariant (never violate this)
This backend is the **single source of truth** for all business logic and
data. The frontend never makes decisions — it only displays what this
backend returns. That means:
- All authorization/role checks happen here, on every request, regardless
  of what the frontend already hid or disabled.
- All validation (required fields, valid status transitions, valid role
  assignments) happens here — never trust the frontend already checked it.
- Role is always read from the verified JWT, never from any value sent in
  a request body.

## Hard rules
1. **SLA deadlines are fixed and centralized** (see
   `FEAT-17-sla-rule-storage.md`): Critical=2h, High=8h, Medium=24h,
   Low=72h. Define this once, reference it everywhere — never duplicate
   the numbers in multiple files.
2. **Ticket status can only move forward** through Open → In Progress →
   Resolved → Closed (see `FEAT-12-update-ticket-status-api.md`). Reject
   any other transition with a clear error.
3. **Passwords are always hashed** (bcrypt) — never store, log, or return
   plain text passwords anywhere, including in error messages.
4. **Every ticket-mutating endpoint depends on a permission check** from
   `app/core/permissions.py` (see `FEAT-20-permission-check-middleware.md`).
   Don't skip this even for "obviously fine" endpoints.
5. **CORS must never combine `allow_origins=["*"]` with
   `allow_credentials=True`** — browsers reject that combination silently
   and auth will appear broken. Use an explicit list of allowed frontend
   origins read from an environment variable.
6. **Database connection string is read from one place only**
   (`DATABASE_URL` via a central settings object) — never construct
   connection strings inline in multiple files.

## What you should set up yourself (not covered by feature specs)
Since this repo is built independently, please create the following as part
of project setup, using sensible defaults:
- `.env.example` and a local `.env` — must include at least:
  - `DATABASE_URL` (default to a local Postgres connection string for dev)
  - `CORS_ORIGINS` (comma-separated list of allowed frontend origins;
    default to `http://localhost:3000` for local dev)
  - `JWT_SECRET_KEY`, `JWT_ALGORITHM` (default `HS256`),
    `ACCESS_TOKEN_EXPIRE_MINUTES` (default `60`)
- `.gitignore` appropriate for a Python project (venv, __pycache__, .env*,
  *.db, etc.)
- `requirements.txt` with fastapi, uvicorn, sqlalchemy, alembic,
  psycopg2-binary, pydantic, python-jose, passlib[bcrypt], python-dotenv.
- `Dockerfile` that Railway will build from directly — must listen on the
  `$PORT` environment variable Railway injects at runtime, not a hardcoded
  port.
- A central `app/core/config.py` that loads all of the above env vars once,
  so nothing else in the codebase calls `os.getenv()` directly.

## Feature specs
All specs are in `docs/features/` as a simple flat list, numbered
FEAT-01 through FEAT-33 in build order: auth (01-06) → ticket management
(07-13) → priority/SLA rules (14-17) → assignment/RBAC (18-22) →
comments/attachments (23-26) → SLA timer/alerts (27-29) → reporting
(30-33). Build in that numeric order — later features assume earlier ones
exist (e.g. ticket creation assumes auth and priority scoring already
work).

## Data dictionary — return exactly these field names, always
Because the frontend and backend are built as two separate repos
(possibly in separate Antigravity sessions), a feature "matching its own
spec" is not enough — the two sides must also agree on exact field names,
or the frontend and backend will fail to connect even though each side
looks correct on its own. To prevent this, every endpoint you build must
return exactly the field names and types below. Do not rename, abbreviate,
add wrapper objects, or reshape these for convenience.

**Conventions:** all field names are `snake_case`. All timestamps are ISO
8601 UTC strings (e.g. `"2026-08-22T14:30:00Z"`). All ids are UUID
strings. Error responses look like `{ "detail": "message" }` (FastAPI's
default `HTTPException` shape — don't build a custom error format). List
endpoints return a plain JSON array unless a spec explicitly says
otherwise.

**User**
`id, name, email, role ("customer"|"agent"|"admin"), created_at`
— never include `hashed_password` in any response.

**Auth response** (login/signup)
`{ "access_token": string, "token_type": "bearer", "user": User }`

**Ticket**
`id, title, description, category, status ("open"|"in_progress"|"resolved"|"closed"), priority ("critical"|"high"|"medium"|"low"), customer_id, assigned_agent_id (nullable), created_at, deadline_at, sla_breached (boolean)`

**Comment**
`id, ticket_id, author_id, visibility ("internal"|"public"), content, created_at`

**Attachment**
`id, ticket_id, uploaded_by, filename, url, size_bytes, created_at`

**Notification**
`id, user_id, ticket_id, type, message, created_at, read (boolean)`

If a feature you're building needs a field not listed here, use
`snake_case` and the same conventions above, then say so explicitly in
your implementation summary — the field needs to be added to this same
dictionary in **both** `backend/AGENTS.md` and `frontend/AGENTS.md` so the
two repos stay in sync. Never invent or rename a field silently on just
one side, and never change an existing field's name or type here without
flagging it — every feature already built against it would break.

## Keep specs and code in sync (mandatory, every time)
The spec file for a feature is the source of truth for what that feature is
supposed to do — not just a one-time planning document. Whenever you add,
change, or remove behavior in a feature after it's already been built:
1. **Update that feature's `.md` file in `docs/features/` in the same
   change** — add/edit/remove the relevant bullet points (endpoint path,
   request/response shape, validation rule, permission rule) so the spec
   still accurately describes the current behavior.
2. If the change affects what the frontend receives (new/renamed field,
   changed endpoint, changed status codes), note that clearly in the spec
   so it's visible to whoever is working on the frontend repo.
3. If a change doesn't fit any existing feature file, create a new
   `FEAT-XX-name.md` for it, following the same format as the others,
   rather than leaving the change undocumented.
4. Never let a spec describe behavior that no longer exists in the code, and
   never let the code do something its spec doesn't mention — this matters
   even more here than on the frontend, since these specs define fixed
   business rules (SLA timings, permission rules) that must stay provably
   correct. Treat a stale or missing spec update as an incomplete task, not
   an optional cleanup step.

## Never let a change to one feature break a feature it depends on
Many backend features build on each other (e.g. "Manual Priority Override"
depends on "SLA Deadline Calculation" and "Automatic Priority Scoring";
"Reassign Ticket" depends on "Assign Ticket"; almost everything depends on
"Permission Check Middleware" and "JWT Token Generation"). Before changing
a feature that others rely on:
1. **Check `docs/features/` for any file that references the feature
   you're about to change** — treat every such reference as a dependent
   that must keep working exactly as its own spec describes (same
   endpoint path, same response shape, same validation/permission rule,
   unless you are deliberately changing it).
2. If your change is scoped to the feature you're working on and doesn't
   require altering the contract described in a dependency's spec, proceed
   normally — just don't touch that dependency's code or spec.
3. If your change genuinely requires altering a dependency's behavior
   (its inputs, its output shape, a rule it enforces), that is a deliberate
   cross-feature change, not a side-effect: update that dependency's own
   spec file explicitly to describe the new behavior, and check every other
   feature that depends on it — including frontend features listed in the
   sibling repo's specs, if the change affects the API contract — to
   confirm they still hold.
4. **Never modify a dependency's spec or code silently as a byproduct of
   working on something else**, and never change a fixed business rule
   (like the SLA time table) as a side-effect of an unrelated fix. If
   you're not sure whether a change ripples into a dependency, treat that
   uncertainty as a signal to check its spec file, not to guess.

## Deployment target
This repo deploys to **Railway**, alongside a Railway-managed Postgres
plugin in the same project. `DATABASE_URL` should be set in Railway to
reference the attached Postgres plugin's connection string rather than a
hardcoded value. `CORS_ORIGINS` must be updated to include the deployed
frontend's Vercel URL once that's known — the app should read this from
the environment, not from a hardcoded list, so this is just a config
change, not a code change.
