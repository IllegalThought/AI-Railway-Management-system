"""Production deployment configuration regression tests."""

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_render_blueprint_uses_backend_root_health_gate_and_safe_secrets() -> None:
    blueprint = (REPOSITORY_ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "rootDir: backend" in blueprint
    assert "startCommand: bash scripts/start-production.sh" in blueprint
    assert "healthCheckPath: /api/health" in blueprint
    assert "autoDeployTrigger: checksPass" in blueprint
    assert "key: DATABASE_URL\n        sync: false" in blueprint
    assert "key: BACKEND_CORS_ORIGINS\n        sync: false" in blueprint


def test_render_start_command_runs_migration_and_binds_assigned_port() -> None:
    script = (REPOSITORY_ROOT / "backend/scripts/start-production.sh").read_text(
        encoding="utf-8"
    )
    assert "python -m alembic upgrade head" in script
    assert "python -m app.database.verify_schema" in script
    assert "--host 0.0.0.0" in script
    assert '--port "${PORT}"' in script
    assert "app.database.init_db" not in script
    assert "seed_demo" not in script


def test_vercel_configuration_builds_frontend_without_secret_values() -> None:
    configuration = json.loads(
        (REPOSITORY_ROOT / "frontend/vercel.json").read_text(encoding="utf-8")
    )
    assert configuration["framework"] == "nextjs"
    assert configuration["installCommand"] == "npm ci"
    assert configuration["buildCommand"] == "npm run build"

    frontend_environment = (
        REPOSITORY_ROOT / "frontend/.env.example"
    ).read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_API_BASE_URL=" in frontend_environment
    assert "DATABASE_URL" not in frontend_environment
    assert "PASSWORD" not in frontend_environment


def test_github_verification_workflow_contains_no_deployment_secrets() -> None:
    workflow = (
        REPOSITORY_ROOT / ".github/workflows/verify.yml"
    ).read_text(encoding="utf-8")
    assert "python -m alembic upgrade head" in workflow
    assert "python -m pytest -q" in workflow
    assert "npm run build" in workflow
    assert "secrets." not in workflow


def test_migrations_do_not_contain_sqlite_only_sql() -> None:
    migration_directory = REPOSITORY_ROOT / "backend/alembic/versions"
    migrations = sorted(migration_directory.glob("*.py"))

    assert len(migrations) == 6
    for migration in migrations:
        source = migration.read_text(encoding="utf-8")
        assert "PRAGMA" not in source
        assert "sqlite_" not in source


def test_backend_declares_psycopg_three_and_safe_connection_probe() -> None:
    requirements = (REPOSITORY_ROOT / "backend/requirements.txt").read_text(
        encoding="utf-8"
    )
    deployment_guide = (REPOSITORY_ROOT / "docs/DEPLOYMENT.md").read_text(
        encoding="utf-8"
    )

    assert "psycopg[binary]>=3.2,<4.0" in requirements
    assert "python -m app.database.check_connection" in deployment_guide
    assert "NEXT_PUBLIC_DATABASE_URL" in deployment_guide


def test_interactive_neon_migration_command_is_documented() -> None:
    migration_script = REPOSITORY_ROOT / "backend/scripts/migrate_neon.py"
    deployment_guide = (REPOSITORY_ROOT / "docs/DEPLOYMENT.md").read_text(
        encoding="utf-8"
    )

    assert migration_script.is_file()
    assert "python scripts/migrate_neon.py" in deployment_guide
