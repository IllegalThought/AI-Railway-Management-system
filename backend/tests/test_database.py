from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app import models  # noqa: F401 - register mapped tables for DDL compilation
from app.database.base import Base
from app.database import session as database_session
from app.config import Settings
from app.database.session import build_engine
from app.models import Platform, Train
from app.schemas.railway import PlatformCreate, TrainCreate
from app.services.records import create_platform, create_simulation_session, create_train


def test_sqlite_foreign_key_enforcement_is_enabled(database) -> None:
    assert database.scalar(text("PRAGMA foreign_keys")) == 1


def test_records_are_scoped_to_independent_simulation_sessions(database) -> None:
    first = create_simulation_session(database, name="First visitor")
    second = create_simulation_session(database, name="Second visitor")
    payload = PlatformCreate(
        code="P1",
        platform_type="passenger",
        length_meters=300,
        clearance_minutes=3,
    )

    create_platform(database, session_id=first.id, data=payload)
    create_platform(database, session_id=second.id, data=payload)

    first_platforms = database.scalars(
        select(Platform).where(Platform.session_id == first.id)
    ).all()
    second_platforms = database.scalars(
        select(Platform).where(Platform.session_id == second.id)
    ).all()
    assert [platform.code for platform in first_platforms] == ["P1"]
    assert [platform.code for platform in second_platforms] == ["P1"]


def test_train_persists_platform_compatibility(database) -> None:
    demo = create_simulation_session(database, name="Compatibility test")
    create_platform(
        database,
        session_id=demo.id,
        data=PlatformCreate(
            code="P1",
            platform_type="passenger",
            length_meters=300,
            clearance_minutes=3,
        ),
    )
    train = create_train(
        database,
        session_id=demo.id,
        data=TrainCreate(
            identifier="RA-303",
            priority=4,
            arrival_minute=300,
            departure_minute=320,
            minimum_dwell_minutes=10,
            length_meters=240,
            required_platform_type="passenger",
            compatible_platform_codes=["P1"],
        ),
    )

    stored = database.scalar(select(Train).where(Train.id == train.id))
    assert stored is not None
    assert stored.compatible_platforms[0].platform.code == "P1"


def test_request_database_session_rolls_back_after_an_error(monkeypatch) -> None:
    class FakeSession:
        rolled_back = False
        closed = False

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    fake = FakeSession()
    monkeypatch.setattr(database_session, "SessionLocal", lambda: fake)
    dependency = database_session.get_db()
    assert next(dependency) is fake

    try:
        dependency.throw(RuntimeError("request failed"))
    except RuntimeError:
        pass

    assert fake.rolled_back is True
    assert fake.closed is True


def test_postgresql_engine_uses_bounded_recycled_pool_without_connecting() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://railops:placeholder@database.example/railops?sslmode=require",
        DATABASE_POOL_SIZE=4,
        DATABASE_MAX_OVERFLOW=3,
        DATABASE_POOL_TIMEOUT_SECONDS=9,
        DATABASE_POOL_RECYCLE_SECONDS=240,
    )
    engine = build_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
    )
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.pool.size() == 4
        assert engine.pool._max_overflow == 3
        assert engine.pool._timeout == 9
        assert engine.pool._recycle == 240
    finally:
        engine.dispose()


def test_complete_model_schema_compiles_for_postgresql() -> None:
    dialect = postgresql.dialect()
    statements = [
        str(CreateTable(table).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
    ]
    assert len(statements) == len(Base.metadata.tables)
    assert all("CREATE TABLE" in statement for statement in statements)

