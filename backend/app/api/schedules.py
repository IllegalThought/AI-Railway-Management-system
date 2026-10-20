from fastapi import APIRouter, status

from app.api.dependencies import ActiveSession, DatabaseSession
from app.models import SchedulingPlan
from app.schemas.common import ErrorResponse
from app.schemas.schedules import (
    ApplyScheduleResponse,
    GenerateScheduleRequest,
    PlanActionRequest,
    ScheduleAssignment,
    SchedulePlanResponse,
    SchedulePlatform,
    ValidateScheduleResponse,
    ValidationIssueResponse,
)
from app.services import schedules


router = APIRouter(prefix="/schedules", tags=["Schedules"])


def plan_response(database: DatabaseSession, plan: SchedulingPlan) -> SchedulePlanResponse:
    platforms = schedules.load_resources(database, plan.session_id)[1]
    return SchedulePlanResponse(
        id=plan.id,
        name=plan.name,
        version=plan.version,
        lifecycle_status=plan.status.value,
        solver_status=plan.solver_status,
        engine=plan.engine,
        horizon_start_minute=plan.horizon_start_minute,
        horizon_end_minute=plan.horizon_end_minute,
        maximum_delay_minutes=plan.maximum_delay_minutes,
        objective_value=plan.objective_value,
        is_validated=plan.is_validated,
        is_stale=schedules.is_stale(database, plan),
        explanation=plan.explanation,
        assignments=[ScheduleAssignment(id=item.id, train_id=item.train_id, train_identifier=item.train.identifier, platform_id=item.platform_id, platform_code=item.platform.code, priority=item.train.priority, planned_arrival_minute=item.train.arrival_minute, planned_departure_minute=item.train.departure_minute, occupancy_start_minute=item.occupancy_start_minute, occupancy_end_minute=item.occupancy_end_minute, delay_minutes=item.delay_minutes, reassigned=item.reassigned) for item in sorted(plan.assignments, key=lambda assignment: (assignment.occupancy_start_minute, assignment.train.identifier))],
        platforms=[SchedulePlatform(id=item.id, code=item.code, platform_type=item.platform_type, length_meters=item.length_meters, clearance_minutes=item.clearance_minutes, is_available=item.is_available) for item in platforms],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post("/generate", response_model=SchedulePlanResponse, status_code=status.HTTP_201_CREATED)
def generate(data: GenerateScheduleRequest, database: DatabaseSession, simulation_session: ActiveSession) -> SchedulePlanResponse:
    return plan_response(database, schedules.generate_schedule(database, simulation_session, data))


@router.post("/validate", response_model=ValidateScheduleResponse, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def validate(data: PlanActionRequest, database: DatabaseSession, simulation_session: ActiveSession) -> ValidateScheduleResponse:
    plan, issues = schedules.validate_plan(database, simulation_session, data.plan_id, data.version)
    return ValidateScheduleResponse(plan=plan_response(database, plan), valid=not issues, issues=[ValidationIssueResponse.model_validate(item.__dict__) for item in issues], message="All platform constraints passed. Route reservations remain provisional until Phase 5." if not issues else f"Validation found {len(issues)} constraint issue(s).")


@router.post("/apply", response_model=ApplyScheduleResponse, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def apply(data: PlanActionRequest, database: DatabaseSession, simulation_session: ActiveSession) -> ApplyScheduleResponse:
    plan = schedules.apply_plan(database, simulation_session, data.plan_id, data.version)
    return ApplyScheduleResponse(plan=plan_response(database, plan), message="The platform plan was applied provisionally. Route reservations have not yet been validated.")


@router.get("/current", response_model=SchedulePlanResponse | None)
def current(database: DatabaseSession, simulation_session: ActiveSession) -> SchedulePlanResponse | None:
    plan = schedules.get_current_schedule(database, simulation_session.id)
    return plan_response(database, plan) if plan else None
