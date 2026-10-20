from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.models.enums import IncidentSeverity, IncidentStatus, IncidentType
from app.schemas.common import ApiModel
from app.schemas.railway import TrainCreate
from app.schemas.schedules import ScheduleAssignment, SchedulePlanResponse


class SimulationAction(StrEnum):
    START = "start"
    PAUSE = "pause"
    STEP = "step"
    RESET = "reset"


class SimulationControlRequest(ApiModel):
    action: SimulationAction
    expected_revision: int = Field(ge=0)
    speed: int | None = Field(default=None)

    @model_validator(mode="after")
    def validate_speed(self) -> "SimulationControlRequest":
        if self.speed is not None and self.speed not in {1, 2, 5}:
            raise ValueError("Simulation speed must be 1x, 2x, or 5x.")
        return self


class LiveTrainState(ApiModel):
    train_id: int
    train_identifier: str
    status: str
    position: str
    platform_code: str
    progress_percent: int = Field(ge=0, le=100)
    movement_permission: str
    signal: str


class PlatformOccupancy(ApiModel):
    platform_code: str
    train_identifier: str | None
    occupied: bool


class ActiveReservation(ApiModel):
    train_identifier: str
    resource_code: str
    resource_type: str
    start_minute: int
    end_minute: int


class LiveEvent(ApiModel):
    id: int
    event_type: str
    event_minute: int
    message: str
    resource_code: str | None


class SimulationStateResponse(ApiModel):
    current_minute: int
    run_status: str
    speed: int
    revision: int
    active_plan_id: int | None
    active_plan_version: int | None
    trains: list[LiveTrainState]
    platforms: list[PlatformOccupancy]
    active_reservations: list[ActiveReservation]
    events: list[LiveEvent]
    message: str


class IncidentCreate(ApiModel):
    incident_type: IncidentType
    affected_resource: str = Field(min_length=1, max_length=80)
    start_minute: int = Field(ge=0, le=10_080)
    duration_minutes: int = Field(gt=0, le=1_440)
    severity: IncidentSeverity
    description: str = Field(min_length=1, max_length=1_000)
    new_train: TrainCreate | None = None

    @model_validator(mode="after")
    def validate_new_train(self) -> "IncidentCreate":
        if self.incident_type == IncidentType.NEW_TRAIN_REQUEST and self.new_train is None:
            raise ValueError("A new train request must include train details.")
        if self.incident_type != IncidentType.NEW_TRAIN_REQUEST and self.new_train is not None:
            raise ValueError("Train details are only valid for a new train request.")
        return self


class IncidentResponse(ApiModel):
    id: int
    incident_type: IncidentType
    affected_resource: str
    start_minute: int
    duration_minutes: int
    severity: IncidentSeverity
    status: IncidentStatus
    description: str
    title: str
    affected_train_ids: list[int] = Field(default_factory=list)
    created_at: datetime


class ReplanRequest(ApiModel):
    incident_id: int = Field(gt=0)
    base_plan_id: int = Field(gt=0)
    base_plan_version: int = Field(gt=0)
    expected_simulation_revision: int = Field(ge=0)


class AssignmentChange(ApiModel):
    train_identifier: str
    before: ScheduleAssignment | None
    after: ScheduleAssignment | None
    change: str


class ReplanResponse(ApiModel):
    base_plan: SchedulePlanResponse
    revised_plan: SchedulePlanResponse
    valid: bool
    infeasible_reason: str | None
    preserved_train_ids: list[int]
    affected_train_ids: list[int]
    changes: list[AssignmentChange]
    message: str
