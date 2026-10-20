# RailOps AI Progress

Last updated: 2026-10-20

## Current status

Phases 1 through 3 are complete and validated. RailOps AI now provides isolated, persistent train and platform management, operational demo scenarios, real Overview metrics, and a production-built management interface.

## Phase tracking

| Phase | Status | Scope | Evidence |
| --- | --- | --- | --- |
| Repository foundation | Complete | Git repository, development rules, documentation baseline, ignore rules, and environment template | `AGENTS.md`, `docs/`, `.gitignore`, `.env.example`, `.git/` |
| Phase 1 | Complete | Backend architecture, database foundation, data models, API setup, migrations, initialization, seed data, and tests | `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/requirements.txt` |
| Phase 2 | Complete | Next.js application shell, design system, working navigation, typed health integration, Overview dashboard, and frontend validation | `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/package.json` |
| Phase 3 | Complete | Persistent train CRUD, platform availability, isolated scenarios, operational metrics, and full Trains & Platforms integration | `backend/app/api/`, `backend/app/services/`, `backend/tests/test_phase3_api.py`, `frontend/components/operations/` |

## Completed

- Established repository-wide engineering and English-language requirements.
- Documented the intended system architecture and deployment targets.
- Added safe ignore rules for the planned Python and Node.js toolchains.
- Added an environment-variable template containing no secrets.
- Added a modular FastAPI application with typed health response, structured error handling, OpenAPI documentation, and environment-based configuration.
- Added environment-controlled CORS with wildcard origins rejected in production.
- Added SQLAlchemy models for simulation sessions, trains, platforms, compatibility, track nodes and edges, scheduling plans, assignments, incidents, and operational events.
- Scoped operational records to isolated simulation sessions.
- Defined integer-minute scheduling and half-open occupancy intervals.
- Added reusable Pydantic validation for records and scheduling inputs.
- Added SQLite and PostgreSQL configuration support with SQLite foreign-key enforcement and psycopg v3 URL normalization.
- Added an initial Alembic migration.
- Added a database initialization command and idempotent synthetic seed data.
- Added Pytest coverage for health and OpenAPI, structured API errors, validation, persistence, session isolation, initialization, seeding, and duplicate handling.
- Isolated pytest configuration from normal runtime settings and ensured factory-injected settings are used consistently by request dependencies.
- Added backend setup and exact run instructions.
- Added a responsive Next.js App Router frontend with TypeScript, Tailwind CSS, shadcn/ui-compatible primitives, and Lucide icons.
- Added a persistent desktop sidebar, accessible mobile navigation, top header, RailOps AI wordmark, active navigation states, and eight working routes.
- Added a professional dark operations design system using deep navy and charcoal surfaces with restrained cyan and teal status accents.
- Added reusable buttons, badges, cards, compact data tables, KPI cards, loading skeletons, empty states, and accessible toast notifications.
- Added an Overview dashboard containing service readiness, operational KPIs, platform occupancy, upcoming trains, active incidents, and recent activity sections.
- Connected the Overview to the real `GET /api/health` contract through a typed API client configured by `NEXT_PUBLIC_API_BASE_URL`.
- Kept operational metrics unavailable where the backend has no read endpoint; the interface does not fabricate train, platform, incident, or activity data.
- Added API client tests for missing configuration, a valid health response, and contract validation.
- Added frontend setup and validation instructions.
- Added session-scoped train CRUD APIs and platform read/update APIs with structured errors and validation.
- Added a stable `X-RailOps-Session` workspace contract so each browser receives isolated mutable demo data instead of sharing global state.
- Added normal traffic, congested station, multiple delayed trains, platform closure, and track closure scenarios with a restore API.
- Expanded the default scenario to 20 trains and 5 platforms.
- Added persisted train service status and delay fields, platform availability and closure reason fields, and a Phase 3 Alembic migration.
- Added an operational Overview API with real train, platform, incident, upcoming-service, and recent-activity data.
- Added plan invalidation behavior: changes to assigned trains or platforms demote ready plans to draft and report that schedule validation is required.
- Completed the Trains & Platforms page with search, sorting, status filtering, add/edit forms, delete confirmation, train details, compatibility selection, platform details, availability management, scenario restore, and responsive loading/error/empty states.
- Updated Overview cards and sections to use real persistent backend data.
- Added backend API, validation, persistence, isolation, scenario, and schedule-invalidation tests plus frontend session-header and structured-error integration tests.

## Known gaps

- CSP scheduling, A* routing, and simulation behavior are intentionally not implemented.
- OR-Tools and NetworkX are deferred until the phases that implement optimization and routing.
- Deployment service manifests are not part of Phase 1.
- Assignment CRUD, incident management, and event-management APIs are not implemented; Phase 3 exposes their verified summary data only through the Overview endpoint.
- Live Operations, Dispatch Board, Network Monitor, Incident Center, Performance Analytics, and Settings remain later-phase shell destinations.
- Recharts is available in the frontend dependency baseline, but no operational chart is rendered because there is no verified time-series endpoint in the current backend.

## Phase 1 validation

- `python3 -m compileall -q app tests alembic`: passed.
- `git diff --check`: passed.
- English/ASCII content scan: passed.
- `alembic upgrade head` against an isolated SQLite database: passed.
- `python -m pytest -q`: passed (17 tests: all 16 existing tests plus one configuration regression test).

## Phase 2 validation

- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings.
- `npm test`: passed (3 tests).
- `npm run build`: passed; all eight application routes and the not-found route were statically generated.
- `git diff --check`: passed.

## Phase 2 handoff

- Run the backend on `http://localhost:8000` and set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env.local` for health connectivity.
- Run the frontend from `frontend/` with `npm run dev`.
- Phase 2 stops at the professional application shell and Overview experience. No algorithm, simulation, dispatch, or operational mutation workflows were added.

## Phase 3 validation

- `python -m compileall -q app tests alembic`: passed.
- `python -m pytest -q`: passed (25 tests).
- Alembic upgrade through `20261020_0002` against an isolated SQLite database: passed.
- Idempotent default scenario initialization against an isolated SQLite database: passed.
- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings.
- `npm test`: passed (6 tests).
- `npm run build`: passed; all application routes were statically generated.
- `git diff --check`: passed.

## Phase 3 handoff

- Apply migrations with `cd backend && alembic upgrade head` before running the updated API.
- The browser-generated workspace UUID is retained under `railops-session-id` in local storage and sent as `X-RailOps-Session` for every operational request.
- Scenario restore replaces only the current isolated workspace data.
- Phase 3 stops at train management, platform management, scenarios, and operational summary integration. Scheduling, routing, and AI algorithms remain unimplemented.

## Update policy

For each requested phase, record its scope, implementation status, validation commands, known limitations, and handoff notes. A phase may be marked complete only after its required automated checks pass.

