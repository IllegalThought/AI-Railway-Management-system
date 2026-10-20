# RailOps AI Progress

Last updated: 2026-10-20

## Current status

Phases 1 through 7 are complete and validated. RailOps AI now includes persisted operational analytics, consistent three-engine benchmarks, evidence-backed decision insights, and a refined analytics and Overview experience on top of the live simulation and dynamic replanning workflows.

## Phase tracking

| Phase | Status | Scope | Evidence |
| --- | --- | --- | --- |
| Repository foundation | Complete | Git repository, development rules, documentation baseline, ignore rules, and environment template | `AGENTS.md`, `docs/`, `.gitignore`, `.env.example`, `.git/` |
| Phase 1 | Complete | Backend architecture, database foundation, data models, API setup, migrations, initialization, seed data, and tests | `backend/app/`, `backend/alembic/`, `backend/tests/`, `backend/requirements.txt` |
| Phase 2 | Complete | Next.js application shell, design system, working navigation, typed health integration, Overview dashboard, and frontend validation | `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/package.json` |
| Phase 3 | Complete | Persistent train CRUD, platform availability, isolated scenarios, operational metrics, and full Trains & Platforms integration | `backend/app/api/`, `backend/app/services/`, `backend/tests/test_phase3_api.py`, `frontend/components/operations/` |
| Phase 4 | Complete | CSP, FCFS, CP-SAT platform scheduling, independent validation, version-safe apply workflow, and interactive Dispatch Board | `backend/app/ai/`, `backend/app/services/schedules.py`, `backend/tests/test_phase4_scheduling.py`, `frontend/components/dispatch/` |
| Phase 5 | Complete | NetworkX topology, custom A*, track and switch reservations, forward-chaining inference, combined plan validation, and interactive Network Monitor | `backend/app/ai/routing.py`, `backend/app/ai/inference.py`, `backend/app/services/network.py`, `backend/tests/test_phase5_network.py`, `frontend/components/network/` |
| Phase 6 | Complete | Persisted backend simulation clock, validated live movement state, incident management, committed-movement-safe dynamic replanning, schedule comparison, Live Operations, and Incident Center | `backend/app/services/simulation.py`, `backend/app/services/incidents.py`, `backend/tests/test_phase6_simulation.py`, `frontend/components/live/`, `frontend/components/incidents/` |
| Phase 7 | Complete | Actual operational metrics, persisted FCFS/CSP/CP-SAT benchmarks, decision explanations, incident-change rationales, Recharts analytics, and measured Overview KPIs | `backend/app/services/analytics.py`, `backend/app/api/analytics.py`, `backend/tests/test_phase7_analytics.py`, `frontend/components/analytics/`, `frontend/lib/analytics.test.ts` |

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
- Added a custom constraint-satisfaction scheduler with explicit variables/domains, hard constraints, recursive backtracking, minimum remaining values, forward checking, and a configurable search limit.
- Added a deterministic first-come-first-served scheduling baseline and an OR-Tools CP-SAT optimizer using optional intervals and per-platform non-overlap constraints.
- Added weighted delay optimization by train priority and platform reassignment penalties against the currently applied plan.
- Enforced platform compatibility, platform type, train length, availability, effective arrival, planned occupancy duration, minimum dwell, clearance buffer, maximum delay, horizon, and non-overlap constraints.
- Added an independent schedule validator that does not rely on solver feasibility claims.
- Persisted solver status, engine, objective, version, validation lifecycle, explanations, assignment delays, and reassignment indicators through Alembic revision `20261020_0003`.
- Added version-safe generate, validate, apply, and current-schedule APIs. Older generated plans cannot be applied after a newer version exists.
- Added a professional Dispatch Board with a platform/time timeline, priority-coded train blocks, clearance visualization, planned and allocated timings, delays, engine selection, validation findings, apply gating, and solver summaries from actual backend results.
- Kept every Phase 4 plan explicitly provisional for route reservations; Phase 4 does not perform or claim route-level validation.
- Replaced the placeholder topology with a directed weighted NetworkX station graph containing entry and exit points, junctions, switches, five platform connections, shared throats, shared berth sections, and bypass alternatives.
- Added explicit train entry and exit points plus layout coordinates, persisted route movements, exclusive half-open track/switch reservations, and Alembic revision `20261020_0004` with legacy synthetic-network data migration.
- Implemented deterministic custom A* using nonnegative travel-time costs and an admissible geometric heuristic, with Dijkstra/NetworkX reference validation.
- Added closure-aware routing, alternative-path selection, unreachable-route handling, and overlap rejection for shared track and switch resources while allowing adjacent reservations.
- Integrated route reservation validation into the schedule lifecycle. A plan becomes ready or applicable only when both independent platform validation and modeled routing constraints pass.
- Added a restricted predicate/rule forward-chaining engine using `PlatformOccupied`, `PlatformCompatible`, `TrackOccupied`, `RouteReserved`, `ResourceBlocked`, `MovementAllowed`, and `MovementBlocked`, with explanations based on evaluated facts and rules.
- Added RED, YELLOW, and GREEN simulated movement indicators; GREEN is emitted only when every mandatory modeled fact is present and the allow rule fires.
- Completed the Network Monitor with an interactive SVG topology, directed tracks, resource/closure state, selected train route, platform train label, movement indicators, reservation intervals, and decision explanations.
- Diagnosed the post-Phase 5 overview 503 as an unapplied `20261020_0004` migration: valid unknown browser UUIDs reached workspace initialization, which referenced the missing route-reservation tables. Applied the migration without resetting sessions, trains, platforms, or schedules.
- Hardened integration behavior by validating archived and expired workspaces, repairing malformed browser-stored UUIDs, rolling back failed request sessions, and logging underlying SQLAlchemy exceptions while retaining the safe structured 503 response.
- Added a persisted per-workspace simulation control row with current minute, run/pause state, 1x/2x/5x speed, optimistic revision, active plan, and backend tick timestamp through Alembic revision `20261020_0005`.
- Added deterministic start, pause, step, reset, and speed controls. Live train position, platform occupancy, active route reservations, movement permissions, signal indications, and events are derived from the applied validated plan and backend-owned time.
- Added incident creation and lifecycle APIs for arrival delay, departure delay, platform closure, track blockage, junction closure, and new train requests, including resource validation, severity, duration, status, description, and impact detection.
- Added dynamic CSP replanning from live station state with stale state/plan rejection, locked completed and started assignments, exact preservation of committed route reservations, independent platform and route validation, and explicit infeasibility responses.
- Completed Live Operations and Incident Center with real API controls, backend-driven progress animation, platform/resource views, incident reporting, affected-train inspection, before/after comparison, and validated revised-plan apply workflow.
- Added Phase 6 tests covering control state transitions, backend time progression, occupancy projection, delay mutation, platform closures, replanning, stale rejection, committed movement preservation, and visitor-session isolation.

