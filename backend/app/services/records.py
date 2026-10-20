from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    OperationalEvent,
    Platform,
    SchedulingPlan,
    SimulationSession,
    Train,
    TrainAssignment,
    TrainPlatformCompatibility,
)
from app.models.enums import EventType, PlanStatus
from app.schemas.railway import PlatformCreate, PlatformUpdate, TrainCreate, TrainUpdate
from app.services.exceptions import DuplicateRecordError, RecordNotFoundError


def create_simulation_session(database: Session, *, name: str, session_key: str | None = None) -> SimulationSession:
    simulation_session = SimulationSession(name=name, session_key=session_key)
    database.add(simulation_session)
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise DuplicateRecordError("A simulation session with this key already exists.") from exc
    database.refresh(simulation_session)
    return simulation_session


def create_platform(database: Session, *, session_id: int, data: PlatformCreate) -> Platform:
    platform = Platform(session_id=session_id, **data.model_dump())
    database.add(platform)
    _commit_duplicate_safe(database, "A platform with this code already exists in the simulation session.")
    database.refresh(platform)
    return platform


def list_platforms(database: Session, *, session_id: int) -> list[Platform]:
    return list(database.scalars(select(Platform).where(Platform.session_id == session_id).options(selectinload(Platform.compatible_trains)).order_by(Platform.code)).all())


def get_platform(database: Session, *, session_id: int, platform_id: int) -> Platform:
    platform = database.scalar(select(Platform).where(Platform.session_id == session_id, Platform.id == platform_id).options(selectinload(Platform.compatible_trains)))
    if platform is None:
        raise RecordNotFoundError("Platform was not found in this demo workspace.")
    return platform


def update_platform(database: Session, *, simulation_session: SimulationSession, platform_id: int, data: PlatformUpdate) -> tuple[Platform, bool]:
    platform = get_platform(database, session_id=simulation_session.id, platform_id=platform_id)
    values = {
        "code": platform.code,
        "platform_type": platform.platform_type,
        "length_meters": platform.length_meters,
        "clearance_minutes": platform.clearance_minutes,
        "is_available": platform.is_available,
        "unavailable_reason": platform.unavailable_reason,
    }
    values.update(data.model_dump(exclude_unset=True))
    validated = PlatformCreate.model_validate(values)
    for field, value in validated.model_dump().items():
        setattr(platform, field, value)
    validation_required = _invalidate_ready_plans_for_platform(database, simulation_session.id, platform.id)
    database.add(OperationalEvent(session_id=simulation_session.id, event_type=EventType.PLATFORM_UPDATED, event_minute=0, message=f"Platform {platform.code} was updated.", resource_code=platform.code))
    _commit_duplicate_safe(database, "A platform with this code already exists in the simulation session.")
    return get_platform(database, session_id=simulation_session.id, platform_id=platform.id), validation_required


def create_train(database: Session, *, session_id: int, data: TrainCreate) -> Train:
    train = Train(session_id=session_id, **data.model_dump(exclude={"compatible_platform_codes"}))
    train.compatible_platforms = _compatibility_records(database, session_id, data.compatible_platform_codes)
    database.add(train)
    _commit_duplicate_safe(database, "A train with this identifier already exists in the simulation session.")
    return get_train(database, session_id=session_id, train_id=train.id)


def list_trains(database: Session, *, session_id: int) -> list[Train]:
    return list(database.scalars(select(Train).where(Train.session_id == session_id).options(selectinload(Train.compatible_platforms).selectinload(TrainPlatformCompatibility.platform)).order_by(Train.arrival_minute, Train.identifier)).all())


def get_train(database: Session, *, session_id: int, train_id: int) -> Train:
    train = database.scalar(select(Train).where(Train.session_id == session_id, Train.id == train_id).options(selectinload(Train.compatible_platforms).selectinload(TrainPlatformCompatibility.platform)))
    if train is None:
        raise RecordNotFoundError("Train was not found in this demo workspace.")
    return train


