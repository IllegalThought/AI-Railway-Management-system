# RailOps AI Architecture

## System purpose

RailOps AI is a synthetic railway operations management and decision-support simulation. It combines an operational web interface with optimization, graph analysis, and explainable AI workflows. It is not certified signaling software and must not be used to control real railway infrastructure.

## System context

```text
User
  |
  v
Next.js web application (Vercel)
  |
  | HTTPS / JSON API
  v
FastAPI service (Render)
  |                 |
  |                 +--> Optimization and graph services
  |                      (OR-Tools, NetworkX)
  v
SQLAlchemy persistence layer
  |
  +--> SQLite (local development)
  +--> PostgreSQL (production)
```

## Implemented responsibilities

### Frontend (Phases 2–8)

- Presents a professional, responsive operations workspace using the Next.js App Router, React, and strict TypeScript.
- Uses Tailwind CSS and shadcn/ui-compatible primitives as a modular design-system foundation, with Lucide icons and Recharts for measured operational datasets.
- Provides a shared application shell with desktop and mobile navigation, a top header, consistent workspace status language, loading states, unavailable states, tables, KPI cards, and toast notifications.
- Exposes routes for Overview, Live Operations, Dispatch Board, Network Monitor, Incident Center, Trains & Platforms, Performance Analytics, and System Status.
- Uses `NEXT_PUBLIC_API_BASE_URL` as the public backend origin and a typed client boundary in `frontend/lib/api.ts`.
- Uses a browser-generated UUID stored under `railops-session-id` and sends it as `X-RailOps-Session` on operational API requests.
- Provides fully integrated train management, platform availability management, scenario restore, and real operational Overview metrics.
- Provides a Dispatch Board backed by persisted solver output, with a horizontally scrollable platform timeline, interactive train selection, solver lifecycle controls, combined validation findings, and apply state.
- Provides an SVG Network Monitor for directed topology, selected paths, train/platform placement, blocked resources, movement indicators, reservation intervals, and inference explanations.
- Provides Live Operations with backend-controlled playback, reservation-derived train progress, live platform occupation, current signals, and persisted event history.
- Provides Incident Center for all supported disruption types, affected-service inspection, dynamic replanning, before/after comparisons, infeasibility reporting, and revised-plan application.
- Provides Performance Analytics with Recharts views for shared-state solver comparison, delay distribution, platform utilization, solver execution time, and schedule trends.
- Presents contextual decision evidence for platform acceptance/rejection, route reservation and knowledge-base outcomes, and incident-driven replanning changes.
- Uses actual analytics metrics on Overview for total and average delay, processed trains, schedule feasibility, solver timing, and active conflict signals.
- Keeps frontend presentation and transport concerns separate from backend domain and optimization logic.
- Keeps all user-facing content in English and identifies the product as a synthetic simulation.
- Provides a keyboard skip link, visible focus treatment, semantic chart labels, responsive overflow behavior, reduced-motion support, and consistent status and error presentation.
- Uses the live health contract on System Status instead of presenting nonfunctional configuration controls.

### Backend

- Exposes a FastAPI application with typed Pydantic request and response models.
- Provides health, train CRUD, platform read/update, scenario restore, operational Overview, schedule lifecycle, live simulation, and incident/replanning endpoints, plus OpenAPI at `/api/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`.
- Keep route handlers thin and place business rules in dedicated service modules.
- Uses structured English errors for application, request-validation, and database failures.
- Loads application, database, and CORS settings from environment variables.
- Rejects wildcard CORS in production, bounds declared request bodies, emits no-store and browser hardening headers, and returns structured errors without database internals.
- Resolves every operational request to an isolated simulation session through `X-RailOps-Session`; new session UUIDs receive the default 20-train, 5-platform scenario.
- Keeps scenario generation and record mutation in service modules; route handlers remain transport-focused.
- Keeps optimization in `app/ai`: a custom CSP uses MRV, recursive backtracking, and forward checking; FCFS provides a deterministic baseline; OR-Tools CP-SAT uses optional intervals and non-overlap constraints; an independent validator rechecks all persisted assignments.
- Keeps analytical aggregation and decision explanation in `app/services/analytics.py`; API handlers do not calculate business metrics.
- Keeps route intelligence in `app/ai` and `app/services/network.py`: a custom A* uses an admissible geometric heuristic, NetworkX Dijkstra independently checks shortest-path cost, and the reservation service checks half-open track and switch intervals.
- Uses restricted forward chaining over explicit movement predicates. GREEN requires complete platform, compatibility, and route facts; blocked resources or occupied track derive RED; missing mandatory facts remain YELLOW.

