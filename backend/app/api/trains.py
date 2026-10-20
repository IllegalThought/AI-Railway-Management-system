from fastapi import APIRouter, status

from app.api.dependencies import ActiveSession, DatabaseSession
from app.api.serializers import train_response
from app.schemas.common import ErrorResponse
from app.schemas.railway import (
    DeleteTrainResponse,
    TrainCreate,
    TrainMutationResponse,
    TrainResponse,
    TrainUpdate,
)
from app.services import records


router = APIRouter(prefix="/trains", tags=["Trains"])


@router.get("", response_model=list[TrainResponse], summary="List trains in the demo workspace")
def list_trains(database: DatabaseSession, simulation_session: ActiveSession) -> list[TrainResponse]:
    return [train_response(item) for item in records.list_trains(database, session_id=simulation_session.id)]


@router.post("", response_model=TrainMutationResponse, status_code=status.HTTP_201_CREATED, responses={409: {"model": ErrorResponse}})
def create_train(data: TrainCreate, database: DatabaseSession, simulation_session: ActiveSession) -> TrainMutationResponse:
    train = records.create_train(database, session_id=simulation_session.id, data=data)
    validation_required = records.invalidate_active_plans(database, simulation_session.id)
    return TrainMutationResponse(train=train_response(train), schedule_validation_required=validation_required)


@router.get("/{train_id}", response_model=TrainResponse, responses={404: {"model": ErrorResponse}})
def get_train(train_id: int, database: DatabaseSession, simulation_session: ActiveSession) -> TrainResponse:
    return train_response(records.get_train(database, session_id=simulation_session.id, train_id=train_id))


@router.patch("/{train_id}", response_model=TrainMutationResponse, responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def update_train(train_id: int, data: TrainUpdate, database: DatabaseSession, simulation_session: ActiveSession) -> TrainMutationResponse:
    train, validation_required = records.update_train(database, simulation_session=simulation_session, train_id=train_id, data=data)
    return TrainMutationResponse(train=train_response(train), schedule_validation_required=validation_required)


@router.delete("/{train_id}", response_model=DeleteTrainResponse, responses={404: {"model": ErrorResponse}})
def delete_train(train_id: int, database: DatabaseSession, simulation_session: ActiveSession) -> DeleteTrainResponse:
    validation_required = records.delete_train(database, simulation_session=simulation_session, train_id=train_id)
    return DeleteTrainResponse(message="Train deleted successfully.", deleted_id=train_id, schedule_validation_required=validation_required)
