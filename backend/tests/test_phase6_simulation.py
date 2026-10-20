from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from app.database.base import utc_now
from app.models import RouteMovement, RouteReservation, SimulationSession, SimulationState, TrainAssignment


def headers() -> dict[str, str]:
    return {"X-RailOps-Session": str(uuid4())}


def applied_plan(client, request_headers: dict[str, str]) -> dict:
    plan = client.post("/api/schedules/generate", headers=request_headers, json={"engine": "csp", "maximum_delay_minutes": 60}).json()
    validated = client.post("/api/schedules/validate", headers=request_headers, json={"plan_id": plan["id"], "version": plan["version"]}).json()
    assert validated["valid"] is True
    return client.post("/api/schedules/apply", headers=request_headers, json={"plan_id": plan["id"], "version": plan["version"]}).json()["plan"]


def test_simulation_start_pause_step_reset_and_occupancy(client) -> None:
    request_headers = headers()
    plan = applied_plan(client, request_headers)
    initial = client.get("/api/simulation/state", headers=request_headers).json()
    assert initial["current_minute"] == plan["horizon_start_minute"]
    assert initial["run_status"] == "paused"
    assert any(item["occupied"] for item in initial["platforms"])
    assert initial["trains"][0]["position"]

    started = client.post("/api/simulation/control", headers=request_headers, json={"action": "start", "expected_revision": initial["revision"], "speed": 2})
    assert started.status_code == 200
    running = started.json()
    assert (running["run_status"], running["speed"]) == ("running", 2)

    stale = client.post("/api/simulation/control", headers=request_headers, json={"action": "pause", "expected_revision": initial["revision"]})
    assert stale.status_code == 409
    paused = client.post("/api/simulation/control", headers=request_headers, json={"action": "pause", "expected_revision": running["revision"]}).json()
    stepped = client.post("/api/simulation/control", headers=request_headers, json={"action": "step", "expected_revision": paused["revision"], "speed": 5}).json()
    assert stepped["current_minute"] == paused["current_minute"] + 5
    reset = client.post("/api/simulation/control", headers=request_headers, json={"action": "reset", "expected_revision": stepped["revision"]}).json()
    assert reset["current_minute"] == plan["horizon_start_minute"]
    assert reset["run_status"] == "paused"


def test_backend_clock_progresses_and_state_survives_requests(client, database_engine) -> None:
    request_headers = headers()
    applied_plan(client, request_headers)
    initial = client.get("/api/simulation/state", headers=request_headers).json()
    running = client.post("/api/simulation/control", headers=request_headers, json={"action": "start", "expected_revision": initial["revision"], "speed": 2}).json()
    from sqlalchemy.orm import Session
    with Session(database_engine) as database:
        public_id = request_headers["X-RailOps-Session"]
        session_id = database.scalar(select(SimulationSession.id).where(SimulationSession.public_id == public_id))
        state = database.scalar(select(SimulationState).where(SimulationState.session_id == session_id))
        state.last_tick_at = utc_now() - timedelta(seconds=3)
        database.commit()
    progressed = client.get("/api/simulation/state", headers=request_headers).json()
    assert progressed["current_minute"] >= running["current_minute"] + 6
    assert progressed["revision"] > running["revision"]


