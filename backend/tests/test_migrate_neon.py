from scripts import migrate_neon
from sqlalchemy import create_engine, text
import pytest


DIRECT_URL = (
    "postgresql://railops:super-secret@"
    "ep-example.us-east-2.aws.neon.tech/railops?sslmode=require&channel_binding=require"
)


def test_direct_neon_url_is_normalized_without_losing_options() -> None:
    target = migrate_neon.validate_neon_direct_url(DIRECT_URL)

    assert target.host == "ep-example.us-east-2.aws.neon.tech"
    assert target.database == "railops"
    assert target.database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in target.database_url
    assert "channel_binding=require" in target.database_url


def test_pooled_or_non_neon_targets_are_rejected() -> None:
    invalid_urls = (
        DIRECT_URL.replace("ep-example.", "ep-example-pooler."),
        DIRECT_URL.replace("neon.tech", "example.com"),
        DIRECT_URL.replace("postgresql://", "sqlite:///"),
        DIRECT_URL.replace("?sslmode=require&channel_binding=require", ""),
    )

    for invalid_url in invalid_urls:
        try:
            migrate_neon.validate_neon_direct_url(invalid_url)
        except migrate_neon.NeonTargetError:
            continue
        raise AssertionError(f"Expected URL to be rejected: {invalid_url!r}")


def test_cancelled_migration_never_calls_runner_or_prints_password(capsys) -> None:
    called = False

    def migration_runner(_database_url: str) -> migrate_neon.MigrationResult:
        nonlocal called
        called = True
        raise AssertionError("Migration runner must not be called")

    exit_code = migrate_neon.main(
        secret_prompt=lambda _prompt: DIRECT_URL,
        input_prompt=lambda _prompt: "cancel",
        migration_runner=migration_runner,
    )

    output = capsys.readouterr()
    assert exit_code == 1
    assert called is False
    assert "super-secret" not in output.out
    assert "super-secret" not in output.err


def test_confirmed_migration_verifies_head_without_printing_password(capsys) -> None:
    received_url = ""

    def migration_runner(database_url: str) -> migrate_neon.MigrationResult:
        nonlocal received_url
        received_url = database_url
        return migrate_neon.MigrationResult(
            current_revision="20261020_0006",
            head_revisions=("20261020_0006",),
            errors=(),
        )

    exit_code = migrate_neon.main(
        secret_prompt=lambda _prompt: DIRECT_URL,
        input_prompt=lambda _prompt: "MIGRATE",
        migration_runner=migration_runner,
    )

    output = capsys.readouterr()
    assert exit_code == 0
    assert received_url.startswith("postgresql+psycopg://")
    assert "Host: ep-example.us-east-2.aws.neon.tech" in output.out
    assert "Database: railops" in output.out
    assert "super-secret" not in output.out
    assert "super-secret" not in output.err


def test_migration_error_is_sanitized(capsys) -> None:
    def migration_runner(_database_url: str) -> migrate_neon.MigrationResult:
        raise RuntimeError("super-secret")

    exit_code = migrate_neon.main(
        secret_prompt=lambda _prompt: DIRECT_URL,
        input_prompt=lambda _prompt: "MIGRATE",
        migration_runner=migration_runner,
    )

    output = capsys.readouterr()
    assert exit_code == 3
    assert "RuntimeError" in output.err
    assert "super-secret" not in output.out
    assert "super-secret" not in output.err


def test_preflight_refuses_legacy_topology_rebuild(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('20261020_0003')")
        )
        connection.execute(text("CREATE TABLE track_nodes (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE track_edges (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO track_nodes (id) VALUES (1)"))
    engine.dispose()

    with pytest.raises(migrate_neon.MigrationSafetyError, match="Legacy topology"):
        migrate_neon.assert_safe_existing_state(database_url)
