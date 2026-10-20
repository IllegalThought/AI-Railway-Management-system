#!/usr/bin/env python3
"""Interactively apply the project's Alembic migrations to Neon PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass
import os
from pathlib import Path
import sys
from typing import Callable
import unicodedata

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.pool import NullPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class NeonTargetError(ValueError):
    """Raised when a supplied URL is not a safe direct Neon target."""


class MigrationSafetyError(RuntimeError):
    """Raised when an existing schema needs owner review before migration."""


@dataclass(frozen=True)
class NeonTarget:
    database_url: str
    host: str
    database: str


@dataclass(frozen=True)
class MigrationResult:
    current_revision: str | None
    head_revisions: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def compatible(self) -> bool:
        return not self.errors


APP_TABLES = {
    "simulation_sessions",
    "platforms",
    "trains",
    "track_nodes",
    "track_edges",
    "scheduling_plans",
    "incidents",
    "operational_events",
    "train_platform_compatibility",
    "train_assignments",
    "route_movements",
    "route_reservations",
    "simulation_states",
    "solver_benchmarks",
}
PRE_TOPOLOGY_REBUILD_REVISIONS = {
    "20261020_0001",
    "20261020_0002",
    "20261020_0003",
}


def _contains_control_characters(value: str) -> bool:
    return any(unicodedata.category(character).startswith("C") for character in value)


def validate_neon_direct_url(value: str) -> NeonTarget:
    """Validate and normalize a direct, TLS-enforced Neon PostgreSQL URL."""

    try:
        parsed = make_url(value.strip())
    except (ArgumentError, ValueError) as error:
        raise NeonTargetError("The connection string is not a valid database URL.") from error

    if parsed.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise NeonTargetError("The target must use PostgreSQL with the psycopg driver.")

    host = (parsed.host or "").rstrip(".").lower()
    if not host.endswith(".neon.tech"):
        raise NeonTargetError("The target host must be a Neon PostgreSQL endpoint.")
    if any(label.endswith("-pooler") for label in host.split(".")):
        raise NeonTargetError(
            "Use the direct Neon endpoint for migrations, not the pooled endpoint."
        )

    database = parsed.database or ""
    if not parsed.username or not parsed.password or not database:
        raise NeonTargetError(
            "The Neon connection string must include a user, password, and database name."
        )
    if _contains_control_characters(host) or _contains_control_characters(database):
        raise NeonTargetError("The target host and database name contain invalid characters.")

    ssl_mode = str(parsed.query.get("sslmode", "")).lower()
    if ssl_mode not in {"require", "verify-ca", "verify-full"}:
        raise NeonTargetError(
            "The Neon connection string must enforce TLS with sslmode=require, "
            "verify-ca, or verify-full."
        )

    normalized: URL = parsed.set(drivername="postgresql+psycopg")
    return NeonTarget(
        database_url=normalized.render_as_string(hide_password=False),
        host=host,
        database=database,
    )


def assert_safe_existing_state(database_url: str) -> None:
    """Refuse ambiguous or data-rebuilding upgrades without touching the schema."""

    engine = create_engine(database_url, poolclass=NullPool, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            table_names = set(inspector.get_table_names())
            current_revision = MigrationContext.configure(
                connection
            ).get_current_revision()

            unmanaged_app_tables = APP_TABLES.intersection(table_names)
            if current_revision is None and unmanaged_app_tables:
                raise MigrationSafetyError(
                    "RailOps AI tables exist without an Alembic revision. No migration "
                    "was applied; inspect and back up this database before continuing."
                )

            if current_revision in PRE_TOPOLOGY_REBUILD_REVISIONS:
                legacy_rows = 0
                for table_name in ("track_nodes", "track_edges"):
                    if table_name in table_names:
                        legacy_rows += connection.execute(
                            text(f"SELECT COUNT(*) FROM {table_name}")
                        ).scalar_one()
                if legacy_rows:
                    raise MigrationSafetyError(
                        "Legacy topology records exist before revision 20261020_0004. "
                        "No migration was applied because that historical revision "
                        "rebuilds synthetic topology data. Create a Neon backup or branch "
                        "and use an owner-reviewed migration plan."
                    )
    finally:
        engine.dispose()


def apply_migrations(database_url: str) -> MigrationResult:
    """Run the existing online Alembic chain, then verify the resulting schema."""

    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        from app.config import get_settings

        get_settings.cache_clear()
        configuration = Config(str(BACKEND_ROOT / "alembic.ini"))
        configuration.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        assert_safe_existing_state(database_url)
        command.upgrade(configuration, "head")

        # Import only after DATABASE_URL is set because the database module owns
        # a process-level engine for the configured runtime database.
        from app.database.verify_schema import verify_schema

        verification = verify_schema(database_url)
        return MigrationResult(
            current_revision=verification.current_revision,
            head_revisions=verification.head_revisions,
            errors=verification.errors,
        )
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        try:
            from app.config import get_settings

            get_settings.cache_clear()
        except ImportError:
            pass


def main(
    *,
    secret_prompt: Callable[[str], str] = getpass,
    input_prompt: Callable[[str], str] = input,
    migration_runner: Callable[[str], MigrationResult] = apply_migrations,
) -> int:
    print("RailOps AI Neon migration")
    print("The connection string will not be echoed, saved, or printed.")
    try:
        supplied_url = secret_prompt("Neon DIRECT database connection string: ")
    except (EOFError, KeyboardInterrupt):
        print("\nMigration cancelled. No database changes were requested.")
        return 1

    try:
        target = validate_neon_direct_url(supplied_url)
    except NeonTargetError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    finally:
        supplied_url = ""

    print("Validated target: Neon PostgreSQL direct endpoint")
    print(f"Host: {target.host}")
    print(f"Database: {target.database}")
    try:
        confirmation = input_prompt(
            "Type MIGRATE to apply the existing Alembic migrations to this database: "
        )
    except (EOFError, KeyboardInterrupt):
        print("\nMigration cancelled. No database changes were requested.")
        return 1
    if confirmation != "MIGRATE":
        print("Migration cancelled. No database changes were requested.")
        return 1

    print("Applying existing Alembic migrations through head.")
    try:
        result = migration_runner(target.database_url)
    except MigrationSafetyError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 3
    except Exception as error:  # Keep driver messages from exposing credentials.
        print(
            f"ERROR: Migration or verification failed ({type(error).__name__}). "
            "No database reset, downgrade, or cleanup was attempted. Review the "
            "Neon and Alembic logs, then correct the cause and run this command again.",
            file=sys.stderr,
        )
        return 3

    if not result.compatible:
        print("ERROR: Schema verification failed after migration.", file=sys.stderr)
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            "No database reset, downgrade, or cleanup was attempted.",
            file=sys.stderr,
        )
        return 4

    expected_heads = ", ".join(result.head_revisions)
    print(f"Current Alembic revision: {result.current_revision or 'none'}")
    print(f"Expected Alembic head: {expected_heads}")
    print("Neon schema migration and verification completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