def update_train(database: Session, *, simulation_session: SimulationSession, train_id: int, data: TrainUpdate) -> tuple[Train, bool]:
    train = get_train(database, session_id=simulation_session.id, train_id=train_id)
    current_codes = [item.platform.code for item in train.compatible_platforms]
    values = {
        "identifier": train.identifier,
        "priority": train.priority,
        "arrival_minute": train.arrival_minute,
        "departure_minute": train.departure_minute,
        "minimum_dwell_minutes": train.minimum_dwell_minutes,
        "length_meters": train.length_meters,
        "required_platform_type": train.required_platform_type,
        "compatible_platform_codes": current_codes,
        "service_status": train.service_status,
        "delay_minutes": train.delay_minutes,
    }
    values.update(data.model_dump(exclude_unset=True))
    validated = TrainCreate.model_validate(values)
    for field, value in validated.model_dump(exclude={"compatible_platform_codes"}).items():
        setattr(train, field, value)
    if "compatible_platform_codes" in data.model_fields_set:
        train.compatible_platforms.clear()
        database.flush()
        train.compatible_platforms = _compatibility_records(database, simulation_session.id, validated.compatible_platform_codes)
    validation_required = _invalidate_ready_plans_for_train(database, simulation_session.id, train.id)
    database.add(OperationalEvent(session_id=simulation_session.id, event_type=EventType.TRAIN_UPDATED, event_minute=train.arrival_minute, message=f"Train {train.identifier} was updated.", resource_code=train.identifier))
    _commit_duplicate_safe(database, "A train with this identifier already exists in the simulation session.")
    return get_train(database, session_id=simulation_session.id, train_id=train.id), validation_required


def delete_train(database: Session, *, simulation_session: SimulationSession, train_id: int) -> bool:
    train = get_train(database, session_id=simulation_session.id, train_id=train_id)
    validation_required = _invalidate_ready_plans_for_train(database, simulation_session.id, train.id)
    database.execute(delete(TrainAssignment).where(TrainAssignment.train_id == train.id))
    database.add(OperationalEvent(session_id=simulation_session.id, event_type=EventType.TRAIN_DELETED, event_minute=train.arrival_minute, message=f"Train {train.identifier} was deleted.", resource_code=train.identifier))
    database.delete(train)
    database.commit()
    return validation_required


def _compatibility_records(database: Session, session_id: int, platform_codes: list[str]) -> list[TrainPlatformCompatibility]:
    if not platform_codes:
        return []
    platforms = database.scalars(select(Platform).where(Platform.session_id == session_id, Platform.code.in_(platform_codes))).all()
    found_codes = {platform.code for platform in platforms}
    missing_codes = set(platform_codes) - found_codes
    if missing_codes:
        missing = ", ".join(sorted(missing_codes))
        raise RecordNotFoundError(f"Compatible platforms were not found: {missing}.")
    return [TrainPlatformCompatibility(platform=platform) for platform in platforms]


def _invalidate_ready_plans_for_train(database: Session, session_id: int, train_id: int) -> bool:
    plans = database.scalars(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status.in_([PlanStatus.READY, PlanStatus.APPLIED]))).all()
    for plan in plans:
        plan.status = PlanStatus.INVALID if plan.status == PlanStatus.APPLIED else PlanStatus.DRAFT
        plan.is_validated = False
    return bool(plans)


def _invalidate_ready_plans_for_platform(database: Session, session_id: int, platform_id: int) -> bool:
    plans = database.scalars(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status.in_([PlanStatus.READY, PlanStatus.APPLIED]))).all()
    for plan in plans:
        plan.status = PlanStatus.INVALID if plan.status == PlanStatus.APPLIED else PlanStatus.DRAFT
        plan.is_validated = False
    return bool(plans)


def invalidate_active_plans(database: Session, session_id: int) -> bool:
    plans = database.scalars(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status.in_([PlanStatus.READY, PlanStatus.APPLIED]))).all()
    for plan in plans:
        plan.status = PlanStatus.INVALID if plan.status == PlanStatus.APPLIED else PlanStatus.DRAFT
        plan.is_validated = False
    if plans:
        database.commit()
    return bool(plans)


def _commit_duplicate_safe(database: Session, message: str) -> None:
    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise DuplicateRecordError(message) from exc
