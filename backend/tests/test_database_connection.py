from pathlib import Path

from sqlalchemy.exc import OperationalError

from app.database import check_connection


def test_connection_check_uses_read_only_probe_for_local_sqlite(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'connectivity.db'}"

    result = check_connection.check_database_connection(database_url)

    assert result.connected is True
    assert result.database_backend == "sqlite"


def test_failed_connection_check_does_not_print_credentials(
    monkeypatch, capsys
) -> None:
    secret_url = "postgresql+psycopg://railops:highly-secret@database.example/railops"

    class FailedConnection:
        def __enter__(self):
            raise OperationalError("SELECT 1", {}, Exception("highly-secret"))

        def __exit__(self, *_args):
            return False

    class FailedEngine:
        def connect(self):
            return FailedConnection()

        def dispose(self):
            return None

    monkeypatch.setattr(check_connection, "_build_engine", lambda *_args, **_kwargs: FailedEngine())
    monkeypatch.setattr(
        check_connection,
        "get_settings",
        lambda: type(
            "SettingsStub",
            (),
            {
                "database_url": secret_url,
                "database_pool_size": 1,
                "database_max_overflow": 0,
                "database_pool_timeout_seconds": 1,
                "database_pool_recycle_seconds": 30,
            },
        )(),
    )

    assert check_connection.main() == 1
    output = capsys.readouterr()
    assert "Database connection failed (postgresql)." in output.err
    assert "highly-secret" not in output.err
    assert secret_url not in output.err


def test_malformed_connection_url_does_not_print_credentials(
    monkeypatch, capsys
) -> None:
    malformed_url = "postgresql://railops:another-secret@[invalid"
    monkeypatch.setattr(
        check_connection,
        "get_settings",
        lambda: type(
            "SettingsStub",
            (),
            {
                "database_url": malformed_url,
                "database_pool_size": 1,
                "database_max_overflow": 0,
                "database_pool_timeout_seconds": 1,
                "database_pool_recycle_seconds": 30,
            },
        )(),
    )

    assert check_connection.main() == 1
    output = capsys.readouterr()
    assert "Database connection failed (postgresql)." in output.err
    assert "another-secret" not in output.err
    assert malformed_url not in output.err
