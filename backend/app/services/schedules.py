from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.ai.scheduling import (
    Candidate,
    PlatformProblem,
    SolverStatus,
    TrainProblem,
    build_domains,
    solve_cp_sat,
    solve_csp,
    solve_fcfs,
)
from app.ai.validation import ValidationIssue, validate_assignments
from app.models import OperationalEvent, Platform, SchedulingPlan, SimulationSession, Train, TrainAssignment, TrainPlatformCompatibility
from app.models.enums import EventType, PlanStatus, TrainStatus
from app.schemas.schedules import GenerateScheduleRequest, SchedulingEngine
from app.services.exceptions import InvalidOperationError, RecordNotFoundError
from app.services.network import validate_route_reservations


def load_resources(database: Session, session_id: int) -> tuple[list[Train], list[Platform]]:
    trains = list(database.scalars(select(Train).where(Train.session_id == session_id, Train.service_status != TrainStatus.CANCELLED).options(selectinload(Train.compatible_platforms))).all())
    platforms = list(database.scalars(select(Platform).where(Platform.session_id == session_id).order_by(Platform.code)).all())
    return trains, platforms


def _problems(trains: list[Train], platforms: list[Platform]) -> tuple[list[TrainProblem], list[PlatformProblem]]:
    train_problems = [TrainProblem(item.id, item.identifier, item.priority, item.arrival_minute, item.departure_minute, item.minimum_dwell_minutes, item.length_meters, item.required_platform_type, item.delay_minutes, frozenset(link.platform_id for link in item.compatible_platforms)) for item in trains]
    platform_problems = [PlatformProblem(item.id, item.code, item.platform_type, item.length_meters, item.clearance_minutes, item.is_available) for item in platforms]
    return train_problems, platform_problems


def _preferred_platforms(database: Session, session_id: int) -> dict[int, int]:
    applied = database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.status == PlanStatus.APPLIED).order_by(SchedulingPlan.version.desc()).options(selectinload(SchedulingPlan.assignments)))
    return {item.train_id: item.platform_id for item in applied.assignments} if applied else {}


def generate_schedule(database: Session, simulation_session: SimulationSession, request: GenerateScheduleRequest) -> SchedulingPlan:
    trains, platforms = load_resources(database, simulation_session.id)
    if not trains:
        raise InvalidOperationError("No active trains are available for scheduling.")
    start = request.horizon_start_minute if request.horizon_start_minute is not None else min(item.arrival_minute for item in trains)
    end = request.horizon_end_minute if request.horizon_end_minute is not None else max(item.departure_minute + request.maximum_delay_minutes for item in trains) + max((item.clearance_minutes for item in platforms), default=0)
    train_problems, platform_problems = _problems(trains, platforms)
    domains = build_domains(train_problems, platform_problems, horizon_start=start, horizon_end=end, maximum_delay=request.maximum_delay_minutes)
    preferred = _preferred_platforms(database, simulation_session.id)
    if request.engine == SchedulingEngine.FCFS:
        result = solve_fcfs(train_problems, platform_problems, domains, preferred)
    elif request.engine == SchedulingEngine.CSP:
        result = solve_csp(train_problems, platform_problems, domains, preferred, node_limit=request.search_limit)
    else:
        result = solve_cp_sat(train_problems, platform_problems, domains, preferred, time_limit_seconds=request.time_limit_seconds)
    version = (database.scalar(select(func.max(SchedulingPlan.version)).where(SchedulingPlan.session_id == simulation_session.id)) or 0) + 1
    plan = SchedulingPlan(session_id=simulation_session.id, name=f"Dispatch plan v{version}", version=version, status=PlanStatus.DRAFT, engine=request.engine.value, solver_status=result.status.value, objective_value=result.objective, maximum_delay_minutes=request.maximum_delay_minutes, is_validated=False, route_validated=False, explanation=result.explanation, horizon_start_minute=start, horizon_end_minute=end)
    database.add(plan)
    database.flush()
    for train in trains:
        candidate = result.assignments.get(train.id)
        if candidate is None:
            continue
        database.add(TrainAssignment(plan_id=plan.id, train_id=train.id, platform_id=candidate.platform_id, occupancy_start_minute=candidate.start, occupancy_end_minute=candidate.end, delay_minutes=candidate.delay, reassigned=train.id in preferred and preferred[train.id] != candidate.platform_id))
    database.add(OperationalEvent(session_id=simulation_session.id, event_type=EventType.PLAN_CREATED, event_minute=start, message=f"{plan.name} was generated with {request.engine.value.upper()} ({result.status.value}).", resource_code=plan.name))
    database.commit()
    return get_plan(database, simulation_session.id, plan.id)


