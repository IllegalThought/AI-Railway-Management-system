"""Incident mutation, impact analysis, and constraint-based dynamic replanning."""

from __future__ import annotations

from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.scheduling import Candidate, SolverStatus, build_domains, solve_csp
from app.models import (
    Incident,
    OperationalEvent,
    Platform,
    SchedulingPlan,
    SimulationSession,
    SimulationState,
    TrackEdge,
    TrackNode,
    Train,
    TrainAssignment,
    TrainPlatformCompatibility,
)
from app.models.enums import EventType, IncidentStatus, IncidentType, PlanStatus, TrainStatus
from app.schemas.simulation import IncidentCreate
from app.services import schedules
from app.services.exceptions import DuplicateRecordError, InvalidOperationError, RecordNotFoundError


def list_incidents(database: Session, session_id: int) -> list[Incident]:
    return list(database.scalars(select(Incident).where(Incident.session_id == session_id).order_by(Incident.created_at.desc(), Incident.id.desc())).all())


def _base_plan(database: Session, session_id: int) -> SchedulingPlan | None:
    return database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status == PlanStatus.APPLIED).order_by(SchedulingPlan.version.desc()).options(selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.route)))


def affected_train_ids(database: Session, incident: Incident, plan: SchedulingPlan | None = None) -> list[int]:
    plan = plan or _base_plan(database, incident.session_id)
    if plan is None:
        return []
    if incident.incident_type in {IncidentType.ARRIVAL_DELAY, IncidentType.DEPARTURE_DELAY, IncidentType.NEW_TRAIN_REQUEST}:
        return list(database.scalars(select(Train.id).where(Train.session_id == incident.session_id, Train.identifier == incident.resource_code)).all())
    result: list[int] = []
    for assignment in plan.assignments:
        if incident.incident_type == IncidentType.PLATFORM_CLOSURE and assignment.platform.code == incident.resource_code:
            result.append(assignment.train_id)
        elif assignment.route and any(item.resource_code == incident.resource_code or item.edge_code == incident.resource_code for item in assignment.route.reservations):
            result.append(assignment.train_id)
    return sorted(set(result))


def _assert_not_committed(plan: SchedulingPlan | None, train_id: int, current_minute: int) -> None:
    if plan is None:
        return
    assignment = next((item for item in plan.assignments if item.train_id == train_id), None)
    if assignment and assignment.route:
        first = min((item.start_minute for item in assignment.route.reservations), default=assignment.occupancy_start_minute)
        if first <= current_minute:
            raise InvalidOperationError("The affected train has begun a committed movement and its timing can no longer be changed.")


def create_incident(database: Session, simulation_session: SimulationSession, data: IncidentCreate) -> Incident:
    state = database.scalar(select(SimulationState).where(SimulationState.session_id == simulation_session.id))
    current = state.current_minute if state else 0
    plan = _base_plan(database, simulation_session.id)
    resource = data.affected_resource.strip()
    title = data.incident_type.value.replace("_", " ").title()

    if data.incident_type in {IncidentType.ARRIVAL_DELAY, IncidentType.DEPARTURE_DELAY}:
        train = database.scalar(select(Train).where(Train.session_id == simulation_session.id, Train.identifier == resource))
        if train is None:
            raise RecordNotFoundError("The affected train was not found in this demo workspace.")
        _assert_not_committed(plan, train.id, current)
        if data.incident_type == IncidentType.ARRIVAL_DELAY:
            train.delay_minutes += data.duration_minutes
            train.service_status = TrainStatus.DELAYED
        else:
            train.departure_minute += data.duration_minutes
        title = f"{train.identifier} {data.incident_type.value.replace('train_', '').replace('_', ' ')}"
    elif data.incident_type == IncidentType.PLATFORM_CLOSURE:
        platform = database.scalar(select(Platform).where(Platform.session_id == simulation_session.id, Platform.code == resource))
        if platform is None:
            raise RecordNotFoundError("The affected platform was not found in this demo workspace.")
        platform.is_available = False
        platform.unavailable_reason = data.description
        title = f"Platform {resource} closure"
    elif data.incident_type == IncidentType.TRACK_BLOCKAGE:
        edge = database.scalar(select(TrackEdge).where(TrackEdge.session_id == simulation_session.id, (TrackEdge.code == resource) | (TrackEdge.resource_group == resource)))
        if edge is None:
            raise RecordNotFoundError("The affected track resource was not found in this demo workspace.")
        title = f"Track {resource} blockage"
    elif data.incident_type == IncidentType.JUNCTION_CLOSURE:
        node = database.scalar(select(TrackNode).where(TrackNode.session_id == simulation_session.id, TrackNode.code == resource, TrackNode.node_type.in_(["junction", "switch"])))
        if node is None:
            raise RecordNotFoundError("The affected junction or switch was not found in this demo workspace.")
        title = f"Junction {resource} closure"
    else:
        assert data.new_train is not None
        if database.scalar(select(Train.id).where(Train.session_id == simulation_session.id, Train.identifier == data.new_train.identifier)):
            raise DuplicateRecordError("A train with this identifier already exists in the simulation session.")
        train = Train(session_id=simulation_session.id, **data.new_train.model_dump(exclude={"compatible_platform_codes"}))
        platforms = list(database.scalars(select(Platform).where(Platform.session_id == simulation_session.id, Platform.code.in_(data.new_train.compatible_platform_codes))).all())
        if {item.code for item in platforms} != set(data.new_train.compatible_platform_codes):
            raise RecordNotFoundError("One or more compatible platforms were not found.")
        train.compatible_platforms = [TrainPlatformCompatibility(platform=item) for item in platforms]
        database.add(train)
        database.flush()
        resource = train.identifier
        title = f"New train request {resource}"

    incident = Incident(session_id=simulation_session.id, title=title, description=data.description, severity=data.severity, status=IncidentStatus.OPEN, reported_minute=current, resource_code=resource, incident_type=data.incident_type, start_minute=data.start_minute, duration_minutes=data.duration_minutes)
    database.add(incident)
    database.add(OperationalEvent(session_id=simulation_session.id, event_type=EventType.INCIDENT_REPORTED, event_minute=current, message=f"{title} was reported.", resource_code=resource))
    database.commit()
    database.refresh(incident)
    return incident


