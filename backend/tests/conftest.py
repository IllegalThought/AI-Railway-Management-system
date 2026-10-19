import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Configure the pytest process before importing modules that initialize cached
# settings, the application, or the default database engine.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"

from app.config import Settings, get_settings
from app.database.base import Base
from app.database.session import build_engine, get_db
from app.main import create_app
from app import models  # noqa: F401 - imports models into SQLAlchemy metadata


@pytest.fixture(autouse=True)
def isolate_settings_cache() -> Generator[None, None, None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def database_engine(tmp_path) -> Generator[Engine, None, None]:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def database(database_engine: Engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(
        bind=database_engine, autoflush=False, expire_on_commit=False
    )
    with session_factory() as session:
        yield session


@pytest.fixture
def client(database_engine: Engine) -> Generator[TestClient, None, None]:
    session_factory = sessionmaker(
        bind=database_engine, autoflush=False, expire_on_commit=False
    )
    settings = Settings(
        APP_ENV="test",
        DATABASE_URL="sqlite://",
        BACKEND_CORS_ORIGINS="http://localhost:3000",
    )
    app = create_app(settings)

    def override_database() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client

