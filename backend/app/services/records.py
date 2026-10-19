from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Platform, SimulationSession, Train, TrainPlatformCompatibility
from app.schemas.railway import PlatformCreate, TrainCreate
from app.services.exceptions import DuplicateRecordError, RecordNotFoundError


def create_simulation_session(
    database: Session, *, name: str, session_key: str | None = None
) -> SimulationSession:
    simulation_session = SimulationSession(name=name, session_key=session_key)
    database.add(simulation_session)
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise DuplicateRecordError("A simulation session with this key already exists.") from exc
    database.refresh(simulation_session)
    return simulation_session


def create_platform(
    database: Session, *, session_id: int, data: PlatformCreate
) -> Platform:
    platform = Platform(session_id=session_id, **data.model_dump())
    database.add(platform)
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise DuplicateRecordError(
            "A platform with this code already exists in the simulation session."
        ) from exc
    database.refresh(platform)
    return platform


def create_train(database: Session, *, session_id: int, data: TrainCreate) -> Train:
    values = data.model_dump(exclude={"compatible_platform_codes"})
    train = Train(session_id=session_id, **values)
    if data.compatible_platform_codes:
        platforms = database.scalars(
            select(Platform).where(
                Platform.session_id == session_id,
                Platform.code.in_(data.compatible_platform_codes),
            )
        ).all()
        found_codes = {platform.code for platform in platforms}
        missing_codes = set(data.compatible_platform_codes) - found_codes
        if missing_codes:
            missing = ", ".join(sorted(missing_codes))
            raise RecordNotFoundError(f"Compatible platforms were not found: {missing}.")
        train.compatible_platforms = [
            TrainPlatformCompatibility(platform=platform) for platform in platforms
        ]
    database.add(train)
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise DuplicateRecordError(
            "A train with this identifier already exists in the simulation session."
        ) from exc
    database.refresh(train)
    return train

