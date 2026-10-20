# RailOps AI Backend

This FastAPI service provides the persistence and operational-data APIs for the RailOps AI synthetic railway operations platform. It is not a certified railway signaling system.

## Requirements

- Python 3.11 or newer
- SQLite for local development
- PostgreSQL for production deployment

## Local setup

Run these commands from the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp -n ../.env.example .env
alembic upgrade head
python -m app.database.init_db --seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation is available at `http://127.0.0.1:8000/docs`, and the health endpoint is available at `http://127.0.0.1:8000/api/health`.

Operational requests require an `X-RailOps-Session` header containing a UUID. The frontend generates and retains this identifier in browser storage. An unknown UUID creates an isolated workspace populated with the 20-train, 5-platform normal-traffic scenario. Train and platform changes persist within that workspace.

Phase 3 endpoints include:

- train CRUD at `/api/trains`;
- platform reads and updates at `/api/platforms`;
- scenario discovery and restore at `/api/scenarios`;
- real workspace metrics at `/api/overview`.

`alembic upgrade head` is the preferred schema-management command. The initialization command is safe to rerun and can create the idempotent synthetic demonstration dataset with `--seed`.

## Tests

From `backend/` with the virtual environment active:

```bash
pytest
```

## Configuration

- `APP_ENV`: `development`, `test`, or `production`.
- `APP_NAME`: API display name.
- `APP_VERSION`: API version exposed through health and OpenAPI.
- `DATABASE_URL`: SQLAlchemy URL. The local default is `sqlite:///./railops.db`; deployment can use `postgresql+psycopg://...`.
- `BACKEND_CORS_ORIGINS`: comma-separated allowed origins. Wildcard origins are rejected in production.
- `NEXT_PUBLIC_API_BASE_URL`: non-secret frontend API origin, without an `/api` suffix.

All schedule and occupancy values are integer minutes. Intervals are half-open: `[start, end)`. An interval occupies its start minute and excludes its end minute, allowing adjacent assignments to meet without overlapping.

