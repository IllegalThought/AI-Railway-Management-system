# Production Deployment Guide

RailOps AI is prepared as one GitHub monorepo with these deployment boundaries:

- `frontend/`: Next.js application deployed to Vercel
- `backend/`: FastAPI service deployed to Render
- Neon: managed PostgreSQL persistence
- `render.yaml`: Render Blueprint configuration
- `frontend/vercel.json`: Vercel build and response-header configuration
- `.github/workflows/verify.yml`: secret-free pull-request and main-branch verification

RailOps AI is a synthetic decision-support simulation. Deployment does not make it certified railway signaling, dispatch, or safety software.

## 1. Local release verification

From the repository root:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m app.database.verify_schema
.venv/bin/pytest -q

cd ../frontend
npm ci
npm test
npm run typecheck
npm run lint
npm run build
```

Local development continues to use `sqlite:///./railops.db`. Production settings fail fast unless `DATABASE_URL` resolves to PostgreSQL.

## 2. Push the monorepo to GitHub

Review changes before committing:

```bash
git status --short
git diff --check
git diff
git ls-files | grep -E '(^|/)(\.env|.*\.(db|sqlite|sqlite3))($|\.)'
```

Only safe `.env.example` templates should match. Then push through a normal reviewable commit:

```bash
git add .
git commit -m "chore: prepare Phase 9 production deployment"
git push -u origin main
```

If the GitHub remote has not been configured:

```bash
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

Do not put Neon, Render, or Vercel credentials in Git, GitHub Actions variables, or any `NEXT_PUBLIC_*` value. The included GitHub workflow uses SQLite and placeholder public origins, so it requires no secrets.

## 3. Create the Neon PostgreSQL database

1. Sign in to Neon and create a project and production branch.
2. Place the Neon region close to the Render service region to reduce database latency.
3. In **Connection Details**, select Python/SQLAlchemy-compatible connection information.
4. Copy a TLS-enabled PostgreSQL URL. Keep it only in a local ignored environment file or Render's secret environment settings.
5. Prefer the direct Neon endpoint for schema migrations. A pooled endpoint can be used for application traffic when needed; RailOps AI also maintains a small bounded SQLAlchemy pool.

The value should have this general form:

```text
postgresql://USER:PASSWORD@ENDPOINT.neon.tech/DATABASE?sslmode=require&channel_binding=require
```

The backend uses psycopg 3 and converts `postgres://` and `postgresql://` to SQLAlchemy's `postgresql+psycopg://` form internally. Query parameters issued by Neon, including `sslmode` and `channel_binding`, are preserved. Production configuration rejects PostgreSQL URLs that do not use `sslmode=require`, `verify-ca`, or `verify-full`.

Do not paste the URL into Vercel, source code, Git commands, issue trackers, screenshots, or this project's documentation. In particular, never create a `NEXT_PUBLIC_DATABASE_URL`; every `NEXT_PUBLIC_*` variable is available to browser code.

Neon data survives Render restarts and redeployments because it is stored outside the Render filesystem. Do not use a Render-local SQLite file in production.

## 4. Deploy the FastAPI backend to Render

### Blueprint method

1. In Render, choose **New > Blueprint**.
2. Connect the GitHub repository and select the repository-root `render.yaml`.
3. Enter secret values requested for `DATABASE_URL` and `BACKEND_CORS_ORIGINS`.
4. Select a Render region near the Neon project.
5. Review the service plan and create the service.

The Blueprint configures:

- root directory: `backend`
- runtime: Python, pinned through `backend/.python-version`
- build: `pip install -r requirements.txt`
- start: `bash scripts/start-production.sh`
- health check: `/api/health`
- graceful shutdown window: 30 seconds

The production startup script runs `alembic upgrade head`, verifies ORM/schema compatibility, and then binds Uvicorn to `0.0.0.0:$PORT`. It does not run a database reset or automatic seed. Alembic skips revisions already recorded as applied; pending revision data transformations still require the backup and review described below. For a paid Render service, moving migrations to a Render pre-deploy command is also valid; keep the schema verification before application startup.

### Manual web-service method

Use these exact Render fields:

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `bash scripts/start-production.sh` |
| Health Check Path | `/api/health` |
| Auto Deploy | After GitHub checks pass |

### Required backend environment variables

| Variable | Production value |
| --- | --- |
| `APP_ENV` | `production` |
| `APP_NAME` | `RailOps AI API` |
| `APP_VERSION` | `0.9.0` |
| `DATABASE_URL` | Secret Neon PostgreSQL URL with TLS |
| `BACKEND_CORS_ORIGINS` | Exact Vercel HTTPS origin(s), comma-separated |
| `MAX_REQUEST_BODY_BYTES` | `1048576` |
| `DATABASE_POOL_SIZE` | `5` |
| `DATABASE_MAX_OVERFLOW` | `5` |
| `DATABASE_POOL_TIMEOUT_SECONDS` | `10` |
| `DATABASE_POOL_RECYCLE_SECONDS` | `300` |

Render supplies `PORT`. Do not define it manually unless Render requires an override.

