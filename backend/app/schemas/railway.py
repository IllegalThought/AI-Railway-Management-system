from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.models.enums import TrainStatus
from app.schemas.common import ApiModel
from app.schemas.validators import (
    validate_half_open_interval,
    validate_minute,
    validate_non_blank,
    validate_unique_values,
)


class TrainCreate(ApiModel):
    identifier: str = Field(min_length=1, max_length=40)
    priority: int = Field(ge=1, le=5)
    arrival_minute: int
    departure_minute: int
    minimum_dwell_minutes: int = Field(gt=0)
    length_meters: int = Field(gt=0, le=1_000)
    required_platform_type: str | None = Field(default=None, max_length=40)
    compatible_platform_codes: list[str] = Field(default_factory=list)
    service_status: TrainStatus = TrainStatus.SCHEDULED
    delay_minutes: int = Field(default=0, ge=0, le=1_440)

    @field_validator("identifier")
    @classmethod
    def identifier_must_be_present(cls, value: str) -> str:
        return validate_non_blank(value, "Train identifier")

    @field_validator("arrival_minute", "departure_minute")
    @classmethod
    def minutes_must_be_valid(cls, value: int, info) -> int:
        return validate_minute(value, info.field_name.replace("_", " ").capitalize())

    @field_validator("required_platform_type")
    @classmethod
    def normalize_optional_type(cls, value: str | None) -> str | None:
        return validate_non_blank(value, "Required platform type") if value is not None else None

    @field_validator("compatible_platform_codes")
    @classmethod
    def validate_platform_codes(cls, values: list[str]) -> list[str]:
        normalized = [validate_non_blank(value, "Platform code") for value in values]
        validate_unique_values(normalized, "Compatible platform codes")
        return normalized

    @model_validator(mode="after")
    def validate_timing(self) -> "TrainCreate":
        validate_half_open_interval(
            self.arrival_minute, self.departure_minute, "Train occupancy window"
        )
        if self.departure_minute - self.arrival_minute < self.minimum_dwell_minutes:
            raise ValueError(
                "Train occupancy window must be at least the minimum dwell time."
            )
        if self.service_status == TrainStatus.DELAYED and self.delay_minutes == 0:
            raise ValueError("Delayed trains must have a positive delay in minutes.")
        if self.service_status != TrainStatus.DELAYED and self.delay_minutes != 0:
            raise ValueError("Only delayed trains may have a positive delay in minutes.")
        return self


