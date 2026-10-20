from fastapi import APIRouter

from app.api.dependencies import ActiveSession, DatabaseSession
from app.api.serializers import platform_response
from app.schemas.common import ErrorResponse
from app.schemas.railway import PlatformMutationResponse, PlatformResponse, PlatformUpdate
from app.services import records


router = APIRouter(prefix="/platforms", tags=["Platforms"])


@router.get("", response_model=list[PlatformResponse], summary="List platforms in the demo workspace")
def list_platforms(database: DatabaseSession, simulation_session: ActiveSession) -> list[PlatformResponse]:
    return [platform_response(item) for item in records.list_platforms(database, session_id=simulation_session.id)]


@router.get("/{platform_id}", response_model=PlatformResponse, responses={404: {"model": ErrorResponse}})
def get_platform(platform_id: int, database: DatabaseSession, simulation_session: ActiveSession) -> PlatformResponse:
    return platform_response(records.get_platform(database, session_id=simulation_session.id, platform_id=platform_id))


@router.patch("/{platform_id}", response_model=PlatformMutationResponse, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def update_platform(platform_id: int, data: PlatformUpdate, database: DatabaseSession, simulation_session: ActiveSession) -> PlatformMutationResponse:
    platform, validation_required = records.update_platform(database, simulation_session=simulation_session, platform_id=platform_id, data=data)
    return PlatformMutationResponse(platform=platform_response(platform), schedule_validation_required=validation_required)
