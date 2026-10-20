from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database.session import build_engine, get_db
from app.database.verify_schema import verify_schema
from app.main import create_app
from app.models import SchedulingPlan


def _alembic_config(database_url: str) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_existing_phase6_database_upgrades_without_losing_plan_or_api_functionality(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "existing-phase6.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = _alembic_config(database_url)
    command.upgrade(config, "20261020_0005")
    engine = build_engine(database_url)
    existing_public_id = str(uuid4())
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(text("""
            INSERT INTO simulation_sessions
                (public_id, name, session_key, status, expires_at, scenario_key, created_at, updated_at)
            VALUES (:public_id, 'Existing workspace', NULL, 'ACTIVE', NULL, 'normal-traffic', :now, :now)
        """), {"public_id": existing_public_id, "now": now})
        session_id = connection.execute(text("SELECT id FROM simulation_sessions WHERE public_id = :public_id"), {"public_id": existing_public_id}).scalar_one()
        connection.execute(text("""
            INSERT INTO scheduling_plans
                (session_id, name, status, horizon_start_minute, horizon_end_minute, created_at, updated_at,
                 version, engine, solver_status, objective_value, maximum_delay_minutes, is_validated,
                 explanation, route_validated)
            VALUES (:session_id, 'Existing plan', 'APPLIED', 0, 120, :now, :now,
                    1, 'csp', 'FEASIBLE', 0, 30, 1, 'Existing persisted result.', 1)
        """), {"session_id": session_id, "now": now})
        plan_id = connection.execute(text("SELECT id FROM scheduling_plans WHERE session_id = :session_id"), {"session_id": session_id}).scalar_one()
        connection.execute(text("""
            INSERT INTO simulation_states
                (session_id, current_minute, run_status, speed, revision, active_plan_id, last_tick_at, created_at, updated_at)
            VALUES (:session_id, 0, 'PAUSED', 1, 0, :plan_id, NULL, :now, :now)
        """), {"session_id": session_id, "plan_id": plan_id, "now": now})
    engine.dispose()

    pending = verify_schema(database_url)
    assert not pending.compatible
    assert any("Pending Alembic migrations" in error for error in pending.errors)
    assert any("scheduling_plans.execution_time_ms" in error for error in pending.errors)

    command.upgrade(config, "head")
    upgraded_engine = build_engine(database_url)
    assert "execution_time_ms" in {column["name"] for column in inspect(upgraded_engine).get_columns("scheduling_plans")}
    assert verify_schema(database_url).compatible
    session_factory = sessionmaker(bind=upgraded_engine, autoflush=False, expire_on_commit=False)
    with session_factory() as database:
        existing_plan = database.scalar(select(SchedulingPlan).where(SchedulingPlan.id == plan_id))
        assert existing_plan is not None
        assert existing_plan.name == "Existing plan"
        assert existing_plan.execution_time_ms is None

    app = create_app(Settings(APP_ENV="test", DATABASE_URL=database_url, BACKEND_CORS_ORIGINS="http://localhost:3000"))
    def override_database():
        with session_factory() as database:
            yield database
    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        existing_headers = {"X-RailOps-Session": existing_public_id}
        analytics = client.get("/api/analytics", headers=existing_headers)
        assert analytics.status_code == 200
        assert analytics.json()["metrics"]["plan_id"] == plan_id
        assert analytics.json()["metrics"]["solver_execution_time_ms"] is None
        assert client.get("/api/simulation/state", headers=existing_headers).status_code == 200

        fresh_headers = {"X-RailOps-Session": str(uuid4())}
        generated = client.post("/api/schedules/generate", headers=fresh_headers, json={"engine": "csp"})
        assert generated.status_code == 201
        assert generated.json()["execution_time_ms"] >= 0
    upgraded_engine.dispose()
    get_settings.cache_clear()
