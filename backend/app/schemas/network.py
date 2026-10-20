from pydantic import Field

from app.schemas.common import ApiModel


class NetworkNodeResponse(ApiModel):
    code: str
    name: str
    node_type: str
    x: int
    y: int
    blocked: bool


class NetworkEdgeResponse(ApiModel):
    code: str
    from_node: str
    to_node: str
    traversal_minutes: int
    capacity: int
    resource_group: str | None
    blocked: bool


class ReservationResponse(ApiModel):
    resource_code: str
    resource_type: str
    edge_code: str | None
    start_minute: int
    end_minute: int
    sequence: int


class MovementResponse(ApiModel):
    train_id: int
    train_identifier: str
    platform_code: str
    origin_node_code: str | None
    destination_node_code: str | None
    path: list[str]
    indicator: str
    decision: str
    explanation: str
    reservations: list[ReservationResponse]


class NetworkMonitorResponse(ApiModel):
    plan_id: int | None
    plan_version: int | None
    route_validation_complete: bool
    nodes: list[NetworkNodeResponse]
    edges: list[NetworkEdgeResponse]
    movements: list[MovementResponse]
    blocked_resources: list[str]
    message: str = Field(min_length=1)
