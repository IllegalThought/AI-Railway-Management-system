from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def build_engine(
    database_url: str,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 5,
    pool_timeout: int = 10,
    pool_recycle: int = 300,
) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    pool_options = {}
    if not database_url.startswith("sqlite"):
        pool_options = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
        }
    database_engine = create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,
        connect_args=connect_args,
        **pool_options,
    )
    if database_url.startswith("sqlite"):
        @event.listens_for(database_engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return database_engine


runtime_settings: Settings = get_settings()
engine = build_engine(
    runtime_settings.database_url,
    pool_size=runtime_settings.database_pool_size,
    max_overflow=runtime_settings.database_max_overflow,
    pool_timeout=runtime_settings.database_pool_timeout_seconds,
    pool_recycle=runtime_settings.database_pool_recycle_seconds,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()

