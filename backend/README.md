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
cp -n .env.example .env
alembic upgrade head
python -m app.database.verify_schema
python -m app.database.init_db --seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation is available at `http://127.0.0.1:8000/docs`, and the health endpoint is available at `http://127.0.0.1:8000/api/health`.

Operational requests require an `X-RailOps-Session` header containing a UUID. The frontend generates and retains this identifier in browser storage. An unknown UUID creates an isolated workspace populated with the 20-train, 5-platform normal-traffic scenario. Train and platform changes persist within that workspace.

Operational endpoints include:

- train CRUD at `/api/trains`;
- platform reads and updates at `/api/platforms`;
- scenario discovery and restore at `/api/scenarios`;
- real workspace metrics at `/api/overview`;
- schedule generation, combined platform/route validation, apply, and current-plan reads at `/api/schedules`;
- route state at `/api/network`, simulation controls at `/api/simulation`, incidents and replanning at `/api/incidents`, and measured analytics at `/api/analytics`.

`alembic upgrade head` is the preferred schema-management command. Run `python -m app.database.verify_schema` after every migration; it fails on a missing table or column, a pending revision, model/schema drift, or a relative/missing active SQLite path. The initialization command is safe to rerun and can create the idempotent synthetic demonstration dataset with `--seed`.

Production uses `bash scripts/start-production.sh`. It requires Render's `PORT`, applies migrations, verifies schema compatibility, and starts Uvicorn on `0.0.0.0`. Direct `init_db` schema creation is disabled when `APP_ENV=production`; the optional `python -m app.database.seed_demo` command adds demonstration records idempotently after migrations.

## Tests

From `backend/` with the virtual environment active:

```bash
pytest
python -m app.database.verify_schema
```

## Configuration

- `APP_ENV`: `development`, `test`, or `production`.
- `APP_NAME`: API display name.
- `APP_VERSION`: API version exposed through health and OpenAPI.
- `DATABASE_URL`: SQLAlchemy URL. The local default is anchored to `backend/railops.db` regardless of the launch working directory; deployment can use `postgresql+psycopg://...`.
- `BACKEND_CORS_ORIGINS`: comma-separated exact origins. Production requires HTTPS and rejects wildcards, paths, queries, and fragments.
- `MAX_REQUEST_BODY_BYTES`: declared request-body ceiling; defaults to 1 MiB.
- `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT_SECONDS`, and `DATABASE_POOL_RECYCLE_SECONDS`: bounded PostgreSQL connection-pool controls.
- `NEXT_PUBLIC_API_BASE_URL`: non-secret frontend-only API origin, without an `/api` suffix.

All schedule and occupancy values are integer minutes. Intervals are half-open: `[start, end)`. An interval occupies its start minute and excludes its end minute, allowing adjacent assignments to meet without overlapping.

