from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.database import init_db
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
        assert database.scalar(select(func.count()).select_from(Platform)) == 2
        assert database.scalar(select(func.count()).select_from(Train)) == 1
    assert "created successfully" in first_message
    assert "already exists" in second_message
    engine.dispose()