def get_plan(database: Session, session_id: int, plan_id: int) -> SchedulingPlan:
    plan = database.scalar(select(SchedulingPlan).where(SchedulingPlan.session_id == session_id, SchedulingPlan.id == plan_id).options(selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.train), selectinload(SchedulingPlan.assignments).selectinload(TrainAssignment.platform)))
    if plan is None:
        raise RecordNotFoundError("Scheduling plan was not found in this demo workspace.")
    return plan


def get_current_schedule(database: Session, session_id: int) -> SchedulingPlan | None:
    plan_id = database.scalar(select(SchedulingPlan.id).where(SchedulingPlan.session_id == session_id).order_by(SchedulingPlan.version.desc()).limit(1))
    return get_plan(database, session_id, plan_id) if plan_id is not None else None


def is_stale(database: Session, plan: SchedulingPlan) -> bool:
    latest = database.scalar(select(func.max(SchedulingPlan.version)).where(SchedulingPlan.session_id == plan.session_id)) or 0
    return plan.version != latest


def validate_plan(database: Session, simulation_session: SimulationSession, plan_id: int, version: int) -> tuple[SchedulingPlan, list[ValidationIssue]]:
    plan = get_plan(database, simulation_session.id, plan_id)
    if plan.version != version:
        raise InvalidOperationError("The supplied schedule version does not match the persisted plan.")
    trains, platforms = load_resources(database, simulation_session.id)
    train_problems, platform_problems = _problems(trains, platforms)
    assignments = {item.train_id: Candidate(item.platform_id, item.occupancy_start_minute, item.occupancy_end_minute, item.delay_minutes) for item in plan.assignments}
    issues = validate_assignments(train_problems, platform_problems, assignments, horizon_start=plan.horizon_start_minute, horizon_end=plan.horizon_end_minute, maximum_delay=plan.maximum_delay_minutes)
    valid_solver = plan.solver_status in {SolverStatus.FEASIBLE.value, SolverStatus.OPTIMAL.value}
    if not valid_solver:
        issues.insert(0, ValidationIssue("SOLVER_RESULT", f"The solver result is {plan.solver_status}; there is no complete plan to validate."))
    route_issues = validate_route_reservations(database, plan, platform_constraints_passed=not issues) if valid_solver else []
    issues.extend(route_issues)
    plan.route_validated = not route_issues and valid_solver and len(plan.assignments) == len(trains)
    plan.is_validated = not issues
    plan.status = PlanStatus.READY if not issues else PlanStatus.INVALID
    database.commit()
    return get_plan(database, simulation_session.id, plan.id), issues


def apply_plan(database: Session, simulation_session: SimulationSession, plan_id: int, version: int) -> SchedulingPlan:
    plan = get_plan(database, simulation_session.id, plan_id)
    if plan.version != version:
        raise InvalidOperationError("The supplied schedule version does not match the persisted plan.")
    if is_stale(database, plan):
        raise InvalidOperationError("A newer schedule version exists. Validate and apply the latest plan instead.")
    if plan.status != PlanStatus.READY or not plan.is_validated or not plan.route_validated:
        raise InvalidOperationError("Only a schedule with validated platform constraints and route reservations can be applied.")
    prior = list(database.scalars(select(SchedulingPlan).where(SchedulingPlan.session_id == simulation_session.id, SchedulingPlan.status == PlanStatus.APPLIED)).all())
    for item in prior:
        item.status = PlanStatus.ARCHIVED
    plan.status = PlanStatus.APPLIED
    database.commit()
    return get_plan(database, simulation_session.id, plan.id)