def update_status(database: Session, session_id: int, incident_id: int, status: IncidentStatus) -> Incident:
    incident = database.scalar(select(Incident).where(Incident.session_id == session_id, Incident.id == incident_id))
    if incident is None:
        raise RecordNotFoundError("Incident was not found in this demo workspace.")
    incident.status = status
    if status == IncidentStatus.RESOLVED and incident.incident_type == IncidentType.PLATFORM_CLOSURE:
        platform = database.scalar(select(Platform).where(Platform.session_id == session_id, Platform.code == incident.resource_code))
        if platform:
            platform.is_available = True
            platform.unavailable_reason = None
    database.commit()
    database.refresh(incident)
    return incident


def replan(database: Session, simulation_session: SimulationSession, incident: Incident, base_plan_id: int, base_version: int, expected_revision: int) -> tuple[SchedulingPlan, SchedulingPlan, list[int], list[int], list]:
    state = database.scalar(select(SimulationState).where(SimulationState.session_id == simulation_session.id))
    current = state.current_minute if state else 0
    revision = state.revision if state else 0
    if revision != expected_revision:
        raise InvalidOperationError("The simulation state changed. Refresh before replanning.")
    base = schedules.get_plan(database, simulation_session.id, base_plan_id)
    if base.version != base_version or schedules.is_stale(database, base):
        raise InvalidOperationError("The base plan is stale. Replan from the latest schedule version.")
    if state and state.active_plan_id != base.id:
        raise InvalidOperationError("The selected base plan is not the simulation's active plan.")

    trains, platforms = schedules.load_resources(database, simulation_session.id)
    train_problems, platform_problems = schedules._problems(trains, platforms)
    start = base.horizon_start_minute
    end = max(base.horizon_end_minute, max((item.departure_minute + 60 for item in trains), default=base.horizon_end_minute))
    domains = build_domains(train_problems, platform_problems, horizon_start=start, horizon_end=end, maximum_delay=max(base.maximum_delay_minutes, 60))
    preserved: list[int] = []
    for assignment in base.assignments:
        first = min((item.start_minute for item in assignment.route.reservations), default=assignment.occupancy_start_minute) if assignment.route else assignment.occupancy_start_minute
        if assignment.occupancy_end_minute <= current or first <= current:
            domains[assignment.train_id] = [Candidate(assignment.platform_id, assignment.occupancy_start_minute, assignment.occupancy_end_minute, assignment.delay_minutes)]
            preserved.append(assignment.train_id)
    started = perf_counter()
    result = solve_csp(train_problems, platform_problems, domains, {item.train_id: item.platform_id for item in base.assignments}, node_limit=500_000)
    execution_time_ms = (perf_counter() - started) * 1000
    version = (database.scalar(select(func.max(SchedulingPlan.version)).where(SchedulingPlan.session_id == simulation_session.id)) or 0) + 1
    plan = SchedulingPlan(session_id=simulation_session.id, name=f"Incident replan v{version}", version=version, status=PlanStatus.DRAFT, engine="csp", solver_status=result.status.value, objective_value=result.objective, maximum_delay_minutes=max(base.maximum_delay_minutes, 60), is_validated=False, route_validated=False, explanation=result.explanation, execution_time_ms=execution_time_ms, horizon_start_minute=start, horizon_end_minute=end)
    database.add(plan)
    database.flush()
    previous = {item.train_id: item for item in base.assignments}
    for train in trains:
        candidate = result.assignments.get(train.id)
        if candidate:
            old = previous.get(train.id)
            database.add(TrainAssignment(plan_id=plan.id, train_id=train.id, platform_id=candidate.platform_id, occupancy_start_minute=candidate.start, occupancy_end_minute=candidate.end, delay_minutes=candidate.delay, reassigned=bool(old and old.platform_id != candidate.platform_id)))
    database.add(OperationalEvent(session_id=simulation_session.id, event_type=EventType.REPLAN_CREATED, event_minute=current, message=f"{plan.name} was generated for incident {incident.id} ({result.status.value}).", resource_code=str(incident.id)))
    database.commit()
    if result.status in {SolverStatus.FEASIBLE, SolverStatus.OPTIMAL}:
        locked_routes = {item.train_id: item.route for item in base.assignments if item.train_id in preserved and item.route is not None}
        plan, issues = schedules.validate_plan(database, simulation_session, plan.id, plan.version, locked_routes=locked_routes)
    else:
        plan = schedules.get_plan(database, simulation_session.id, plan.id)
        issues = []
    if not (plan.is_validated and plan.route_validated):
        plan.status = PlanStatus.ARCHIVED
        database.commit()
        plan = schedules.get_plan(database, simulation_session.id, plan.id)
    return base, plan, preserved, affected_train_ids(database, incident, base), issues
