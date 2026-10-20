import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.database import init_db, seed_demo
from app.config import Settings
from app.database.session import build_engine
from app.models import Platform, SimulationSession, Train


def test_database_initialization_and_seed_are_idempotent(tmp_path, monkeypatch) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'initialized.db'}")
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr(init_db, "engine", engine)
    monkeypatch.setattr(init_db, "SessionLocal", session_factory)

    first_message = init_db.initialize_database(seed=True)
    second_message = init_db.initialize_database(seed=True)

    with session_factory() as database:
        assert database.scalar(select(func.count()).select_from(SimulationSession)) == 1
        assert database.scalar(select(func.count()).select_from(Platform)) == 5
        assert database.scalar(select(func.count()).select_from(Train)) == 20
    assert "created successfully" in first_message
    assert "already exists" in second_message
    engine.dispose()


def test_direct_schema_initialization_is_disabled_in_production(monkeypatch) -> None:
    production = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql://railops:placeholder@database.example/railops?sslmode=require",
        BACKEND_CORS_ORIGINS="https://railops.example",
    )
    monkeypatch.setattr(init_db, "get_settings", lambda: production)
    with pytest.raises(RuntimeError, match="use Alembic migrations"):
        init_db.initialize_database(seed=True)


def test_deployment_seed_command_is_idempotent(database_engine, monkeypatch) -> None:
    session_factory = sessionmaker(
        bind=database_engine, autoflush=False, expire_on_commit=False
    )
    monkeypatch.setattr(seed_demo, "SessionLocal", session_factory)

    assert "created successfully" in seed_demo.seed_production_demo()
    assert "already exists" in seed_demo.seed_production_demo()

    with session_factory() as database:
        assert database.scalar(select(func.count()).select_from(SimulationSession)) == 1
        assert database.scalar(select(func.count()).select_from(Platform)) == 5
        assert database.scalar(select(func.count()).select_from(Train)) == 20