Production startup rejects SQLite, PostgreSQL without enforced TLS, wildcard CORS, non-HTTPS CORS origins, and origins containing paths, queries, or fragments.

## 5. Migrate the Neon database

From a trusted workstation, use the repository's guarded migration command with the direct Neon connection string:

```bash
cd backend
python scripts/migrate_neon.py
```

The script prompts for the URL without echoing it and never saves or prints it. It rejects non-PostgreSQL targets, non-Neon hosts, pooled Neon endpoints, and connections without enforced TLS. Before any connection or migration, it displays only the validated host and database name and requires you to type `MIGRATE`. It then performs a read-only schema preflight, runs the existing Alembic chain through `head`, and verifies the resulting schema. On failure it reports a sanitized error and does not run any reset, downgrade, deletion, or cleanup command.

For a new database, successful verification reports Alembic head `20261020_0006`. Do not use `alembic stamp head`: it records a revision without creating tables. The script does not seed data and does not copy records from local SQLite.

The committed revision chain was reviewed for PostgreSQL portability. It uses SQLAlchemy types, foreign keys, indexes, check constraints, and SQLAlchemy Core data updates rather than SQLite-only SQL. Revisions `20261020_0004` and `20261020_0005` read and update existing rows, so migrations must run online; offline `alembic upgrade --sql` generation is not supported. The interactive command is the final environment-specific verification because no Neon credentials are stored in this repository.

If the Neon database already contains important data, create a Neon backup or temporary branch before upgrading and verify it first. Revision `20261020_0004` intentionally rebuilds legacy synthetic topology rows while preserving their owning workspaces. The guarded script refuses to cross that revision when legacy topology rows exist, leaving the database untouched for an owner-reviewed migration plan. It also refuses RailOps AI tables that exist without Alembic revision tracking.

### Optional manual connection check

For a trusted workstation, configure the secret without putting it directly in a command that may be retained in shell history. Either create the already-ignored `backend/.env` file or use a hidden shell prompt.

### Ignored local environment file

```bash
cd backend
cp -n .env.example .env
chmod 600 .env
${EDITOR:-vi} .env
```

The `-n` option preserves an existing `.env`. Set `DATABASE_URL` in that file to the direct Neon URL. Keep `APP_ENV=development` for this pre-deployment check so no production frontend origin is required. Confirm the file is ignored with `git check-ignore .env`. Never use `git add -f` on it.

### Hidden shell prompt

```bash
cd backend
printf 'Neon DATABASE_URL: '
IFS= read -r -s DATABASE_URL
printf '\n'
export DATABASE_URL
```

The prompt does not echo the URL and the command itself contains no credential. Remove it from the shell when finished with `unset DATABASE_URL`.

Install the declared backend dependencies, then run the connection-only probe before changing the schema:

```bash
python -m pip install -r requirements.txt
python -m app.database.check_connection
```

The check executes only `SELECT 1`. Its output contains the database backend and success or failure, never the URL, hostname, username, password, or driver exception. A successful check proves connectivity, not schema compatibility. The interactive migration script already performs its own connection through Alembic, so this separate check is optional.

### Render migration behavior

The start script automatically applies committed migrations. To migrate manually from a Render shell or a trusted workstation:

```bash
cd backend
python -m app.database.check_connection
python -m alembic upgrade head
python -m app.database.verify_schema
```

On Render, set `DATABASE_URL` only through the service's secret environment settings before running these commands. Never print it in logs. The production start script performs the same upgrade and verification gates without resetting data.

## 6. Optional demo seed

The normal web experience lazily creates isolated synthetic data for each new UUID workspace. A shared fixed demo workspace is optional and is not required by the frontend. To create it once:

```bash
cd backend
python -m app.database.seed_demo
```

Run this only after the same shell or Render service has privately configured `DATABASE_URL`. The seed command is idempotent. Repeating it reports that the data exists and changes no records. `app.database.init_db` is intentionally disabled in production so deployments cannot bypass Alembic migration history.

Never run a scenario restore as a database initialization step. Scenario restore affects only the UUID workspace supplied in the request header, but it intentionally replaces that workspace's synthetic records.

## 7. Deploy the Next.js frontend to Vercel

1. In Vercel, choose **Add New Project** and import the same GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Keep the detected framework as Next.js.
4. Use Node.js `24.x`; `frontend/package.json` pins this supported major version.
5. Add `NEXT_PUBLIC_API_BASE_URL` for Production and any intended Preview environments.
6. Deploy after the Render service has a stable HTTPS URL.

Production example:

```text
NEXT_PUBLIC_API_BASE_URL=https://railops-ai-api.onrender.com
```

The value must be an origin only: no `/api`, path, query, fragment, or trailing route. Public production origins must use HTTPS. Database URLs, Neon passwords, and backend-only settings must never use the `NEXT_PUBLIC_` prefix.

Vercel reads `frontend/vercel.json`, runs `npm ci` and `npm run build`, and applies baseline browser response headers. Next.js App Router owns all application routes, so direct navigation and page refreshes do not require custom rewrite rules.