## Known gaps

- Track capacity greater than one is represented in topology data but Phase 6 movement reservations remain exclusive.
- Deployment service manifests are not part of Phase 1.
- General assignment CRUD and arbitrary event-management APIs are not implemented; assignments remain governed by the validated scheduling lifecycle.
- Settings remains a later-phase shell destination.

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

## Phase 4 validation

- `python -m compileall -q app tests alembic`: passed.
- `python -m pytest -q`: passed (35 tests).
- Alembic upgrade through `20261020_0003` against an isolated SQLite database: passed.
- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings.
- `npm test`: passed (7 tests).
- `npm run build`: passed; the Dispatch Board and all other application routes were statically generated.
- `git diff --check`: passed.

## Phase 4 handoff

- Apply migrations and install updated backend dependencies before starting the API: `cd backend && python -m pip install -r requirements.txt && alembic upgrade head`.
- The CP-SAT engine is provided by OR-Tools; the API reports `UNKNOWN` with an explanation if a runtime is deployed without that declared dependency.
- Generate creates a new immutable plan version. Validate rechecks the persisted assignments against current train and platform data. Apply accepts only the latest independently validated version.
- Applied platform allocations are provisional. Phase 5 must check applicable route reservations before any route-valid language or workflow is introduced.
- Phase 4 stops at platform allocation, constraint optimization, independent validation, and the Dispatch Board.

## Phase 5 validation

- `python -m compileall -q app tests alembic`: passed.
- `python -m pytest -q`: passed (43 tests).
- Upgrade from Alembic revision `20261020_0003` through `20261020_0004` with legacy network records: passed; migrated topology contained 14 nodes and 32 directed edges.
- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings.
- `npm test`: passed (7 tests).
- `npm run build`: passed; the Network Monitor and all application routes were statically generated.
- `git diff --check`: passed.

## Phase 5 handoff

- Install the new NetworkX dependency and apply the migration: `cd backend && python -m pip install -r requirements.txt && alembic upgrade head`.
- Generate and validate a dispatch plan before inspecting assigned movement routes. Validation atomically rebuilds the plan's modeled route and resource reservations.
- Use the track-closure scenario to inspect RED blocked movement decisions; plans without route validation or mandatory route information remain YELLOW and cannot be applied.
- Phase 5 stops at network monitoring, route planning, resource reservation, logical inference, and combined schedule/route validation.

## Phase 5 integration verification

- Confirmed missing and malformed `X-RailOps-Session` headers return structured `400 INVALID_SESSION` responses; valid unknown UUIDs initialize an isolated normal-traffic workspace exactly once.
- Confirmed browser storage retains a valid workspace UUID across requests and repairs malformed stored values without weakening backend validation.
- Confirmed the active SQLite database was upgraded from `20261020_0003` to `20261020_0004`; existing core records were preserved. A pre-upgrade safety copy was written outside the repository.
- Verified real HTTP responses for Overview, Trains, Platforms, current schedule, schedule generation, schedule validation, and Network Monitor. The validated monitor returned 14 nodes, 32 edges, 20 movements, and GREEN indicators.
- Verified the Next.js dashboard, Trains & Platforms, Dispatch Board, and Network Monitor routes all returned HTTP 200 against a concurrently running FastAPI instance.
- `python -m pytest -q`: passed (48 tests).
- `npm test`: passed (9 tests).
- `npm run typecheck` and `npm run lint`: passed.

