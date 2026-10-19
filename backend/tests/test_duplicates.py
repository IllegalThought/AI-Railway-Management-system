import pytest

from app.schemas.railway import TrainCreate
from app.services.exceptions import DuplicateRecordError
from app.services.records import create_simulation_session, create_train


def test_duplicate_train_identifier_returns_domain_error_and_rolls_back(database) -> None:
    demo = create_simulation_session(database, name="Duplicate test")
    payload = TrainCreate(
        identifier="RA-404",
        priority=1,
        arrival_minute=400,
        departure_minute=415,
        minimum_dwell_minutes=10,
        length_meters=200,
    )
    create_train(database, session_id=demo.id, data=payload)

    with pytest.raises(DuplicateRecordError, match="already exists"):
        create_train(database, session_id=demo.id, data=payload)

    assert database.is_active


def test_same_train_identifier_is_allowed_in_another_session(database) -> None:
    first = create_simulation_session(database, name="First")
    second = create_simulation_session(database, name="Second")
    payload = TrainCreate(
        identifier="RA-505",
        priority=3,
        arrival_minute=500,
        departure_minute=515,
        minimum_dwell_minutes=10,
        length_meters=220,
    )

    first_train = create_train(database, session_id=first.id, data=payload)
    second_train = create_train(database, session_id=second.id, data=payload)

    assert first_train.session_id != second_train.session_id

