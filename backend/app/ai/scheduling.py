"""Platform allocation algorithms for the synthetic RailOps simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable


class SolverStatus(StrEnum):
    FEASIBLE = "FEASIBLE"
    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"
    SEARCH_LIMIT = "SEARCH_LIMIT"


@dataclass(frozen=True)
class TrainProblem:
    id: int
    identifier: str
    priority: int
    arrival: int
    departure: int
    minimum_dwell: int
    length: int
    required_type: str | None
    recorded_delay: int
    compatible_platform_ids: frozenset[int]

    @property
    def duration(self) -> int:
        return max(self.minimum_dwell, self.departure - self.arrival)


@dataclass(frozen=True)
class PlatformProblem:
    id: int
    code: str
    platform_type: str
    length: int
    clearance: int
    available: bool


@dataclass(frozen=True)
class Candidate:
    platform_id: int
    start: int
    end: int
    delay: int


@dataclass
class ScheduleResult:
    status: SolverStatus
    assignments: dict[int, Candidate] = field(default_factory=dict)
    objective: int | None = None
    explored_nodes: int = 0
    explanation: str = ""


def priority_weight(priority: int) -> int:
    return 6 - priority


def assignment_cost(train: TrainProblem, candidate: Candidate, preferred: dict[int, int]) -> int:
    reassignment = 15 if train.id in preferred and preferred[train.id] != candidate.platform_id else 0
    return priority_weight(train.priority) * candidate.delay + reassignment


def build_domains(
    trains: Iterable[TrainProblem],
    platforms: Iterable[PlatformProblem],
    *,
    horizon_start: int,
    horizon_end: int,
    maximum_delay: int,
) -> dict[int, list[Candidate]]:
    platform_list = list(platforms)
    domains: dict[int, list[Candidate]] = {}
    for train in trains:
        choices: list[Candidate] = []
        earliest = train.arrival + train.recorded_delay
        latest = train.arrival + maximum_delay
        for platform in platform_list:
            if (
                not platform.available
                or platform.id not in train.compatible_platform_ids
                or train.length > platform.length
                or (train.required_type is not None and train.required_type != platform.platform_type)
            ):
                continue
            for start in range(max(earliest, horizon_start), latest + 1):
                end = start + train.duration
                if end <= horizon_end:
                    choices.append(Candidate(platform.id, start, end, start - train.arrival))
        domains[train.id] = choices
    return domains


def conflicts(left: Candidate, right: Candidate, platforms: dict[int, PlatformProblem]) -> bool:
    if left.platform_id != right.platform_id:
        return False
    clearance = platforms[left.platform_id].clearance
    return left.start < right.end + clearance and right.start < left.end + clearance


def solve_fcfs(
    trains: list[TrainProblem], platforms: list[PlatformProblem], domains: dict[int, list[Candidate]], preferred: dict[int, int]
) -> ScheduleResult:
    selected: dict[int, Candidate] = {}
    by_id = {item.id: item for item in trains}
    platform_map = {item.id: item for item in platforms}
    for train in sorted(trains, key=lambda item: (item.arrival + item.recorded_delay, item.identifier)):
        candidates = sorted(domains[train.id], key=lambda item: (item.start, assignment_cost(train, item, preferred), platform_map[item.platform_id].code))
        choice = next((item for item in candidates if all(not conflicts(item, other, platform_map) for other in selected.values())), None)
        if choice is None:
            return ScheduleResult(SolverStatus.INFEASIBLE, explored_nodes=len(selected), explanation=f"FCFS could not place {train.identifier} within its compatibility and delay limits.")
        selected[train.id] = choice
    objective = sum(assignment_cost(by_id[train_id], item, preferred) for train_id, item in selected.items())
    return ScheduleResult(SolverStatus.FEASIBLE, selected, objective, len(selected), "FCFS assigned trains in effective-arrival order using the earliest conflict-free platform slot.")


def solve_csp(
    trains: list[TrainProblem], platforms: list[PlatformProblem], domains: dict[int, list[Candidate]], preferred: dict[int, int], *, node_limit: int
) -> ScheduleResult:
    platform_map = {item.id: item for item in platforms}
    train_map = {item.id: item for item in trains}
    assigned: dict[int, Candidate] = {}
    nodes = 0
    limited = False

    def viable(train_id: int) -> list[Candidate]:
        return [candidate for candidate in domains[train_id] if all(not conflicts(candidate, other, platform_map) for other in assigned.values())]

    def search() -> bool:
        nonlocal nodes, limited
        if len(assigned) == len(trains):
            return True
        if nodes >= node_limit:
            limited = True
            return False
        remaining = [train.id for train in trains if train.id not in assigned]
        viable_domains = {train_id: viable(train_id) for train_id in remaining}
        train_id = min(remaining, key=lambda item: (len(viable_domains[item]), train_map[item].arrival, train_map[item].identifier))
        values = sorted(viable_domains[train_id], key=lambda item: (assignment_cost(train_map[train_id], item, preferred), item.start, item.platform_id))
        for candidate in values:
            nodes += 1
            assigned[train_id] = candidate
            # Forward checking: every remaining variable must retain a value.
            if all(viable(other_id) for other_id in remaining if other_id != train_id) and search():
                return True
            assigned.pop(train_id, None)
            if limited:
                return False
        return False

    solved = search()
    if not solved:
        status = SolverStatus.SEARCH_LIMIT if limited else SolverStatus.INFEASIBLE
        reason = "The CSP search limit was reached before a complete assignment was found." if limited else "The CSP proved that no assignment satisfies every hard constraint."
        return ScheduleResult(status, explored_nodes=nodes, explanation=reason)
    objective = sum(assignment_cost(train_map[train_id], item, preferred) for train_id, item in assigned.items())
    return ScheduleResult(SolverStatus.FEASIBLE, dict(assigned), objective, nodes, "The custom CSP used minimum remaining values, recursive backtracking, and forward checking to satisfy every hard constraint.")


def solve_cp_sat(
    trains: list[TrainProblem], platforms: list[PlatformProblem], domains: dict[int, list[Candidate]], preferred: dict[int, int], *, time_limit_seconds: float
) -> ScheduleResult:
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return ScheduleResult(SolverStatus.UNKNOWN, explanation="OR-Tools is not installed in the backend runtime.")

    if any(not domains[train.id] for train in trains):
        return ScheduleResult(SolverStatus.INFEASIBLE, explanation="At least one train has no compatible platform slot within the scheduling horizon.")
    model = cp_model.CpModel()
    platform_map = {item.id: item for item in platforms}
    starts: dict[int, object] = {}
    presences: dict[tuple[int, int], object] = {}
    platform_intervals: dict[int, list[object]] = {platform.id: [] for platform in platforms}
    objective_terms: list[object] = []
    allowed_platforms: dict[int, list[int]] = {}

    for train in trains:
        candidates = domains[train.id]
        min_start = min(item.start for item in candidates)
        max_start = max(item.start for item in candidates)
        start = model.new_int_var(min_start, max_start, f"start_{train.id}")
        starts[train.id] = start
        platform_ids = sorted({item.platform_id for item in candidates})
        allowed_platforms[train.id] = platform_ids
        train_presence = []
        allowed_starts = sorted({item.start for item in candidates})
        model.add_allowed_assignments([start], [[value] for value in allowed_starts])
        for platform_id in platform_ids:
            present = model.new_bool_var(f"train_{train.id}_platform_{platform_id}")
            presences[(train.id, platform_id)] = present
            train_presence.append(present)
            size = train.duration + platform_map[platform_id].clearance
            end = model.new_int_var(min_start + size, max_start + size, f"end_{train.id}_{platform_id}")
            interval = model.new_optional_interval_var(start, size, end, present, f"occupancy_{train.id}_{platform_id}")
            platform_intervals[platform_id].append(interval)
            if train.id in preferred and preferred[train.id] != platform_id:
                objective_terms.append(15 * present)
        model.add_exactly_one(train_presence)
        objective_terms.append(priority_weight(train.priority) * (start - train.arrival))

    for intervals in platform_intervals.values():
        if intervals:
            model.add_no_overlap(intervals)
    model.minimize(sum(objective_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    status_map = {
        cp_model.OPTIMAL: SolverStatus.OPTIMAL,
        cp_model.FEASIBLE: SolverStatus.FEASIBLE,
        cp_model.INFEASIBLE: SolverStatus.INFEASIBLE,
        cp_model.UNKNOWN: SolverStatus.UNKNOWN,
    }
    result_status = status_map.get(status, SolverStatus.UNKNOWN)
    if result_status not in {SolverStatus.FEASIBLE, SolverStatus.OPTIMAL}:
        return ScheduleResult(result_status, explanation=f"CP-SAT returned {result_status.value.upper()} for the constrained allocation model.")
    assignments: dict[int, Candidate] = {}
    for train in trains:
        start = solver.value(starts[train.id])
        platform_id = next(item for item in allowed_platforms[train.id] if solver.value(presences[(train.id, item)]))
        assignments[train.id] = Candidate(platform_id, start, start + train.duration, start - train.arrival)
    label = "proved the minimum objective" if result_status == SolverStatus.OPTIMAL else "found a feasible plan before the time limit"
    return ScheduleResult(result_status, assignments, round(solver.objective_value), int(solver.num_branches), f"CP-SAT {label} using optional platform intervals and non-overlap constraints.")
