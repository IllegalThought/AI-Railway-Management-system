"""Phase 8 release-candidate integration and security regression coverage."""

from uuid import uuid4


def test_complete_operational_workflow_reaches_analytics(client) -> None:
    request_headers = {"X-RailOps-Session": str(uuid4())}

    overview = client.get("/api/overview", headers=request_headers)
    trains = client.get("/api/trains", headers=request_headers)
    assert overview.status_code == 200
    assert trains.status_code == 200
    assert overview.json()["train_count"] == len(trains.json()) > 0

    generated = client.post(
        "/api/schedules/generate",
        headers=request_headers,
        json={"engine": "csp", "maximum_delay_minutes": 60},
    )
    assert generated.status_code == 201
    plan = generated.json()
    assert plan["solver_status"] == "FEASIBLE"
    assert len(plan["assignments"]) == len(trains.json())

    validated = client.post(
        "/api/schedules/validate",
        headers=request_headers,
        json={"plan_id": plan["id"], "version": plan["version"]},
    )
    assert validated.status_code == 200
    assert validated.json()["valid"] is True

    applied = client.post(
        "/api/schedules/apply",
        headers=request_headers,
        json={"plan_id": plan["id"], "version": plan["version"]},
    )
    assert applied.status_code == 200
    applied_plan = applied.json()["plan"]
    assert applied_plan["lifecycle_status"] == "applied"

    network = client.get("/api/network/monitor", headers=request_headers)
    assert network.status_code == 200
    assert network.json()["route_validation_complete"] is True
    assert len(network.json()["movements"]) == len(applied_plan["assignments"])

    initial_state = client.get("/api/simulation/state", headers=request_headers).json()
    started = client.post(
        "/api/simulation/control",
        headers=request_headers,
        json={"action": "start", "expected_revision": initial_state["revision"], "speed": 1},
    )
    assert started.status_code == 200
    running_state = started.json()
    assert running_state["run_status"] == "running"
    paused = client.post(
        "/api/simulation/control",
        headers=request_headers,
        json={"action": "pause", "expected_revision": running_state["revision"]},
    )
    assert paused.status_code == 200
    paused_state = paused.json()

    future_assignment = max(
        applied_plan["assignments"], key=lambda item: item["occupancy_start_minute"]
    )
    incident = client.post(
        "/api/incidents",
        headers=request_headers,
        json={
            "incident_type": "train_arrival_delay",
            "affected_resource": future_assignment["train_identifier"],
            "start_minute": paused_state["current_minute"],
            "duration_minutes": 8,
            "severity": "medium",
            "description": "Synthetic inbound delay used for release workflow verification.",
        },
    )
    assert incident.status_code == 201

    replanned = client.post(
        "/api/incidents/replan",
        headers=request_headers,
        json={
            "incident_id": incident.json()["id"],
            "base_plan_id": applied_plan["id"],
            "base_plan_version": applied_plan["version"],
            "expected_simulation_revision": paused_state["revision"],
        },
    )
    assert replanned.status_code == 200
    revision = replanned.json()
    assert revision["valid"] is True
    assert revision["changes"]

    revised_plan = revision["revised_plan"]
    revised_apply = client.post(
        "/api/schedules/apply",
        headers=request_headers,
        json={"plan_id": revised_plan["id"], "version": revised_plan["version"]},
    )
    assert revised_apply.status_code == 200
    assert revised_apply.json()["plan"]["lifecycle_status"] == "applied"

    analytics = client.get("/api/analytics", headers=request_headers)
    assert analytics.status_code == 200
    analytics_body = analytics.json()
    assert analytics_body["metrics"]["plan_id"] == revised_plan["id"]
    # Processing count is completion-based, so immediately applying a revised
    # plan correctly reports zero completed trains at the reset horizon start.
    assert analytics_body["metrics"]["train_processing_count"] == sum(
        item["occupancy_end_minute"] <= paused_state["current_minute"]
        for item in revised_plan["assignments"]
    )
    assert analytics_body["platform_decisions"]
    assert analytics_body["decision_insights"]
    assert any(item["category"] == "replanning" for item in analytics_body["decision_insights"])


def test_release_security_headers_and_request_limit(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"

    oversized = client.post(
        "/api/schedules/generate",
        content=b"x" * 1_048_577,
        headers={"content-type": "application/json"},
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "REQUEST_TOO_LARGE"
