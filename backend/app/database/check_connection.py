"""Perform a read-only database connectivity check without printing credentials."""

from __future__ import annotations

from dataclasses import dataclass
import sys

from sqlalchemy import text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings


@dataclass(frozen=True)
class ConnectionCheck:
    database_backend: str
    connected: bool


def _build_engine(database_url: str, **pool_options: int) -> Engine:
    # Import lazily so even malformed configuration can be reported without a
    # module-import traceback that might include environment input.
    from app.database.session import build_engine

    return build_engine(database_url, **pool_options)


def check_database_connection(database_url: str | None = None) -> ConnectionCheck:
    """Execute a harmless query and return only non-secret connection metadata."""

    database_backend = "unknown"
    database_engine = None
    try:
        settings = get_settings()
        resolved_url = database_url or settings.database_url
        database_backend = make_url(resolved_url).get_backend_name()
        database_engine = _build_engine(
            resolved_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
        )
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    except (SQLAlchemyError, ValueError):
        return ConnectionCheck(database_backend=database_backend, connected=False)
    finally:
        if database_engine is not None:
            database_engine.dispose()
    return ConnectionCheck(database_backend=database_backend, connected=True)


def main() -> int:
    result = check_database_connection()
    if result.connected:
        print(f"Database connection successful ({result.database_backend}).")
        return 0
    print(
        f"Database connection failed ({result.database_backend}). "
        "Check DATABASE_URL, TLS settings, network access, and database availability. "
        "Credentials were not displayed.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