## 8. Configure exact CORS origins

After Vercel assigns the production URL, set Render's `BACKEND_CORS_ORIGINS` to the exact origin:

```text
https://railops-ai.vercel.app
```

For more than one real frontend origin:

```text
https://railops-ai.vercel.app,https://railops.example.com
```

Do not use `*`. Vercel preview deployments receive changing hostnames; either add a specific preview URL temporarily, use a stable custom preview domain, or test previews against a separate backend with a deliberately scoped origin list.

After changing CORS, redeploy or restart Render and test a browser request from the actual Vercel origin.

## 9. Deployment testing

Replace the example hosts below with the created services.

### Backend health and CORS

```bash
curl --fail --show-error https://YOUR_RENDER_HOST/api/health
curl --fail --show-error \
  -H 'Origin: https://YOUR_VERCEL_HOST' \
  -H 'Access-Control-Request-Method: GET' \
  -X OPTIONS \
  https://YOUR_RENDER_HOST/api/overview
```

Confirm `access-control-allow-origin` contains the exact Vercel origin.

### Isolated workspace check

```bash
SESSION_ONE='00000000-0000-4000-8000-000000000091'
SESSION_TWO='00000000-0000-4000-8000-000000000092'

curl --fail --show-error \
  -H "X-RailOps-Session: ${SESSION_ONE}" \
  https://YOUR_RENDER_HOST/api/overview

curl --fail --show-error \
  -H "X-RailOps-Session: ${SESSION_TWO}" \
  https://YOUR_RENDER_HOST/api/overview
```

Mutate only a disposable test workspace and confirm the second workspace remains unchanged.

### Browser workflow

1. Load Overview and confirm API and database readiness.
2. Open Trains & Platforms and read seeded records.
3. Generate, validate, and apply a plan.
4. Open Network Monitor and Live Operations.
5. Create an incident, calculate a revision, and apply it.
6. Open Performance Analytics and run the bounded algorithm comparison.
7. Refresh every route directly and confirm it remains available.
8. Redeploy Render and confirm the same browser workspace still contains its records.

## 10. Troubleshooting

### Render reports a missing `PORT`

Use `bash scripts/start-production.sh` as the start command. Render supplies `PORT` only at runtime.

### Render health check times out

Confirm the process binds to `0.0.0.0`, migrations completed, Neon accepts the connection, and `/api/health` returns HTTP 200 in logs.

### `Production requires a PostgreSQL DATABASE_URL`

`APP_ENV=production` was combined with a missing or SQLite URL. Set the Neon URL in Render's secret environment settings.

### Database connection or TLS failure

Copy a fresh Neon connection string, retain `sslmode=require`, verify password encoding, and confirm Neon compute availability. Do not log or paste the secret into issue trackers.

### `Pending Alembic migrations` or model/schema drift

Run `python -m alembic upgrade head`, then `python -m app.database.verify_schema`. Do not use `alembic stamp head`, edit applied migrations, or reset the database.

### Browser shows “Backend configuration error”

Set `NEXT_PUBLIC_API_BASE_URL` to the Render HTTPS origin only, then trigger a new Vercel build. Next.js public values are embedded during the build.

### Browser shows “Backend unreachable”

Open the Render health URL directly, inspect Render logs, and check whether a free service is waking from suspension. This message does not imply the database is unavailable.

### Browser request is blocked by CORS

Compare the browser's exact `Origin` header with `BACKEND_CORS_ORIGINS`. Scheme, hostname, and port must match; paths do not belong in an origin.

### Analytics or scheduling returns validation errors

Public requests are intentionally bounded to 500,000 CSP nodes and 15 seconds of CP-SAT time. Use supported limits and inspect the structured error response.

### Records disappear after a backend redeploy

Confirm Render uses Neon PostgreSQL rather than SQLite and that the production `DATABASE_URL` did not change to another Neon branch.

## 11. Security and operational limitations

- UUID demo workspaces isolate data but are not authenticated accounts.
- No global reset or unrestricted database administration endpoint is exposed.
- Request bodies, record fields, scheduling search, and CP-SAT duration are bounded.
- Render or an upstream edge should additionally enforce request rates and chunked-body limits.
- Before unrestricted public use, add authentication, authorization, server-issued session expiry, rate limiting, abuse monitoring, and retention policies.
- Use Neon backups or branches before high-risk migrations and monitor Render logs, latency, database connections, 409 conflicts, 413 responses, and solver duration.

## 12. External permissions still required

Repository preparation does not create external services. The repository owner must authenticate with GitHub, Neon, Render, and Vercel; create or select the projects; enter secrets; authorize Git access; and verify the resulting live URLs. Do not report deployment success until those live checks pass.

Provider references: [Render Blueprints](https://render.com/docs/blueprint-spec), [Render monorepos](https://render.com/docs/monorepo-support), [Render health checks](https://render.com/docs/health-checks), [Vercel monorepos](https://vercel.com/docs/monorepos), [Vercel environment variables](https://vercel.com/docs/environment-variables), and [Neon compute and pooling](https://neon.com/docs/manage/endpoints/).
