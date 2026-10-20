from fastapi import APIRouter

from app.api.dependencies import ActiveSession, DatabaseSession
from app.schemas.common import ErrorResponse
from app.schemas.simulation import (
    ActiveReservation,
    LiveEvent,
    LiveTrainState,
    PlatformOccupancy,
    SimulationControlRequest,
    SimulationStateResponse,
)
from app.services import simulation


router = APIRouter(prefix="/simulation", tags=["Live simulation"])


def state_response(database: DatabaseSession, session_id: int) -> SimulationStateResponse:
    projected = simulation.project_state(database, session_id)
    state, plan = projected["state"], projected["plan"]
    return SimulationStateResponse(
        current_minute=state.current_minute,
        run_status=state.run_status.value,
        speed=state.speed,
        revision=state.revision,
        active_plan_id=plan.id if plan else None,
        active_plan_version=plan.version if plan else None,
        trains=[LiveTrainState.model_validate(item) for item in projected["trains"]],
        platforms=[PlatformOccupancy.model_validate(item) for item in projected["platforms"]],
        active_reservations=[ActiveReservation.model_validate(item) for item in projected["reservations"]],
        events=[LiveEvent.model_validate(item) for item in projected["events"]],
        message="Live state is derived from the persisted validated plan." if plan else "Apply a validated schedule to begin live simulation.",
    )


@router.get("/state", response_model=SimulationStateResponse)
def get_state(database: DatabaseSession, simulation_session: ActiveSession) -> SimulationStateResponse:
    return state_response(database, simulation_session.id)


@router.post("/control", response_model=SimulationStateResponse, responses={409: {"model": ErrorResponse}})
def control(data: SimulationControlRequest, database: DatabaseSession, simulation_session: ActiveSession) -> SimulationStateResponse:
    simulation.control(database, simulation_session.id, data.action, data.expected_revision, data.speed)
    return state_response(database, simulation_session.id)