### Persistence

- Uses SQLAlchemy 2.x as the database abstraction.
- Select the database through environment configuration.
- Support SQLite for local development and PostgreSQL for deployed environments.
- Uses Alembic migrations for persistent schema changes.
- Enables SQLite foreign-key enforcement for local consistency.

## Operational data model

`SimulationSession` is the ownership boundary for visitor data. Trains, platforms, track nodes, track edges, scheduling plans, incidents, and operational events carry a session reference. Assignments and compatibility rows belong to session-owned records. Future APIs must derive the active session from a trusted session context and include it in every read and mutation filter.

The schema contains:

- trains with identifiers, priority, integer arrival and departure minutes, minimum dwell time, physical length, platform type requirements, explicit platform compatibility, and modeled entry/exit nodes;
- platforms with type, length, and post-occupancy clearance minutes;
- track nodes and directed track edges with traversal time, capacity, and resource groups;
- scheduling plans, train-to-platform assignments, route movements, and time-based track/switch reservations;
- isolated simulation sessions;
- incidents, a persisted simulation control row, and append-only operational events.

Phase 3 adds train service status and delay minutes, platform availability and an unavailable reason, and a scenario key on each simulation session. Phase 4 adds plan version, engine, solver outcome, objective, maximum delay, validation state and explanation plus assignment delay and reassignment state. Phase 5 adds entry/exit points, node layout coordinates, route validation state, movements, and reservations. Phase 6 adds typed incident timing and a one-to-one persisted simulation state. Phase 7 adds measured execution time to schedules and scenario-scoped solver benchmark records through Alembic revision `20261020_0006`. These fields remain portable across SQLite and PostgreSQL.

Each benchmark batch has a UUID and a scenario identifier composed from the scenario key and isolated workspace UUID. FCFS, custom CSP, and CP-SAT receive the same loaded trains, platforms, compatibility mappings, platform availability, scheduling horizon, maximum delay, preferred assignments, and candidate domains. Individual rows retain solver status, wall-clock execution time, delays, processed count, objective, and the solver's factual explanation. Optimality is exposed only when the retained status is `OPTIMAL`.

Ready scheduling plans are not silently left valid after train or platform changes. Ready plans return to draft, applied plans become invalid, route validation is cleared, and the mutation response includes `schedule_validation_required: true`. Combined platform and route validation must pass again before a changed plan can be applied.

All scheduling values use integer minutes. Occupancy and horizon intervals are half-open: `[start, end)`. The start is occupied and the end is excluded, so adjacent intervals can meet at the same minute without overlapping. Database constraints and reusable Pydantic validators enforce non-empty intervals and core record validity.

Platform scheduling treats train arrival plus recorded delay as the earliest usable start, preserves the planned occupancy duration, and allows delay only up to the plan maximum. Platform clearance extends the reserved interval after departure for conflict checks. CP-SAT minimizes priority-weighted delay plus a fixed platform reassignment cost relative to the applied plan. Custom CSP and FCFS expose feasible results but do not claim optimality.

Schedule lifecycle is `draft -> ready -> applied`, with `invalid` used when validation fails or applied inputs change and `archived` used for superseded applied plans. Every generated plan receives a monotonically increasing session-local version. Apply rejects non-latest versions, mismatched versions, and plans without current independent validation.

