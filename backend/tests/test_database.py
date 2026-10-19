from sqlalchemy import select, text

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

