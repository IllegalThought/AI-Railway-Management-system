# RailOps AI

RailOps AI is a professional synthetic railway operations management and decision-support platform. It combines train and platform records, constraint-based dispatch planning, route reservation, live simulation, incident response, dynamic replanning, and measured analytics in one workspace.

> RailOps AI is a simulation for demonstration and evaluation. It is not certified railway signaling, dispatch, or safety software and must not control real infrastructure.

## Release-candidate capabilities

- Isolated 20-train, 5-platform demo workspaces and five deterministic scenarios
- Train management and platform availability controls
- FCFS, custom CSP, and OR-Tools CP-SAT platform scheduling
- Independent hard-constraint validation and version-safe plan application
- Custom A* routing, NetworkX reference checking, and exclusive resource reservations
- Forward-chaining movement inference with evidence-backed explanations
- Backend-owned simulation time, live movement projection, and incident management
- Committed-movement-safe dynamic replanning
- Actual delay, utilization, conflict, feasibility, timing, trend, and benchmark analytics
- Responsive dark enterprise interface with explicit loading, empty, and error states

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Lucide, Recharts |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| AI and optimization | Custom CSP/backtracking/MRV/forward checking, OR-Tools CP-SAT, custom A*, NetworkX, forward chaining |
| Data | SQLite locally, PostgreSQL in deployment, Alembic migrations |
| Validation | Pytest, Vitest, ESLint, TypeScript, Next.js production build |

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m app.database.init_db --seed
.venv/bin/uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`; Swagger documentation is at `/docs`.

### Frontend

```bash
cd frontend
npm install
printf 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8000\n' > .env.local
npm run dev
```

Open `http://localhost:3000`. The browser creates a UUID workspace identifier and sends it through `X-RailOps-Session` for operational endpoints.

## Verification

```bash
cd backend
.venv/bin/python -m app.database.verify_schema
.venv/bin/pytest -q

cd ../frontend
npm test
npm run typecheck
npm run lint
npm run build
```

The schema verifier checks the active database path, Alembic head, missing tables or columns, and ORM/schema drift. Run it after every model or migration change and before starting the API.

## Configuration

Copy `.env.example` values into local or deployment environment configuration. Never commit `.env`, database, or credential files.

| Variable | Purpose |
| --- | --- |
| `APP_ENV` | `development`, `test`, or `production` |
| `APP_NAME` | API service name |
| `APP_VERSION` | Reported application version |
| `DATABASE_URL` | SQLite or PostgreSQL SQLAlchemy URL |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `MAX_REQUEST_BODY_BYTES` | Request content-length ceiling; defaults to 1 MiB |
| `NEXT_PUBLIC_API_BASE_URL` | Public browser-visible backend origin |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Algorithms](docs/ALGORITHMS.md)
- [API reference](docs/API_REFERENCE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Project report](docs/PROJECT_REPORT.md)
- [Syllabus mapping](docs/SYLLABUS_MAPPING.md)
- [Viva questions](docs/VIVA_QUESTIONS.md)
- [Progress and validation](docs/PROGRESS.md)

## Known limitations

- The demo-session UUID provides data isolation, not user authentication or role-based authorization.
- Track resources are reserved exclusively even when topology capacity is greater than one.
- SQLite is intended for local use; public deployment should use managed PostgreSQL.
- Solver limits bound search but the API does not provide distributed job scheduling or per-user rate limiting.
- Results depend on the modeled synthetic station, constraints, incidents, and integer-minute resolution.

See [Deployment](docs/DEPLOYMENT.md) for Vercel, Render, PostgreSQL, CORS, and migration guidance.
