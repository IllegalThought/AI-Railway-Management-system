from pydantic import Field, field_validator, model_validator

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
        return self


class PlatformCreate(ApiModel):
    code: str = Field(min_length=1, max_length=40)
    platform_type: str = Field(min_length=1, max_length=40)
    length_meters: int = Field(gt=0, le=2_000)
    clearance_minutes: int = Field(ge=0, le=120)

    @field_validator("code", "platform_type")
    @classmethod
    def text_must_be_present(cls, value: str, info) -> str:
        return validate_non_blank(value, info.field_name.replace("_", " ").capitalize())


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