class TrainUpdate(ApiModel):
    identifier: str | None = Field(default=None, min_length=1, max_length=40)
    priority: int | None = Field(default=None, ge=1, le=5)
    arrival_minute: int | None = None
    departure_minute: int | None = None
    minimum_dwell_minutes: int | None = Field(default=None, gt=0)
    length_meters: int | None = Field(default=None, gt=0, le=1_000)
    required_platform_type: str | None = Field(default=None, max_length=40)
    compatible_platform_codes: list[str] | None = None
    service_status: TrainStatus | None = None
    delay_minutes: int | None = Field(default=None, ge=0, le=1_440)

    @field_validator("identifier")
    @classmethod
    def identifier_must_be_present(cls, value: str | None) -> str | None:
        return validate_non_blank(value, "Train identifier") if value is not None else None

    @field_validator("arrival_minute", "departure_minute")
    @classmethod
    def minutes_must_be_valid(cls, value: int | None, info) -> int | None:
        return validate_minute(value, info.field_name.replace("_", " ").capitalize()) if value is not None else None

    @field_validator("required_platform_type")
    @classmethod
    def normalize_optional_type(cls, value: str | None) -> str | None:
        return validate_non_blank(value, "Required platform type") if value is not None else None

    @field_validator("compatible_platform_codes")
    @classmethod
    def validate_platform_codes(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [validate_non_blank(value, "Platform code") for value in values]
        validate_unique_values(normalized, "Compatible platform codes")
        return normalized


class TrainResponse(ApiModel):
    id: int
    identifier: str
    priority: int
    arrival_minute: int
    departure_minute: int
    minimum_dwell_minutes: int
    length_meters: int
    required_platform_type: str | None
    compatible_platform_codes: list[str]
    service_status: TrainStatus
    delay_minutes: int
    created_at: datetime
    updated_at: datetime


class TrainMutationResponse(ApiModel):
    train: TrainResponse
    schedule_validation_required: bool = False


class DeleteTrainResponse(ApiModel):
    message: str
    deleted_id: int
    schedule_validation_required: bool = False


class PlatformCreate(ApiModel):
    code: str = Field(min_length=1, max_length=40)
    platform_type: str = Field(min_length=1, max_length=40)
    length_meters: int = Field(gt=0, le=2_000)
    clearance_minutes: int = Field(ge=0, le=120)
    is_available: bool = True
    unavailable_reason: str | None = Field(default=None, max_length=200)

    @field_validator("code", "platform_type")
    @classmethod
    def text_must_be_present(cls, value: str, info) -> str:
        return validate_non_blank(value, info.field_name.replace("_", " ").capitalize())

    @model_validator(mode="after")
    def validate_availability(self) -> "PlatformCreate":
        if not self.is_available and not self.unavailable_reason:
            raise ValueError("An unavailable platform must include a reason.")
        if self.is_available and self.unavailable_reason:
            raise ValueError("An available platform cannot include an unavailable reason.")
        return self


class PlatformUpdate(ApiModel):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    platform_type: str | None = Field(default=None, min_length=1, max_length=40)
    length_meters: int | None = Field(default=None, gt=0, le=2_000)
    clearance_minutes: int | None = Field(default=None, ge=0, le=120)
    is_available: bool | None = None
    unavailable_reason: str | None = Field(default=None, max_length=200)

    @field_validator("code", "platform_type")
    @classmethod
    def text_must_be_present(cls, value: str | None, info) -> str | None:
        return validate_non_blank(value, info.field_name.replace("_", " ").capitalize()) if value is not None else None


class PlatformResponse(ApiModel):
    id: int
    code: str
    platform_type: str
    length_meters: int
    clearance_minutes: int
    is_available: bool
    unavailable_reason: str | None
    compatible_train_count: int
    created_at: datetime
    updated_at: datetime


class PlatformMutationResponse(ApiModel):
    platform: PlatformResponse
    schedule_validation_required: bool = False


class TrainAssignmentInput(ApiModel):
    train_identifier: str = Field(min_length=1, max_length=40)
    platform_code: str = Field(min_length=1, max_length=40)
    occupancy_start_minute: int
    occupancy_end_minute: int

    @field_validator("train_identifier", "platform_code")
    @classmethod
    def codes_must_be_present(cls, value: str, info) -> str:
        return validate_non_blank(value, info.field_name.replace("_", " ").capitalize())

    @model_validator(mode="after")
    def validate_occupancy(self) -> "TrainAssignmentInput":
        validate_half_open_interval(
            self.occupancy_start_minute,
            self.occupancy_end_minute,
            "Assignment occupancy",
        )
        return self


class SchedulingInput(ApiModel):
    plan_name: str = Field(min_length=1, max_length=120)
    horizon_start_minute: int
    horizon_end_minute: int
    assignments: list[TrainAssignmentInput] = Field(default_factory=list)

    @field_validator("plan_name")
    @classmethod
    def name_must_be_present(cls, value: str) -> str:
        return validate_non_blank(value, "Plan name")

    @model_validator(mode="after")
    def validate_schedule(self) -> "SchedulingInput":
        validate_half_open_interval(
            self.horizon_start_minute,
            self.horizon_end_minute,
            "Scheduling horizon",
        )
        identifiers = [item.train_identifier for item in self.assignments]
        validate_unique_values(identifiers, "Assignment train identifiers")
        for assignment in self.assignments:
            if (
                assignment.occupancy_start_minute < self.horizon_start_minute
                or assignment.occupancy_end_minute > self.horizon_end_minute
            ):
                raise ValueError(
                    "Every assignment occupancy interval must be contained within the scheduling horizon."
                )
        return self