Phase 5 validation rebuilds all route movements for the selected plan in assignment-time order. Each train is routed from its entry point to its assigned platform before occupancy and from the platform to its exit after occupancy. Track resource groups and switch nodes are exclusive over half-open intervals. Closures remove resources from A* search, and reservation conflicts trigger alternative-path search before producing an unreachable/conflict finding.

Phase 6 makes `SimulationState` the authoritative workspace clock. GET state materializes elapsed whole seconds into deterministic integer simulation minutes using the persisted speed; control mutations require the caller's expected revision. Live positions are projections of applied assignment and route-reservation intervals, so the frontend never advances a train independently. A page refresh reuses the same workspace and database state.

Incident replanning reads the active applied plan and persisted simulation minute. Completed assignments and any movement whose first reservation has started are locked; committed route paths and reservation intervals are copied exactly into the revised plan before future routes are reserved around them. The CSP recalculates future allocations, route validation runs again, and apply retains the normal latest-version guard. The active plan remains unchanged when no valid revised solution exists.

## Repository shape

```text
backend/app/    FastAPI application, models, schemas, services, and database code
backend/alembic Database migration environment and revisions
backend/tests/  Pytest suite
backend/scripts/ Render-compatible production startup and migration gate
frontend/app/   Next.js routes, root layout, loading state, and global visual tokens
frontend/components/ Application shell, Overview modules, and reusable UI primitives
frontend/lib/   Typed API transport, navigation definitions, and shared utilities
docs/           Architecture and delivery tracking
render.yaml     Render monorepo web-service definition
.github/workflows/ Secret-free GitHub release verification
```

The frontend is independently deployable to Vercel. It contains no server-side domain logic and communicates with the Render-hosted FastAPI service over HTTPS/JSON.

## Configuration

Runtime configuration comes from environment variables. Local secret-bearing `.env` files are ignored; root, backend, and frontend `.env.example` files document variable names without credentials. Browser-exposed variables are limited to the non-secret `NEXT_PUBLIC_API_BASE_URL` backend origin. PostgreSQL URLs are normalized to the psycopg v3 SQLAlchemy driver. The default SQLite URL is resolved to the absolute `backend/railops.db` path, independent of process working directory. Production fails fast unless the database is PostgreSQL and every CORS entry is an exact HTTPS origin.

PostgreSQL connections use pre-ping plus bounded pool size, overflow, timeout, and recycle values. The default five-connection pool with five overflow slots avoids unbounded Render-to-Neon connections. Neon TLS remains part of the secret `DATABASE_URL`, normally through `sslmode=require`.

`python -m app.database.verify_schema` is the development schema gate. It reports the exact active SQLite path, compares the current Alembic revision to repository heads, checks every mapped table and column, and uses Alembic metadata comparison to detect model/schema drift. A migration revision at head is not sufficient by itself; the structural comparison must also pass.

## Frontend data flow

```text
Overview, Trains & Platforms, Dispatch Board, Network Monitor, Live Operations, and Incident Center clients
  |
  | browser-local workspace UUID
  v
Typed API client (`frontend/lib/api.ts`)
  |
  | HTTPS/JSON + X-RailOps-Session
  v
FastAPI route -> session resolver -> service layer -> SQLAlchemy
```

The session resolver looks up the public workspace UUID or creates an isolated normal-traffic workspace on first use. All train, platform, scenario, and Overview queries include the resulting internal session ID. The frontend contains no hardcoded operational records.

The browser validates and retains its generated UUID in local storage, so navigation and refresh reuse the same workspace. Malformed stored identifiers are replaced locally; the backend independently validates every header. Archived or expired sessions are rejected, while sessions with no expiry remain persistent. Database exceptions trigger request-session rollback, emit server-side exception logs with the request method and path, and return a structured `503 DATABASE_ERROR` without exposing internal details.

## Release-candidate API surface

