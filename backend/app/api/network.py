import json

from fastapi import APIRouter

from app.api.dependencies import ActiveSession, DatabaseSession
from app.schemas.network import MovementResponse, NetworkEdgeResponse, NetworkMonitorResponse, NetworkNodeResponse, ReservationResponse
from app.services import network, schedules


router = APIRouter(prefix="/network", tags=["Network"])


@router.get("/monitor", response_model=NetworkMonitorResponse)
def monitor(database: DatabaseSession, simulation_session: ActiveSession) -> NetworkMonitorResponse:
    plan = schedules.get_current_schedule(database, simulation_session.id)
    data = network.get_monitor_data(database, simulation_session.id, plan)
    blocked = data["blocked"]
    return NetworkMonitorResponse(
        plan_id=plan.id if plan else None,
        plan_version=plan.version if plan else None,
        route_validation_complete=bool(plan and plan.route_validated),
        nodes=[NetworkNodeResponse(code=item.code, name=item.name, node_type=item.node_type, x=item.x, y=item.y, blocked=item.code in blocked) for item in data["nodes"]],
        edges=[NetworkEdgeResponse(code=item.code, from_node=item.from_node.code, to_node=item.to_node.code, traversal_minutes=item.traversal_minutes, capacity=item.capacity, resource_group=item.resource_group, blocked=item.code in blocked or (item.resource_group or item.code) in blocked) for item in data["edges"]],
        movements=[
            MovementResponse(
                train_id=item.assignment.train_id,
                train_identifier=item.assignment.train.identifier,
                platform_code=item.assignment.platform.code,
                origin_node_code=item.origin_node_code,
                destination_node_code=item.destination_node_code,
                path=json.loads(item.path_json),
                indicator=item.indicator if item.indicator != "GREEN" or (plan and plan.route_validated and plan.is_validated) else "YELLOW",
                decision=item.decision if item.indicator != "GREEN" or (plan and plan.route_validated and plan.is_validated) else "MovementBlocked",
                explanation=item.explanation if item.indicator != "GREEN" or (plan and plan.route_validated and plan.is_validated) else f"Validation is stale or incomplete. {item.explanation}",
                reservations=[ReservationResponse(resource_code=reservation.resource_code, resource_type=reservation.resource_type, edge_code=reservation.edge_code, start_minute=reservation.start_minute, end_minute=reservation.end_minute, sequence=reservation.sequence) for reservation in sorted(item.reservations, key=lambda value: (value.sequence, value.resource_type))],
            )
            for item in sorted(data["movements"], key=lambda value: value.assignment.train.identifier)
        ],
        blocked_resources=sorted(blocked),
        message="Route reservations are validated for the current plan." if plan and plan.route_validated else "Validate the current dispatch plan to calculate movement routes and reservations.",
    )
