"""Network monitoring, route feasibility, and reservation persistence."""

from __future__ import annotations

import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.ai.inference import infer_movement
from app.ai.routing import Reservation, RouteNotFoundError, astar_route, build_graph, reference_shortest_cost, reserve_available_route
from app.ai.validation import ValidationIssue
from app.models import Incident, RouteMovement, RouteReservation, SchedulingPlan, TrackEdge, TrackNode, TrainAssignment
from app.models.enums import IncidentStatus


def load_network(database: Session, session_id: int) -> tuple[list[TrackNode], list[TrackEdge], set[str]]:
    nodes = list(database.scalars(select(TrackNode).where(TrackNode.session_id == session_id).order_by(TrackNode.code)).all())
    edges = list(database.scalars(select(TrackEdge).where(TrackEdge.session_id == session_id).options(selectinload(TrackEdge.from_node), selectinload(TrackEdge.to_node)).order_by(TrackEdge.code)).all())
    blocked = set(database.scalars(select(Incident.resource_code).where(Incident.session_id == session_id, Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.MONITORING]), Incident.resource_code.is_not(None))).all())
    return nodes, edges, blocked


def validate_route_reservations(database: Session, plan: SchedulingPlan, *, platform_constraints_passed: bool) -> list[ValidationIssue]:
    nodes, edges, blocked = load_network(database, plan.session_id)
    graph = build_graph(nodes, edges, blocked)
    assignment_ids = [item.id for item in plan.assignments]
    if assignment_ids:
        movement_ids = list(database.scalars(select(RouteMovement.id).where(RouteMovement.assignment_id.in_(assignment_ids))).all())
        if movement_ids:
            database.execute(delete(RouteReservation).where(RouteReservation.movement_id.in_(movement_ids)))
        database.execute(delete(RouteMovement).where(RouteMovement.assignment_id.in_(assignment_ids)))
        database.flush()

    issues: list[ValidationIssue] = []
    committed: list[Reservation] = []
    assignments = sorted(plan.assignments, key=lambda item: (item.occupancy_start_minute, item.train.identifier))
    for assignment in assignments:
        train = assignment.train
        platform_code = assignment.platform.code
        origin, destination = train.origin_node_code, train.destination_node_code
        route_reservations: list[Reservation] = []
        path_nodes: list[str] = []
        route_reserved: bool | None = None
        track_occupied = False
        blocked_resource: str | None = None
        failure = ""
        if not origin or not destination:
            failure = f"{train.identifier} is missing a mandatory entry or exit point."
            issues.append(ValidationIssue("MISSING_ROUTE_INFORMATION", failure, train.id, assignment.platform_id))
        elif platform_code not in graph:
            failure = f"Platform {platform_code} has no modeled network connection."
            issues.append(ValidationIssue("MISSING_PLATFORM_CONNECTION", failure, train.id, assignment.platform_id))
            route_reserved = False
        else:
            try:
                if astar_route(graph, origin, platform_code).travel_minutes != reference_shortest_cost(graph, origin, platform_code):
                    raise RuntimeError("A* ingress cost did not match the Dijkstra reference result.")
                if astar_route(graph, platform_code, destination).travel_minutes != reference_shortest_cost(graph, platform_code, destination):
                    raise RuntimeError("A* egress cost did not match the Dijkstra reference result.")
                ingress, ingress_reservations = reserve_available_route(graph, origin, platform_code, assignment.occupancy_start_minute, align="end", existing=committed, blocked_resources=blocked)
                egress, egress_reservations = reserve_available_route(graph, platform_code, destination, assignment.occupancy_end_minute, align="start", existing=committed + ingress_reservations, blocked_resources=blocked, sequence_offset=len(ingress.edge_codes))
                route_reservations = ingress_reservations + egress_reservations
                committed.extend(route_reservations)
                path_nodes = list(ingress.nodes) + list(egress.nodes[1:])
                route_reserved = True
            except RouteNotFoundError as exc:
                failure = str(exc)
                blocked_resource = next((item for item in blocked if item in failure or item in {origin, destination}), None)
                if blocked and not blocked_resource:
                    blocked_resource = sorted(blocked)[0]
                track_occupied = not blocked_resource
                code = "RESOURCE_BLOCKED" if blocked_resource else "ROUTE_CONFLICT_OR_UNREACHABLE"
                issues.append(ValidationIssue(code, f"{train.identifier}: {failure}", train.id, assignment.platform_id))
                route_reserved = False

        compatible = assignment.platform_id in {item.platform_id for item in train.compatible_platforms} and assignment.platform.is_available
        if not platform_constraints_passed and not blocked_resource:
            blocked_resource = "PLATFORM_CONSTRAINT"
        inference = infer_movement(
            train.identifier,
            platform_code,
            platform_occupied=platform_constraints_passed,
            platform_compatible=compatible,
            route_reserved=route_reserved,
            track_occupied=track_occupied,
            blocked_resource=blocked_resource,
        )
        movement = RouteMovement(
            assignment_id=assignment.id,
            origin_node_code=origin,
            destination_node_code=destination,
            path_json=json.dumps(path_nodes),
            indicator=inference.indicator,
            decision=inference.decision,
            explanation=f"{failure + ' ' if failure else ''}{inference.explanation}",
        )
        database.add(movement)
        database.flush()
        database.add_all(
            [
                RouteReservation(
                    movement_id=movement.id,
                    resource_code=item.resource_code,
                    resource_type=item.resource_type,
                    edge_code=item.edge_code,
                    start_minute=item.start_minute,
                    end_minute=item.end_minute,
                    sequence=item.sequence,
                )
                for item in route_reservations
            ]
        )
    database.flush()
    return issues
def get_monitor_data(database: Session, session_id: int, plan: SchedulingPlan | None) -> dict:
    nodes, edges, blocked = load_network(database, session_id)
    movements: list[RouteMovement] = []
    if plan:
        movements = list(database.scalars(select(RouteMovement).join(TrainAssignment).where(TrainAssignment.plan_id == plan.id).options(selectinload(RouteMovement.assignment).selectinload(TrainAssignment.train), selectinload(RouteMovement.assignment).selectinload(TrainAssignment.platform), selectinload(RouteMovement.reservations))).unique().all())
    return {
        "nodes": nodes,
        "edges": edges,
        "blocked": blocked,
        "movements": movements,
        "plan": plan,
    }