## Phase 6 validation

- `.venv/bin/python -m compileall -q app tests alembic`: passed.
- `.venv/bin/python -m pytest -q`: passed (53 tests).
- Fresh SQLite Alembic upgrade through `20261020_0005`: passed.
- Fresh database initialization after migration: passed.
- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings.
- `npm test`: passed (9 tests).
- `npm run build`: passed; Live Operations, Incident Center, and all application routes were statically generated.
- `git diff --check`: passed.

## Phase 6 handoff

- Apply the new migration before starting the backend: `cd backend && .venv/bin/alembic upgrade head`.
- Generate, validate, and apply a dispatch plan before starting playback. The simulation clock and current plan survive refreshes and navigation in the isolated workspace.
- Incident replans are reviewable but are not applied automatically. The operator must apply a valid latest revision from the before/after comparison.
- Phase 6 stops at live synthetic railway simulation, incident management, and dynamic AI replanning.

## Phase 7 validation

- `.venv/bin/python -m compileall -q app tests alembic`: passed.
- `.venv/bin/python -m pytest -q`: passed (56 tests; one upstream Starlette deprecation warning).
- Fresh SQLite Alembic upgrade through `20261020_0006`: passed.
- Fresh database initialization after migration: passed.
- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings.
- `npm test`: passed (11 tests).
- `npm run build`: passed; Performance Analytics and all application routes were statically generated.

## Phase 7 handoff

- Apply the analytics migration before starting the backend: `cd backend && .venv/bin/alembic upgrade head`.
- `GET /api/analytics` reports plan-derived delays, processing, conflict, feasibility, platform-use, trend, rescheduling, and decision evidence. It returns explicit empty datasets until a plan exists.
- `POST /api/analytics/benchmarks` runs FCFS, custom CSP, and OR-Tools CP-SAT against the same immutable station snapshot, hard-constraint domains, horizon, and maximum delay. Each result is persisted under one benchmark UUID and the workspace scenario identifier.
- Solver status and measured wall-clock execution time are retained. Only a CP-SAT `OPTIMAL` status produces an optimality-proven flag or claim.
- Phase 7 stops at performance analytics, AI decision insights, incident-change explanations, and dashboard refinement. No later-phase scope was implemented.

## Phase 7 schema compatibility repair

- Diagnosed the Analytics `503` as Phase 7 ORM code querying a SQLite schema that did not yet contain `scheduling_plans.execution_time_ms`. Revision `20261020_0006` already contained the correct nullable `FLOAT` addition and benchmark table; no migration history was rewritten.
- Confirmed FastAPI settings and Alembic resolve `/Users/panda/railops-ai/backend/railops.db`. The local default is now anchored to the backend directory so a different launch working directory cannot silently select another SQLite file.
- Created a SQLite online backup at `/private/tmp/railops-ai-backups/railops-phase7-schema-repair-20261020-2221.db`. Both the source and backup passed `PRAGMA integrity_check` and retained 2 sessions, 40 trains, 10 platforms, and 10 scheduling plans before API verification.
- Directly inspected `PRAGMA table_info(scheduling_plans)`: `execution_time_ms FLOAT NULL` is present. Directly confirmed Alembic revision and head are both `20261020_0006`.
- Added `python -m app.database.verify_schema` to detect a missing database file, relative SQLite path, pending migration, missing table/column, or ORM/Alembic drift. Made the ORM timing types explicitly `Float` to match the migration.
- Added an upgrade regression test that creates a real Phase 6 database with an existing applied plan, proves the verifier detects the pending column, upgrades through Phase 7, confirms the plan and nullable timing remain readable, calls Analytics and simulation state, and generates a new timed schedule.
- Refined frontend failure states so backend connectivity, database failures, invalid sessions, Analytics endpoint failures, and legitimate empty Analytics data are presented separately. Overview remains operational when only Analytics fails.
- Live verification against the existing applied-plan session returned HTTP 200 for Health, Overview, Current Schedule, Network Monitor, Simulation State, Incidents, and Analytics. A persisted three-engine benchmark returned FCFS `FEASIBLE`, CSP `FEASIBLE`, and CP-SAT `OPTIMAL`; the subsequent Analytics read returned the real delays, five platform utilization rows, measured execution times, and 20 decision explanations.

## Update policy

For each requested phase, record its scope, implementation status, validation commands, known limitations, and handoff notes. A phase may be marked complete only after its required automated checks pass.

