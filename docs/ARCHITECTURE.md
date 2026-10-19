# RailOps AI Architecture

## System purpose

RailOps AI is a synthetic railway operations management and decision-support simulation. It will combine an operational web interface with optimization, graph analysis, and explainable AI workflows. It is not certified signaling software and must not be used to control real railway infrastructure.

## Planned system context

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

## Planned responsibilities

### Frontend

- Present a professional operations interface using Next.js and TypeScript.
- Use Tailwind CSS and shadcn/ui as the design-system foundation.
- Use Lucide for icons and Recharts for operational visualizations.
- Validate inputs and display API-derived results without duplicating domain logic.
- Keep all user-facing content in English.

### Backend

- Expose versioned FastAPI endpoints with Pydantic request and response models.
- Keep route handlers thin and place business rules in dedicated service modules.
- Run genuine optimization and graph algorithms through OR-Tools and NetworkX.
- Return traceable inputs, statuses, constraints, and explanations for generated results.
- Reject invalid or infeasible requests with clear English errors.

### Persistence

- Use SQLAlchemy as the database abstraction.
- Select the database through environment configuration.
- Support SQLite for local development and PostgreSQL for deployed environments.
- Introduce schema migrations when persistent models are added.

## Proposed repository shape

The application structure will be decided during the relevant implementation phase. The expected high-level boundaries are:

```text
frontend/       Next.js application
backend/        FastAPI application, domain services, and tests
docs/           Architecture and delivery tracking
```

These directories are architectural guidance, not evidence that the applications have already been implemented.

## Configuration

Runtime configuration must come from environment variables. Local secret-bearing `.env` files are ignored; `.env.example` documents variable names without credentials. Browser-exposed variables must be limited to non-secret values.

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

