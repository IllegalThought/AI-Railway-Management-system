# RailOps AI Architecture

## System purpose

RailOps AI is a synthetic railway operations management and decision-support simulation. It will combine an operational web interface with optimization, graph analysis, and explainable AI workflows. It is not certified signaling software and must not be used to control real railway infrastructure.

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

### Frontend (Phases 2–3)

- Presents a professional, responsive operations workspace using the Next.js App Router, React, and strict TypeScript.
- Uses Tailwind CSS and shadcn/ui-compatible primitives as a modular design-system foundation, with Lucide icons and Recharts available for verified future datasets.
- Provides a shared application shell with desktop and mobile navigation, a top header, consistent workspace status language, loading states, unavailable states, tables, KPI cards, and toast notifications.
- Exposes routes for Overview, Live Operations, Dispatch Board, Network Monitor, Incident Center, Trains & Platforms, Performance Analytics, and Settings.
- Uses `NEXT_PUBLIC_API_BASE_URL` as the public backend origin and a typed client boundary in `frontend/lib/api.ts`.
- Uses a browser-generated UUID stored under `railops-session-id` and sends it as `X-RailOps-Session` on operational API requests.
- Provides fully integrated train management, platform availability management, scenario restore, and real operational Overview metrics.
- Keeps frontend presentation and transport concerns separate from backend domain and optimization logic.
- Keeps all user-facing content in English and identifies the product as a synthetic simulation.

### Backend

- Exposes a FastAPI application with typed Pydantic request and response models.
- Provides health, train CRUD, platform read/update, scenario restore, and operational Overview endpoints, plus OpenAPI at `/api/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`.
- Keep route handlers thin and place business rules in dedicated service modules.
- Uses structured English errors for application, request-validation, and database failures.
- Loads application, database, and CORS settings from environment variables.
- Resolves every operational request to an isolated simulation session through `X-RailOps-Session`; new session UUIDs receive the default 20-train, 5-platform scenario.
- Keeps scenario generation and record mutation in service modules; route handlers remain transport-focused.
- Reserves isolated packages for later AI and simulation work; no optimization or routing behavior is implemented through Phase 3.

### Persistence

- Uses SQLAlchemy 2.x as the database abstraction.
- Select the database through environment configuration.
- Support SQLite for local development and PostgreSQL for deployed environments.
- Uses Alembic migrations for persistent schema changes.
- Enables SQLite foreign-key enforcement for local consistency.

## Operational data model

`SimulationSession` is the ownership boundary for visitor data. Trains, platforms, track nodes, track edges, scheduling plans, incidents, and operational events carry a session reference. Assignments and compatibility rows belong to session-owned records. Future APIs must derive the active session from a trusted session context and include it in every read and mutation filter.

The schema contains:

- trains with identifiers, priority, integer arrival and departure minutes, minimum dwell time, physical length, platform type requirements, and explicit platform compatibility;
- platforms with type, length, and post-occupancy clearance minutes;
- track nodes and directed track edges with traversal time, capacity, and resource groups;
- scheduling plans and train-to-platform assignments;
- isolated simulation sessions;
- incidents and append-only operational events.

Phase 3 adds train service status and delay minutes, platform availability and an unavailable reason, and a scenario key on each simulation session. These fields are portable across SQLite and PostgreSQL through Alembic revision `20261020_0002`.

Ready scheduling plans are not silently left valid after their assigned train or platform changes. The affected plan is returned to draft and the mutation response includes `schedule_validation_required: true`; a later scheduling phase will perform the actual revalidation.

All scheduling values use integer minutes. Occupancy and horizon intervals are half-open: `[start, end)`. The start is occupied and the end is excluded, so adjacent intervals can meet at the same minute without overlapping. Database constraints and reusable Pydantic validators enforce non-empty intervals and core record validity.

## Repository shape

```text
backend/app/    FastAPI application, models, schemas, services, and database code
backend/alembic Database migration environment and revisions
backend/tests/  Pytest suite
frontend/app/   Next.js routes, root layout, loading state, and global visual tokens
frontend/components/ Application shell, Overview modules, and reusable UI primitives
frontend/lib/   Typed API transport, navigation definitions, and shared utilities
docs/           Architecture and delivery tracking
```

The frontend is independently deployable to Vercel. It contains no server-side domain logic and communicates with the Render-hosted FastAPI service over HTTPS/JSON.

## Configuration

Runtime configuration comes from environment variables. Local secret-bearing `.env` files are ignored; `.env.example` documents variable names without credentials. Browser-exposed variables are limited to the non-secret `NEXT_PUBLIC_API_BASE_URL` backend origin. PostgreSQL URLs are normalized to the psycopg v3 SQLAlchemy driver. Production configuration rejects wildcard CORS origins.

## Frontend data flow

```text
Overview and Trains & Platforms clients
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

## Phase 3 API surface

```text
GET/POST       /api/trains
GET/PATCH/DELETE /api/trains/{id}
GET            /api/platforms
GET/PATCH      /api/platforms/{id}
GET            /api/scenarios
POST           /api/scenarios/{key}/restore
GET            /api/overview
```

Scenario restore deletes and recreates only records owned by the active simulation session. The five deterministic scenario definitions are normal traffic, congested station, multiple delayed trains, platform closure, and track closure.

## Quality boundaries

- Business and optimization logic must be testable independently of HTTP and UI layers.
- Important backend behavior requires Pytest coverage.
- Frontend changes require type checking and a production build.
- Frontend transport behavior requires focused automated tests and inaccessible data must produce explicit unavailable states.
- API contracts must use explicit schemas rather than unstructured payloads.
- AI or optimization output must be produced by working algorithms, never hardcoded demonstrations.
- Controls must be wired to real behavior before they are presented as available.

## Deployment baseline

- GitHub is the source-control host.
- Vercel hosts the frontend.
- Render hosts the FastAPI backend.
- PostgreSQL provides persistent production storage.
- Cross-origin access and public API base URLs will be configured through environment variables.

## Evolution policy

Update this document whenever a phase introduces or changes application boundaries, data flows, deployment topology, major dependencies, persistence decisions, or integration contracts.