```text
GET/POST       /api/trains
GET/PATCH/DELETE /api/trains/{id}
GET            /api/platforms
GET/PATCH      /api/platforms/{id}
GET            /api/scenarios
POST           /api/scenarios/{key}/restore
GET            /api/overview
POST           /api/schedules/generate
POST           /api/schedules/validate
POST           /api/schedules/apply
GET            /api/schedules/current
GET            /api/network/monitor
GET            /api/simulation/state
POST           /api/simulation/control
GET/POST       /api/incidents
PATCH          /api/incidents/{id}
POST           /api/incidents/replan
GET            /api/analytics
POST           /api/analytics/benchmarks
```

Scenario restore deletes and recreates only records owned by the active simulation session. The five deterministic scenario definitions are normal traffic, congested station, multiple delayed trains, platform closure, and track closure.

Generate reads current session resources and persists actual solver assignments. Validate independently reloads current resources, checks platform constraints, calculates A* routes, and persists conflict-free reservations plus inference decisions. Apply changes lifecycle state only after both validation layers and stale-version checks pass.

Analytics reads the authoritative persisted plan and simulation state. Delay metrics come from assignments; processing count comes from the simulation minute; platform utilization comes from occupancy intervals and the plan horizon; active conflicts come from active incidents and RED route decisions; feasibility requires a feasible solver outcome plus both validation layers. Decision explanations reuse compatibility, availability, length, type, delay, overlap, route reservation, inference, and replanning facts rather than generated claims.

## Release security and isolation

The API validates request shapes and domain bounds before service execution. Declared bodies larger than `MAX_REQUEST_BODY_BYTES` receive a structured 413 response. API responses are non-cacheable and carry `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a restrictive `Permissions-Policy`. Production CORS requires explicit HTTPS origins. Public scheduling and benchmark requests are limited to 500,000 CSP search nodes and 15 seconds of CP-SAT execution.

Scenario restore deletes and recreates records only inside the resolved workspace. No global database reset or destructive administration endpoint is exposed. Plan version checks and simulation revisions prevent stale writes. Solver requests are bounded by schema-level search and time limits.

The browser-generated workspace UUID is deliberately described as isolation rather than authentication. A public multi-user production service still requires server-issued identity, authorization, expiry, rate limiting, abuse controls, and audit operations.

## Integration verification

`backend/tests/test_phase8_release.py` exercises the user-visible chain across module boundaries: initialize a workspace, read records, generate, validate and apply a schedule, read routed movements, control simulation, create an incident, calculate a revision, apply it, and inspect analytics plus decision evidence. Existing focused suites validate CSP, backtracking behavior, MRV/forward-checking outcomes, CP-SAT status handling, A*, reservations, inference, migrations, and session isolation.

## Quality boundaries

- Business and optimization logic must be testable independently of HTTP and UI layers.
- Important backend behavior requires Pytest coverage.
- Frontend changes require type checking and a production build.
- Frontend transport behavior requires focused automated tests and inaccessible data must produce explicit unavailable states.
- API contracts must use explicit schemas rather than unstructured payloads.
- AI or optimization output must be produced by working algorithms, never hardcoded demonstrations.
- Controls must be wired to real behavior before they are presented as available.

## Deployment baseline

- GitHub hosts the monorepo and runs backend migration/tests plus frontend tests/type/lint/build before deployment.
- Vercel builds `frontend/` with Node.js 24 and injects the public Render HTTPS origin at build time.
- Render builds `backend/`, waits for GitHub checks, runs Alembic plus structural schema verification, and starts Uvicorn on `0.0.0.0:$PORT`.
- Neon PostgreSQL provides persistent production storage outside Render's ephemeral filesystem.
- `app.database.seed_demo` is optional and idempotent. Production blocks `Base.metadata.create_all`; schema evolution must use Alembic.
- External account creation, credentials, provider authorization, and live endpoint verification remain manual owner actions.

## Evolution policy

Update this document whenever a phase introduces or changes application boundaries, data flows, deployment topology, major dependencies, persistence decisions, or integration contracts.

