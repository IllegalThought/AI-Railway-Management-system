#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${PORT:-}" ]]; then
  echo "ERROR: PORT is required by the production service." >&2
  exit 1
fi

echo "Applying pending database migrations."
python -m alembic upgrade head

echo "Verifying database schema compatibility."
python -m app.database.verify_schema

echo "Starting RailOps AI API on 0.0.0.0:${PORT}."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --proxy-headers \
  --forwarded-allow-ips="*"
