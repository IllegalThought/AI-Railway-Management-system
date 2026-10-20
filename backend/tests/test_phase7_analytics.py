from uuid import uuid4

from app.services.analytics import delay_distribution, platform_utilization


def _applied_plan(client, headers):
    generated = client.post("/api/schedules/generate", headers=headers, json={"engine": "csp", "maximum_delay_minutes": 30})
    assert generated.status_code == 201
    plan = generated.json()
    validated = client.post("/api/schedules/validate", headers=headers, json={"plan_id": plan["id"], "version": plan["version"]})
    assert validated.status_code == 200 and validated.json()["valid"] is True
    applied = client.post("/api/schedules/apply", headers=headers, json={"plan_id": plan["id"], "version": plan["version"]})
    assert applied.status_code == 200
    return applied.json()["plan"]


def test_metric_helpers_calculate_distribution_and_utilization() -> None:
    class Assignment:
        def __init__(self, platform_id, start, end, delay):
            self.platform_id, self.occupancy_start_minute, self.occupancy_end_minute, self.delay_minutes = platform_id, start, end, delay

    class Plan:
        horizon_start_minute, horizon_end_minute = 0, 100
        assignments = [Assignment(1, 0, 20, 0), Assignment(1, 30, 50, 7), Assignment(2, 0, 10, 22)]

    class Platform:
        def __init__(self, platform_id, code): self.id, self.code = platform_id, code

    assert delay_distribution(Plan()) == [
        {"label": "On time", "train_count": 1}, {"label": "1–5 min", "train_count": 0},
        {"label": "6–10 min", "train_count": 1}, {"label": "11–20 min", "train_count": 0},
        {"label": "21+ min", "train_count": 1},
    ]
    usage = platform_utilization(Plan(), [Platform(1, "P1"), Platform(2, "P2")])
    assert usage[0] == {"platform_code": "P1", "occupied_minutes": 40, "utilization_percent": 40.0, "train_count": 2}


def test_analytics_endpoint_uses_persisted_schedule_and_real_decisions(client) -> None:
    headers = {"X-RailOps-Session": str(uuid4())}
    plan = _applied_plan(client, headers)
    response = client.get("/api/analytics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    delays = [item["delay_minutes"] for item in plan["assignments"]]
    assert body["metrics"]["total_arrival_delay_minutes"] == sum(delays)
    assert body["metrics"]["maximum_delay_minutes"] == max(delays)
    assert body["metrics"]["schedule_feasible"] is True
    assert body["metrics"]["solver_execution_time_ms"] >= 0
    assert len(body["platform_utilization"]) == 5
    assert len(body["platform_decisions"]) == len(plan["assignments"])
    first = body["platform_decisions"][0]
    assert first["assigned_platform"]
    assert any("overlap" in reason.lower() or "available" in reason.lower() for reason in first["accepted_reasons"])
    assert first["route_decision"] == "MovementAllowed"


def test_benchmark_compares_same_scenario_and_records_truthful_status(client) -> None:
    headers = {"X-RailOps-Session": str(uuid4())}
    response = client.post("/api/analytics/benchmarks", headers=headers, json={"maximum_delay_minutes": 30, "time_limit_seconds": 5})
    assert response.status_code == 201
    body = response.json()
    assert {item["engine"] for item in body["results"]} == {"fcfs", "csp", "cp_sat"}
    assert {item["scenario_identifier"] for item in body["results"]} == {body["scenario_identifier"]}
    assert {item["benchmark_id"] for item in body["results"]} == {body["benchmark_id"]}
    assert all(item["execution_time_ms"] >= 0 for item in body["results"])
    assert all(item["processed_train_count"] <= 20 for item in body["results"])
    assert all(item["maximum_delay_minutes"] <= 30 for item in body["results"])
    assert all(item["processed_train_count"] == 20 for item in body["results"] if item["solver_status"] in {"FEASIBLE", "OPTIMAL"})
    assert all(item["optimality_proven"] == (item["solver_status"] == "OPTIMAL") for item in body["results"])

    persisted = client.get("/api/analytics", headers=headers).json()["latest_benchmark"]
    assert {item["benchmark_id"] for item in persisted} == {body["benchmark_id"]}
