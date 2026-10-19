from typing import Literal

from app.schemas.common import ApiModel


class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str
    database: Literal["available"]
    message: str

