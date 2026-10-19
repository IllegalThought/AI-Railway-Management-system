import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas.railway import SchedulingInput, TrainCreate


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
    settings = Settings(APP_ENV="production", BACKEND_CORS_ORIGINS="*")
    with pytest.raises(ValueError, match="Unrestricted CORS"):
        _ = settings.cors_origins


def test_postgresql_url_uses_declared_psycopg_driver() -> None:
    settings = Settings(DATABASE_URL="postgres://user:secret@database.example/railops")

    assert settings.database_url.startswith("postgresql+psycopg://")

