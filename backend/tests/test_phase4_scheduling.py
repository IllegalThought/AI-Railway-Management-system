from uuid import uuid4

import pytest

from app.ai.scheduling import (
    Candidate,
    PlatformProblem,
    SolverStatus,
    TrainProblem,
    build_domains,
    solve_cp_sat,
    solve_csp,
    solve_fcfs,
)
from app.ai.validation import validate_assignments


def train(
    train_id: int,
    *,
    arrival: int = 0,
    departure: int = 10,
    priority: int = 3,
    length: int = 200,
    compatible: frozenset[int] = frozenset({1}),
) -> TrainProblem:
    return TrainProblem(train_id, f"T{train_id}", priority, arrival, departure, 5, length, "passenger", 0, compatible)


def platform(platform_id: int = 1, *, length: int = 300, available: bool = True, clearance: int = 0) -> PlatformProblem:
    return PlatformProblem(platform_id, f"P{platform_id}", "passenger", length, clearance, available)


def test_custom_csp_finds_valid_reproducible_assignment_with_clearance() -> None:
    trains = [train(1), train(2)]
    platforms = [platform(clearance=2)]
    domains = build_domains(trains, platforms, horizon_start=0, horizon_end=30, maximum_delay=15)

    first = solve_csp(trains, platforms, domains, {}, node_limit=10_000)
    second = solve_csp(trains, platforms, domains, {}, node_limit=10_000)

    assert first.status == SolverStatus.FEASIBLE
    assert first.assignments == second.assignments
    assert not validate_assignments(trains, platforms, first.assignments, horizon_start=0, horizon_end=30, maximum_delay=15)
    ordered = sorted(first.assignments.values(), key=lambda item: item.start)
    assert ordered[1].start >= ordered[0].end + 2


@pytest.mark.parametrize(
    ("platforms", "candidate", "expected_code"),
    [
        ([platform(available=False)], Candidate(1, 0, 10, 0), "PLATFORM_UNAVAILABLE"),
        ([platform(length=150)], Candidate(1, 0, 10, 0), "INSUFFICIENT_LENGTH"),
        ([platform(2)], Candidate(2, 0, 10, 0), "PLATFORM_INCOMPATIBLE"),
    ],
)
def test_validator_rejects_closure_capacity_and_incompatibility(platforms, candidate, expected_code) -> None:
    issues = validate_assignments([train(1)], platforms, {1: candidate}, horizon_start=0, horizon_end=20, maximum_delay=10)
    assert expected_code in {issue.code for issue in issues}


def test_validator_rejects_overlapping_reservations() -> None:
    trains = [train(1), train(2, arrival=5, departure=15)]
    platforms = [platform(clearance=3)]
    assignments = {1: Candidate(1, 0, 10, 0), 2: Candidate(1, 10, 20, 5)}
    issues = validate_assignments(trains, platforms, assignments, horizon_start=0, horizon_end=30, maximum_delay=10)
    assert "PLATFORM_OVERLAP" in {issue.code for issue in issues}


def test_fcfs_and_csp_report_infeasible_when_capacity_is_insufficient() -> None:
    trains = [train(1), train(2)]
    platforms = [platform()]
    domains = build_domains(trains, platforms, horizon_start=0, horizon_end=10, maximum_delay=0)
    assert solve_fcfs(trains, platforms, domains, {}).status == SolverStatus.INFEASIBLE
    assert solve_csp(trains, platforms, domains, {}, node_limit=100).status == SolverStatus.INFEASIBLE


def test_csp_distinguishes_a_search_limit_from_infeasibility() -> None:
    trains = [train(1), train(2)]
    platforms = [platform()]
    domains = build_domains(trains, platforms, horizon_start=0, horizon_end=30, maximum_delay=15)
    result = solve_csp(trains, platforms, domains, {}, node_limit=1)
    assert result.status == SolverStatus.SEARCH_LIMIT
    assert "limit" in result.explanation.lower()


def test_cp_sat_minimizes_weighted_delay_for_higher_priority_train() -> None:
    pytest.importorskip("ortools")
    trains = [train(1, priority=1), train(2, priority=5)]
    platforms = [platform()]
    domains = build_domains(trains, platforms, horizon_start=0, horizon_end=20, maximum_delay=10)
    result = solve_cp_sat(trains, platforms, domains, {}, time_limit_seconds=5)
    assert result.status == SolverStatus.OPTIMAL
    assert result.assignments[1].delay == 0
    assert result.assignments[2].delay == 10
    assert result.objective == 10


def test_schedule_api_generate_validate_apply_and_reject_stale_version(client) -> None:
    headers = {"X-RailOps-Session": str(uuid4())}
    generated = client.post("/api/schedules/generate", headers=headers, json={"engine": "csp", "maximum_delay_minutes": 30})
    assert generated.status_code == 201
    first = generated.json()
    assert first["solver_status"] == "FEASIBLE"
    assert len(first["assignments"]) == 20
    assert first["route_reservations_provisional"] is True

    validated = client.post("/api/schedules/validate", headers=headers, json={"plan_id": first["id"], "version": first["version"]})
    assert validated.status_code == 200
    assert validated.json()["valid"] is True
    assert "Phase 5" in validated.json()["message"]

    applied = client.post("/api/schedules/apply", headers=headers, json={"plan_id": first["id"], "version": first["version"]})
    assert applied.status_code == 200
    assert applied.json()["plan"]["lifecycle_status"] == "applied"

    newer = client.post("/api/schedules/generate", headers=headers, json={"engine": "fcfs"})
    assert newer.status_code == 201
    stale = client.post("/api/schedules/apply", headers=headers, json={"plan_id": first["id"], "version": first["version"]})
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "INVALID_OPERATION"
    assert client.get("/api/schedules/current", headers=headers).json()["version"] == newer.json()["version"]


def test_platform_closure_scenario_generates_without_closed_platform(client) -> None:
    headers = {"X-RailOps-Session": str(uuid4())}
    client.post("/api/scenarios/platform-closure/restore", headers=headers)
    response = client.post("/api/schedules/generate", headers=headers, json={"engine": "fcfs"})
    assert response.status_code == 201
    body = response.json()
    assert body["solver_status"] == "FEASIBLE"
    assert "P3" not in {item["platform_code"] for item in body["assignments"]}