def test_delay_incident_replanning_preserves_committed_and_rejects_stale_plan(client, database_engine) -> None:
    request_headers = headers()
    plan = applied_plan(client, request_headers)
    state = client.get("/api/simulation/state", headers=request_headers).json()
    incident = client.post("/api/incidents", headers=request_headers, json={
        "incident_type": "train_arrival_delay", "affected_resource": "RA-102", "start_minute": state["current_minute"],
        "duration_minutes": 8, "severity": "medium", "description": "Late inbound handover in the synthetic simulation."
    })
    assert incident.status_code == 201
    assert incident.json()["affected_train_ids"]
    replanned = client.post("/api/incidents/replan", headers=request_headers, json={
        "incident_id": incident.json()["id"], "base_plan_id": plan["id"], "base_plan_version": plan["version"],
        "expected_simulation_revision": state["revision"]
    })
    assert replanned.status_code == 200
    body = replanned.json()
    assert body["valid"] is True
    assert body["preserved_train_ids"]
    preserved_id = body["preserved_train_ids"][0]
    from sqlalchemy.orm import Session
    with Session(database_engine) as database:
        def reservations(plan_id: int) -> list[tuple]:
            return list(database.execute(select(RouteReservation.resource_code, RouteReservation.edge_code, RouteReservation.start_minute, RouteReservation.end_minute, RouteReservation.sequence).join(RouteMovement).join(TrainAssignment).where(TrainAssignment.plan_id == plan_id, TrainAssignment.train_id == preserved_id).order_by(RouteReservation.sequence, RouteReservation.resource_type)).all())
        assert reservations(plan["id"]) == reservations(body["revised_plan"]["id"])
    assert any(item["train_identifier"] == "RA-102" and item["change"] in {"Reallocated", "Unchanged"} for item in body["changes"])
    stale = client.post("/api/incidents/replan", headers=request_headers, json={
        "incident_id": incident.json()["id"], "base_plan_id": plan["id"], "base_plan_version": plan["version"],
        "expected_simulation_revision": state["revision"]
    })
    assert stale.status_code == 409


def test_platform_closure_replanning_and_session_isolation(client) -> None:
    first, second = headers(), headers()
    first_plan = applied_plan(client, first)
    applied_plan(client, second)
    first_state = client.get("/api/simulation/state", headers=first).json()
    response = client.post("/api/incidents", headers=first, json={
        "incident_type": "platform_closure", "affected_resource": "P5", "start_minute": first_state["current_minute"] + 1,
        "duration_minutes": 30, "severity": "high", "description": "Synthetic platform surface defect."
    })
    assert response.status_code == 201
    replanned = client.post("/api/incidents/replan", headers=first, json={
        "incident_id": response.json()["id"], "base_plan_id": first_plan["id"], "base_plan_version": first_plan["version"],
        "expected_simulation_revision": first_state["revision"]
    }).json()
    if replanned["valid"]:
        assert "P5" not in {item["platform_code"] for item in replanned["revised_plan"]["assignments"] if item["train_id"] not in replanned["preserved_train_ids"]}
    assert client.get("/api/incidents", headers=second).json() == []
    second_platforms = client.get("/api/platforms", headers=second).json()
    assert next(item for item in second_platforms if item["code"] == "P5")["is_available"] is True


def test_remaining_incident_types_create_valid_operational_records(client) -> None:
    request_headers = headers()
    common = {"start_minute": 365, "duration_minutes": 12, "severity": "medium", "description": "Synthetic Phase 6 incident test."}
    payloads = [
        {**common, "incident_type": "train_departure_delay", "affected_resource": "RA-102"},
        {**common, "incident_type": "track_blockage", "affected_resource": "T-WEST-01"},
        {**common, "incident_type": "junction_closure", "affected_resource": "J-W"},
        {**common, "incident_type": "new_train_request", "affected_resource": "EXTRA-99", "new_train": {
            "identifier": "EXTRA-99", "priority": 2, "arrival_minute": 420, "departure_minute": 436,
            "minimum_dwell_minutes": 10, "length_meters": 200, "required_platform_type": "passenger",
            "compatible_platform_codes": ["P1", "P2"], "service_status": "scheduled", "delay_minutes": 0,
            "origin_node_code": "ENTRY-W", "destination_node_code": "EXIT-E",
        }},
    ]
    for payload in payloads:
        assert client.post("/api/incidents", headers=request_headers, json=payload).status_code == 201
    records = client.get("/api/incidents", headers=request_headers).json()
    assert {item["incident_type"] for item in records} == {item["incident_type"] for item in payloads}
    assert any(item["identifier"] == "EXTRA-99" for item in client.get("/api/trains", headers=request_headers).json())
