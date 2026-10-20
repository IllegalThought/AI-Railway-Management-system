"""Verify that the configured database matches the Alembic and ORM schema."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import make_url

from app import models  # noqa: F401 - register every mapped table
from app.config import BACKEND_ROOT, get_settings
from app.database.base import Base
from app.database.session import build_engine


@dataclass(frozen=True)
class SchemaVerification:
    database_backend: str
    database_path: str | None
    current_revision: str | None
    head_revisions: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def compatible(self) -> bool:
        return not self.errors


def verify_schema(database_url: str | None = None) -> SchemaVerification:
    resolved_url = database_url or get_settings().database_url
    url = make_url(resolved_url)
    database_path: str | None = None
    errors: list[str] = []
    if url.get_backend_name() == "sqlite" and url.database not in {None, "", ":memory:"}:
        path = Path(url.database).expanduser()
        if not path.is_absolute():
            errors.append(f"The active SQLite database path is relative: {path}.")
            path = path.resolve()
        database_path = str(path)
        if not path.exists():
            errors.append(f"The active SQLite database does not exist: {path}.")

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    heads = tuple(scripts.get_heads())
    engine = build_engine(resolved_url)
    current: str | None = None
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            current = context.get_current_revision()
            if current not in heads:
                errors.append(f"Pending Alembic migrations: database is at {current or 'no revision'}, expected {', '.join(heads)}.")

            inspector = inspect(connection)
            for table_name, table in Base.metadata.tables.items():
                if not inspector.has_table(table_name):
                    errors.append(f"Missing database table: {table_name}.")
                    continue
                actual_columns = {item["name"] for item in inspector.get_columns(table_name)}
                for column_name in set(table.columns.keys()) - actual_columns:
                    errors.append(f"Missing database column: {table_name}.{column_name}.")

            for difference in compare_metadata(context, Base.metadata):
                errors.append(f"Model/schema drift: {difference!r}.")
    finally:
        engine.dispose()

    return SchemaVerification(url.get_backend_name(), database_path, current, heads, tuple(errors))


def main() -> int:
    result = verify_schema()
    print(f"Database backend: {result.database_backend}")
    if result.database_path:
        print(f"Active database path: {result.database_path}")
    print(f"Current Alembic revision: {result.current_revision or 'none'}")
    print(f"Expected Alembic head: {', '.join(result.head_revisions)}")
    if result.compatible:
        print("Database schema is compatible with the SQLAlchemy models.")
        return 0
    for error in result.errors:
        print(f"ERROR: {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
