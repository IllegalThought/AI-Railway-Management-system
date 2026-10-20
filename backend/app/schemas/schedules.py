from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.schemas.common import ApiModel
from app.schemas.validators import validate_half_open_interval


class SchedulingEngine(StrEnum):
    CSP = "csp"
    FCFS = "fcfs"
    CP_SAT = "cp_sat"


class GenerateScheduleRequest(ApiModel):
    engine: SchedulingEngine = SchedulingEngine.CP_SAT
    horizon_start_minute: int | None = Field(default=None, ge=0, le=10_080)
    horizon_end_minute: int | None = Field(default=None, ge=1, le=10_080)
    maximum_delay_minutes: int = Field(default=30, ge=0, le=240)
    search_limit: int = Field(default=100_000, ge=1, le=5_000_000)
    time_limit_seconds: float = Field(default=10, gt=0, le=60)

    @model_validator(mode="after")
    def validate_horizon(self) -> "GenerateScheduleRequest":
        if (self.horizon_start_minute is None) != (self.horizon_end_minute is None):
            raise ValueError("Both scheduling horizon values must be supplied together.")
        if self.horizon_start_minute is not None and self.horizon_end_minute is not None:
            validate_half_open_interval(self.horizon_start_minute, self.horizon_end_minute, "Scheduling horizon")
        return self


class PlanActionRequest(ApiModel):
    plan_id: int = Field(gt=0)
    version: int = Field(gt=0)


class SchedulePlatform(ApiModel):
    id: int
    code: str
    platform_type: str
    length_meters: int
    clearance_minutes: int
    is_available: bool


class ScheduleAssignment(ApiModel):
    id: int
    train_id: int
    train_identifier: str
    platform_id: int
    platform_code: str
    priority: int
    planned_arrival_minute: int
    planned_departure_minute: int
    occupancy_start_minute: int
    occupancy_end_minute: int
    delay_minutes: int
    reassigned: bool


class ValidationIssueResponse(ApiModel):
    code: str
    message: str
    train_id: int | None = None
    platform_id: int | None = None


class SchedulePlanResponse(ApiModel):
    id: int
    name: str
    version: int
    lifecycle_status: str
    solver_status: str
    engine: SchedulingEngine
    horizon_start_minute: int
    horizon_end_minute: int
    maximum_delay_minutes: int
    objective_value: int | None
    execution_time_ms: float | None
    is_validated: bool
    is_stale: bool
    route_reservations_provisional: bool = True
    explanation: str
    assignments: list[ScheduleAssignment]
    platforms: list[SchedulePlatform]
    created_at: datetime
    updated_at: datetime


class ValidateScheduleResponse(ApiModel):
    plan: SchedulePlanResponse
    valid: bool
    issues: list[ValidationIssueResponse]
    message: str


class ApplyScheduleResponse(ApiModel):
    plan: SchedulePlanResponse
    message: str
