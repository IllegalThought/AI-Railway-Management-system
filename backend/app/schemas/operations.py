from datetime import datetime

from pydantic import Field

from app.schemas.common import ApiModel


class ScenarioResponse(ApiModel):
    key: str
    name: str
    description: str
    train_count: int
    platform_count: int


class ScenarioRestoreResponse(ApiModel):
    scenario: ScenarioResponse
    message: str


class IncidentSummary(ApiModel):
    id: int
    title: str
    severity: str
    status: str
    resource_code: str | None
    reported_minute: int


class ActivitySummary(ApiModel):
    id: int
    message: str
    event_type: str
    event_minute: int
    resource_code: str | None
    created_at: datetime


class OverviewResponse(ApiModel):
    scenario_key: str
    scenario_name: str
    train_count: int = Field(ge=0)
    scheduled_train_count: int = Field(ge=0)
    delayed_train_count: int = Field(ge=0)
    platform_count: int = Field(ge=0)
    available_platform_count: int = Field(ge=0)
    unavailable_platform_count: int = Field(ge=0)
    active_incident_count: int = Field(ge=0)
    upcoming_trains: list[dict[str, int | str]]
    active_incidents: list[IncidentSummary]
    recent_activity: list[ActivitySummary]
