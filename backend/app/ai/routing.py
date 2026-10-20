"""Directed graph routing and exclusive time-based resource reservations."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Callable, Iterable

import networkx as nx


class RouteNotFoundError(ValueError):
    """Raised when no usable directed path connects two network nodes."""


@dataclass(frozen=True)
class RoutePath:
    nodes: tuple[str, ...]
    edge_codes: tuple[str, ...]
    travel_minutes: int


@dataclass(frozen=True)
class Reservation:
    resource_code: str
    resource_type: str
    start_minute: int
    end_minute: int
    edge_code: str | None
    sequence: int


def build_graph(nodes: Iterable[object], edges: Iterable[object], blocked_resources: set[str] | None = None) -> nx.DiGraph:
    blocked = blocked_resources or set()
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node.code, name=node.name, node_type=node.node_type, x=node.x, y=node.y, blocked=node.code in blocked)
    for edge in edges:
        resource = edge.resource_group or edge.code
        graph.add_edge(
            edge.from_node.code,
            edge.to_node.code,
            code=edge.code,
            travel_time=edge.traversal_minutes,
            capacity=edge.capacity,
            resource_group=edge.resource_group,
            blocked=edge.code in blocked or resource in blocked,
        )
    return graph


def admissible_heuristic(graph: nx.DiGraph, node: str, target: str) -> float:
    """Euclidean lower bound scaled by the cheapest cost per layout unit."""
    left, right = graph.nodes[node], graph.nodes[target]
    distance = math.hypot(float(left.get("x", 0)) - float(right.get("x", 0)), float(left.get("y", 0)) - float(right.get("y", 0)))
    ratios = []
    for start, end, data in graph.edges(data=True):
        start_data, end_data = graph.nodes[start], graph.nodes[end]
        length = math.hypot(float(start_data.get("x", 0)) - float(end_data.get("x", 0)), float(start_data.get("y", 0)) - float(end_data.get("y", 0)))
        if length > 0:
            ratios.append(float(data["travel_time"]) / length)
    return distance * min(ratios) if ratios else 0.0


def astar_route(
    graph: nx.DiGraph,
    source: str,
    target: str,
    *,
    excluded_edges: set[str] | None = None,
    edge_filter: Callable[[str, str, dict, int], bool] | None = None,
) -> RoutePath:
    """Find a minimum travel-time path with a custom deterministic A* search."""
    if source not in graph or target not in graph:
        raise RouteNotFoundError(f"Route endpoint is missing: {source} to {target}.")
    excluded = excluded_edges or set()
    frontier: list[tuple[float, int, str, tuple[str, ...], tuple[str, ...]]] = [(admissible_heuristic(graph, source, target), 0, source, (source,), ())]
    best_cost: dict[str, int] = {source: 0}
    while frontier:
        _, cost, node, nodes, edge_codes = heapq.heappop(frontier)
        if cost != best_cost.get(node):
            continue
        if node == target:
            return RoutePath(nodes, edge_codes, cost)
        for neighbor in sorted(graph.successors(node)):
            data = graph[node][neighbor]
            travel_time = int(data.get("travel_time", -1))
            if travel_time < 0:
                raise ValueError("A* requires nonnegative travel-time costs.")
            if data.get("blocked") or data["code"] in excluded:
                continue
            if graph.nodes[neighbor].get("blocked") or (edge_filter and not edge_filter(node, neighbor, data, cost)):
                continue
            next_cost = cost + travel_time
            if next_cost >= best_cost.get(neighbor, math.inf):
                continue
            best_cost[neighbor] = next_cost
            heapq.heappush(frontier, (next_cost + admissible_heuristic(graph, neighbor, target), next_cost, neighbor, nodes + (neighbor,), edge_codes + (data["code"],)))
    raise RouteNotFoundError(f"No available route connects {source} to {target}.")


def intervals_overlap(left_start: int, left_end: int, right_start: int, right_end: int) -> bool:
    return left_start < right_end and right_start < left_end


def reservation_conflict(candidate: Reservation, existing: Iterable[Reservation]) -> Reservation | None:
    return next((item for item in existing if item.resource_code == candidate.resource_code and intervals_overlap(candidate.start_minute, candidate.end_minute, item.start_minute, item.end_minute)), None)


def path_reservations(graph: nx.DiGraph, path: RoutePath, anchor_minute: int, *, align: str, sequence_offset: int = 0) -> list[Reservation]:
    if align not in {"start", "end"}:
        raise ValueError("Reservation alignment must be 'start' or 'end'.")
    minute = anchor_minute if align == "start" else anchor_minute - path.travel_minutes
    reservations: list[Reservation] = []
    for index, (start, end, edge_code) in enumerate(zip(path.nodes[:-1], path.nodes[1:], path.edge_codes, strict=True)):
        data = graph[start][end]
        edge_end = minute + int(data["travel_time"])
        sequence = sequence_offset + index
        reservations.append(Reservation(data.get("resource_group") or edge_code, "track", minute, edge_end, edge_code, sequence))
        for node in (start, end):
            if graph.nodes[node].get("node_type") == "switch":
                reservations.append(Reservation(node, "switch", minute, edge_end, edge_code, sequence))
        minute = edge_end
    return reservations


def reserve_available_route(
    graph: nx.DiGraph,
    source: str,
    target: str,
    anchor_minute: int,
    *,
    align: str,
    existing: list[Reservation],
    blocked_resources: set[str],
    sequence_offset: int = 0,
) -> tuple[RoutePath, list[Reservation]]:
    """Find a shortest available path, excluding conflicts until an alternative is found."""
    excluded: set[str] = set()
    while True:
        path = astar_route(graph, source, target, excluded_edges=excluded)
        candidates = path_reservations(graph, path, anchor_minute, align=align, sequence_offset=sequence_offset)
        conflict = next((item for item in candidates if item.resource_code in blocked_resources or reservation_conflict(item, existing)), None)
        if conflict is None:
            return path, candidates
        if conflict.edge_code is None or conflict.edge_code in excluded:
            raise RouteNotFoundError(f"No conflict-free route connects {source} to {target}.")
        excluded.add(conflict.edge_code)


def reference_shortest_cost(graph: nx.DiGraph, source: str, target: str) -> int:
    """NetworkX/Dijkstra reference used by validation and tests."""
    usable = nx.subgraph_view(graph, filter_node=lambda node: not graph.nodes[node].get("blocked"), filter_edge=lambda left, right: not graph[left][right].get("blocked"))
    try:
        return int(nx.dijkstra_path_length(usable, source, target, weight="travel_time"))
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exc:
        raise RouteNotFoundError(f"No available route connects {source} to {target}.") from exc
