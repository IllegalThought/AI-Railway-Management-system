from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ErrorDetail(ApiModel):
    field: str | None = None
    message: str
    type: str | None = None


class ErrorBody(ApiModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(ApiModel):
    error: ErrorBody


class MessageResponse(ApiModel):
    message: str
    context: dict[str, Any] = Field(default_factory=dict)

