# Deployment Guide

The intended deployment is a Next.js frontend on Vercel, a FastAPI backend on Render, and managed PostgreSQL. SQLite is for local development only.

## Production prerequisites

- A PostgreSQL database and private connection URL
- A Render web service using the `backend` directory
- A Vercel project using the `frontend` directory
- Exact deployed frontend and backend HTTPS origins
- Python and Node versions supported by the declared dependencies

## Render backend

Use `backend` as the root directory.

- Build command: `pip install -r requirements.txt`
- Pre-deploy command: `alembic upgrade head`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Configure:

```text
APP_ENV=production
APP_NAME=RailOps AI API
APP_VERSION=0.8.0
DATABASE_URL=<managed PostgreSQL URL>
BACKEND_CORS_ORIGINS=https://<your-vercel-domain>
MAX_REQUEST_BODY_BYTES=1048576
```

PostgreSQL URLs beginning with `postgres://` or `postgresql://` are normalized to the psycopg 3 driver. Never use wildcard CORS in production; the application rejects it.

Run `python -m app.database.verify_schema` after the migration and before routing traffic. The process must exit successfully and report the expected Alembic head with no drift.

## Vercel frontend

Use `frontend` as the root directory and the standard Next.js framework preset. Configure:

```text
NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>
```

This value is intentionally browser-visible and must contain only the public API origin. Do not put credentials in any `NEXT_PUBLIC_*` variable.

## Safe database updates

1. Back up the production database using the provider snapshot facility.
2. Review the new Alembic revision and its downgrade behavior.
3. Apply `alembic upgrade head` to the configured production URL.
4. Run `python -m app.database.verify_schema`.
5. Check `/api/health`, then test an isolated workspace workflow.

Do not use `alembic stamp head` to hide drift, edit an applied migration, or reset production data. Model changes require a new migration and an upgrade regression test.

## Release verification

```bash
cd backend
python -m app.database.verify_schema
pytest -q

cd ../frontend
npm ci
npm test
npm run typecheck
npm run lint
npm run build
```

Check Git tracking before deployment:

```bash
git ls-files | grep -E '(^|/)(\.env|.*\.(db|sqlite|sqlite3))($|\.)'
```

Only `.env.example` should match. Local `.env*`, `.next`, `node_modules`, and database files are ignored.

## Security and operating notes

- The API limits declared request sizes, applies no-store and browser hardening headers, validates payload bounds, and constrains CSP nodes and CP-SAT time.
- Scenario restore is destructive only inside the caller's isolated workspace; no global reset or administration endpoint is exposed.
- The workspace UUID is not authentication. Add an identity provider, authorization, server-side session issuance, expiry, rate limiting, audit retention, and abuse protection before offering a multi-user production service.
- Use managed PostgreSQL backups, TLS, log retention, dependency scanning, and platform resource ceilings.
- Monitor health, 409 rates, 413 responses, database errors, solver duration, CPU, memory, and database connections.

## Rollback

Prefer application rollback while keeping forward-compatible schema additions. Use Alembic downgrade only after reviewing data-loss implications and restoring a verified backup if necessary. Never delete the live database to resolve a migration problem.
