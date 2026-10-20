import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from app.config import Settings
from app.schemas.analytics import BenchmarkRequest
from app.schemas.railway import SchedulingInput, TrainCreate
from app.schemas.schedules import GenerateScheduleRequest


POSTGRESQL_URL = "postgresql://railops:placeholder@database.example/railops?sslmode=require"


def test_train_requires_dwell_time_inside_occupancy_window() -> None:
    with pytest.raises(ValidationError, match="minimum dwell time"):
        TrainCreate(
            identifier="RA-202",
            priority=2,
            arrival_minute=100,
            departure_minute=105,
            minimum_dwell_minutes=10,
            length_meters=180,
        )


def test_scheduling_intervals_are_half_open_and_non_empty() -> None:
    with pytest.raises(ValidationError, match="half-open interval"):
        SchedulingInput(
            plan_name="Morning plan",
            horizon_start_minute=60,
            horizon_end_minute=60,
        )


def test_assignment_must_be_contained_in_horizon() -> None:
    with pytest.raises(ValidationError, match="contained within"):
        SchedulingInput(
            plan_name="Morning plan",
            horizon_start_minute=60,
            horizon_end_minute=180,
            assignments=[
                {
                    "train_identifier": "RA-202",
                    "platform_code": "P1",
                    "occupancy_start_minute": 50,
                    "occupancy_end_minute": 80,
                }
            ],
        )


def test_duplicate_train_assignment_is_rejected_case_insensitively() -> None:
    with pytest.raises(ValidationError, match="duplicate values"):
        SchedulingInput(
            plan_name="Morning plan",
            horizon_start_minute=0,
            horizon_end_minute=180,
            assignments=[
                {
                    "train_identifier": "RA-202",
                    "platform_code": "P1",
                    "occupancy_start_minute": 50,
                    "occupancy_end_minute": 80,
                },
                {
                    "train_identifier": "ra-202",
                    "platform_code": "P2",
                    "occupancy_start_minute": 90,
                    "occupancy_end_minute": 110,
                },
            ],
        )


def test_production_rejects_unrestricted_cors() -> None:
    settings = Settings(
        APP_ENV="production",
        DATABASE_URL=POSTGRESQL_URL,
        BACKEND_CORS_ORIGINS="*",
    )
    with pytest.raises(ValueError, match="Unrestricted CORS"):
        _ = settings.cors_origins


def test_production_requires_postgresql_and_exact_https_cors() -> None:
    with pytest.raises(ValidationError, match="Production requires a PostgreSQL"):
        Settings(APP_ENV="production", DATABASE_URL="sqlite:///./production.db")

    insecure = Settings(
        APP_ENV="production",
        DATABASE_URL=POSTGRESQL_URL,
        BACKEND_CORS_ORIGINS="http://railops.example",
    )
    with pytest.raises(ValueError, match="must use HTTPS"):
        _ = insecure.cors_origins

    with_path = Settings(
        APP_ENV="production",
        DATABASE_URL=POSTGRESQL_URL,
        BACKEND_CORS_ORIGINS="https://railops.example/app",
    )
    with pytest.raises(ValueError, match="exact HTTP"):
        _ = with_path.cors_origins

    valid = Settings(
        APP_ENV="production",
        DATABASE_URL=POSTGRESQL_URL,
        BACKEND_CORS_ORIGINS="https://railops.example/, https://www.railops.example",
    )
    assert valid.cors_origins == [
        "https://railops.example",
        "https://www.railops.example",
    ]


def test_postgresql_url_uses_declared_psycopg_driver() -> None:
    settings = Settings(DATABASE_URL="postgres://user:secret@database.example/railops")

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_production_postgresql_requires_tls() -> None:
    with pytest.raises(ValueError, match="require sslmode"):
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql://railops:placeholder@database.example/railops",
            BACKEND_CORS_ORIGINS="https://railops.example",
        )


def test_neon_connection_options_survive_driver_normalization() -> None:
    settings = Settings(
        DATABASE_URL=(
            "postgresql://railops:placeholder@ep-example.neon.tech/railops"
            "?sslmode=require&channel_binding=require"
        )
    )

    url = make_url(settings.database_url)
    assert url.drivername == "postgresql+psycopg"
    assert url.query["sslmode"] == "require"
    assert url.query["channel_binding"] == "require"


def test_relative_sqlite_url_is_anchored_to_backend_directory() -> None:
    settings = Settings(DATABASE_URL="sqlite:///./railops.db")

    assert settings.database_url.endswith("/backend/railops.db")


@pytest.mark.parametrize("request_type", [GenerateScheduleRequest, BenchmarkRequest])
def test_public_solver_requests_have_bounded_resources(request_type) -> None:
    with pytest.raises(ValidationError):
        request_type(search_limit=500_001)
    with pytest.raises(ValidationError):
        request_type(time_limit_seconds=15.1)

