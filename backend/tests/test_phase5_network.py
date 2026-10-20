from types import SimpleNamespace
from uuid import uuid4

import networkx as nx
import pytest

from app.ai.inference import infer_movement
from app.ai.routing import Reservation, RouteNotFoundError, astar_route, build_graph, reference_shortest_cost, reservation_conflict, reserve_available_route


def graph() -> nx.DiGraph:
    value = nx.DiGraph()
    value.add_node("A", x=0, y=0, node_type="entry", blocked=False)
    value.add_node("B", x=10, y=0, node_type="switch", blocked=False)
    value.add_node("C", x=20, y=0, node_type="exit", blocked=False)
    value.add_node("D", x=10, y=10, node_type="junction", blocked=False)
    value.add_edge("A", "B", code="AB", travel_time=2, resource_group="MAIN", blocked=False)
    value.add_edge("B", "C", code="BC", travel_time=2, resource_group="MAIN-2", blocked=False)
    value.add_edge("A", "D", code="AD", travel_time=3, resource_group="RELIEF", blocked=False)
    value.add_edge("D", "C", code="DC", travel_time=3, resource_group="RELIEF-2", blocked=False)
    return value


def test_custom_astar_matches_dijkstra_shortest_path() -> None:
    network = graph()
    result = astar_route(network, "A", "C")
    assert result.nodes == ("A", "B", "C")
    assert result.travel_minutes == reference_shortest_cost(network, "A", "C") == 4


def test_astar_handles_unreachable_destination_and_nonnegative_costs() -> None:
    network = graph()
    network.remove_edge("B", "C")
    network.remove_edge("D", "C")
    with pytest.raises(RouteNotFoundError):
        astar_route(network, "A", "C")
    network.add_edge("A", "C", code="AC", travel_time=-1, resource_group=None, blocked=False)
    with pytest.raises(ValueError, match="nonnegative"):
        astar_route(network, "A", "C")


def test_closure_and_conflict_select_an_alternative_path() -> None:
    network = graph()
    conflict = Reservation("MAIN", "track", 10, 13, "AB", 0)
    path, reservations = reserve_available_route(network, "A", "C", 10, align="start", existing=[conflict], blocked_resources=set())
    assert path.nodes == ("A", "D", "C")
    assert not any(reservation_conflict(item, [conflict]) for item in reservations)
    network["A"]["B"]["blocked"] = True
    assert astar_route(network, "A", "C").nodes == ("A", "D", "C")


def test_reservations_reject_overlap_and_allow_adjacent_intervals() -> None:
    existing = [Reservation("SW-1", "switch", 10, 15, "E1", 0)]
    assert reservation_conflict(Reservation("SW-1", "switch", 14, 18, "E2", 0), existing) == existing[0]
    assert reservation_conflict(Reservation("SW-1", "switch", 15, 18, "E2", 0), existing) is None


def test_build_graph_models_shared_resources_and_blocked_sections() -> None:
    a = SimpleNamespace(code="A", name="Entry", node_type="entry", x=0, y=0)
    b = SimpleNamespace(code="B", name="Exit", node_type="exit", x=10, y=0)
    edge = SimpleNamespace(code="AB", from_node=a, to_node=b, traversal_minutes=2, capacity=1, resource_group="SHARED")
    network = build_graph([a, b], [edge], {"SHARED"})
    assert network["A"]["B"]["blocked"] is True


def test_forward_chaining_movement_indicator_transitions() -> None:
    pending = infer_movement("T1", "P1", platform_occupied=True, platform_compatible=True, route_reserved=None)
    allowed = infer_movement("T1", "P1", platform_occupied=True, platform_compatible=True, route_reserved=True)
    blocked = infer_movement("T1", "P1", platform_occupied=True, platform_compatible=True, route_reserved=False, blocked_resource="E1")
    assert (pending.indicator, allowed.indicator, blocked.indicator) == ("YELLOW", "GREEN", "RED")
    assert "MovementAllowed" in {fact.predicate for fact in allowed.facts}
    assert "ResourceBlocked(E1)" in blocked.explanation
    assert allowed.evaluated_rules


def test_complete_schedule_route_validation_and_monitor_api(client) -> None:
    headers = {"X-RailOps-Session": str(uuid4())}
    generated = client.post("/api/schedules/generate", headers=headers, json={"engine": "csp"}).json()
    validated = client.post("/api/schedules/validate", headers=headers, json={"plan_id": generated["id"], "version": generated["version"]})
    assert validated.status_code == 200
    assert validated.json()["valid"] is True
    assert validated.json()["plan"]["route_reservations_provisional"] is False
    monitor = client.get("/api/network/monitor", headers=headers)
    assert monitor.status_code == 200
    payload = monitor.json()
    assert payload["route_validation_complete"] is True
    assert len(payload["nodes"]) >= 10
    assert len(payload["movements"]) == 20
    assert {item["indicator"] for item in payload["movements"]} == {"GREEN"}
    assert all(item["reservations"] for item in payload["movements"])


def test_track_closure_blocks_validation_and_never_shows_green(client) -> None:
    headers = {"X-RailOps-Session": str(uuid4())}
    assert client.post("/api/scenarios/track-closure/restore", headers=headers).status_code == 200
    generated = client.post("/api/schedules/generate", headers=headers, json={"engine": "csp"}).json()
    validated = client.post("/api/schedules/validate", headers=headers, json={"plan_id": generated["id"], "version": generated["version"]}).json()
    assert validated["valid"] is False
    assert "RESOURCE_BLOCKED" in {item["code"] for item in validated["issues"]}
    monitor = client.get("/api/network/monitor", headers=headers).json()
    assert "T-WEST-01" in monitor["blocked_resources"]
    assert "GREEN" not in {item["indicator"] for item in monitor["movements"]}
