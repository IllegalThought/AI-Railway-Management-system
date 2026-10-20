from fastapi import APIRouter

from app.api.dependencies import ActiveSession, DatabaseSession
from app.schemas.common import ErrorResponse
from app.schemas.operations import ScenarioResponse, ScenarioRestoreResponse
from app.services.scenarios import list_scenarios, restore_scenario


router = APIRouter(prefix="/scenarios", tags=["Demo scenarios"])


def _response(scenario) -> ScenarioResponse:
    return ScenarioResponse(
        key=scenario.key,
        name=scenario.name,
        description=scenario.description,
        train_count=scenario.train_count,
        platform_count=scenario.platform_count,
    )


@router.get("", response_model=list[ScenarioResponse])
def get_scenarios() -> list[ScenarioResponse]:
    return [_response(scenario) for scenario in list_scenarios()]


@router.post("/{scenario_key}/restore", response_model=ScenarioRestoreResponse, responses={404: {"model": ErrorResponse}})
def restore_demo_scenario(scenario_key: str, database: DatabaseSession, simulation_session: ActiveSession) -> ScenarioRestoreResponse:
    scenario = restore_scenario(database, simulation_session, scenario_key)
    return ScenarioRestoreResponse(scenario=_response(scenario), message=f"The {scenario.name} scenario was restored successfully.")
