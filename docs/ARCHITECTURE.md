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

## Implemented Phase 1 responsibilities

### Frontend (future phase)

- Present a professional operations interface using Next.js and TypeScript.
- Use Tailwind CSS and shadcn/ui as the design-system foundation.
- Use Lucide for icons and Recharts for operational visualizations.
- Validate inputs and display API-derived results without duplicating domain logic.
- Keep all user-facing content in English.

### Backend

- Exposes a FastAPI application with typed Pydantic request and response models.
- Provides `GET /api/health`, OpenAPI at `/api/openapi.json`, Swagger UI at `/docs`, and ReDoc at `/redoc`.
- Keep route handlers thin and place business rules in dedicated service modules.
- Uses structured English errors for application, request-validation, and database failures.
- Loads application, database, and CORS settings from environment variables.
- Reserves isolated packages for later AI and simulation work; no optimization, routing, or simulation behavior is implemented in Phase 1.

### Persistence

- Uses SQLAlchemy 2.x as the database abstraction.
- Select the database through environment configuration.
- Support SQLite for local development and PostgreSQL for deployed environments.
- Uses Alembic migrations for persistent schema changes.
- Enables SQLite foreign-key enforcement for local consistency.

## Phase 1 data model

`SimulationSession` is the ownership boundary for visitor data. Trains, platforms, track nodes, track edges, scheduling plans, incidents, and operational events carry a session reference. Assignments and compatibility rows belong to session-owned records. Future APIs must derive the active session from a trusted session context and include it in every read and mutation filter.

The schema contains:

- trains with identifiers, priority, integer arrival and departure minutes, minimum dwell time, physical length, platform type requirements, and explicit platform compatibility;
- platforms with type, length, and post-occupancy clearance minutes;
- track nodes and directed track edges with traversal time, capacity, and resource groups;
- scheduling plans and train-to-platform assignments;
- isolated simulation sessions;
- incidents and append-only operational events.

All scheduling values use integer minutes. Occupancy and horizon intervals are half-open: `[start, end)`. The start is occupied and the end is excluded, so adjacent intervals can meet at the same minute without overlapping. Database constraints and reusable Pydantic validators enforce non-empty intervals and core record validity.

## Repository shape

The application structure will be decided during the relevant implementation phase. The expected high-level boundaries are:

```text
backend/app/    FastAPI application, models, schemas, services, and database code
backend/alembic Database migration environment and revisions
backend/tests/  Pytest suite
docs/           Architecture and delivery tracking
```

The frontend has not been created because it is outside Phase 1.

## Configuration

Runtime configuration comes from environment variables. Local secret-bearing `.env` files are ignored; `.env.example` documents variable names without credentials. Browser-exposed variables are limited to non-secret values. PostgreSQL URLs are normalized to the psycopg v3 SQLAlchemy driver. Production configuration rejects wildcard CORS origins.

## Quality boundaries

- Business and optimization logic must be testable independently of HTTP and UI layers.
- Important backend behavior requires Pytest coverage.
- Frontend changes require type checking and a production build.
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

