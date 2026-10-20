from uuid import uuid4


def session_headers() -> dict[str, str]:
    return {"X-RailOps-Session": str(uuid4())}


def train_payload(identifier: str = "RA-901") -> dict[str, object]:
    return {
        "identifier": identifier,
        "priority": 3,
        "arrival_minute": 900,
        "departure_minute": 920,
        "minimum_dwell_minutes": 10,
        "length_meters": 220,
        "required_platform_type": "passenger",
        "compatible_platform_codes": ["P1", "P2"],
        "service_status": "scheduled",
        "delay_minutes": 0,
    }


def test_default_workspace_has_twenty_trains_and_five_platforms(client) -> None:
    headers = session_headers()

    trains = client.get("/api/trains", headers=headers)
    platforms = client.get("/api/platforms", headers=headers)
    overview = client.get("/api/overview", headers=headers)

    assert trains.status_code == 200
    assert len(trains.json()) == 20
    assert platforms.status_code == 200
    assert len(platforms.json()) == 5
    assert overview.json()["train_count"] == 20
    assert overview.json()["available_platform_count"] == 5


def test_train_crud_persists_and_remains_scoped(client) -> None:
    first = session_headers()
    second = session_headers()

    created = client.post("/api/trains", headers=first, json=train_payload())
    assert created.status_code == 201
    train_id = created.json()["train"]["id"]

    fetched = client.get(f"/api/trains/{train_id}", headers=first)
    assert fetched.status_code == 200
    assert fetched.json()["identifier"] == "RA-901"

    updated = client.patch(
        f"/api/trains/{train_id}",
        headers=first,
        json={"service_status": "delayed", "delay_minutes": 15},
    )
    assert updated.status_code == 200
    assert updated.json()["train"]["delay_minutes"] == 15
    assert client.get(f"/api/trains/{train_id}", headers=first).json()["service_status"] == "delayed"

    assert len(client.get("/api/trains", headers=first).json()) == 21
    assert len(client.get("/api/trains", headers=second).json()) == 20

    deleted = client.delete(f"/api/trains/{train_id}", headers=first)
    assert deleted.status_code == 200
    assert client.get(f"/api/trains/{train_id}", headers=first).status_code == 404


def test_train_validation_and_duplicate_errors_are_structured(client) -> None:
    headers = session_headers()
    invalid = train_payload("RA-902")
    invalid["departure_minute"] = 905

    response = client.post("/api/trains", headers=headers, json=invalid)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    first = client.post("/api/trains", headers=headers, json=train_payload("RA-903"))
    second = client.post("/api/trains", headers=headers, json=train_payload("RA-903"))
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_RECORD"


def test_platform_availability_update_persists(client) -> None:
    headers = session_headers()
    platform = client.get("/api/platforms", headers=headers).json()[0]

    response = client.patch(
        f"/api/platforms/{platform['id']}",
        headers=headers,
        json={"is_available": False, "unavailable_reason": "Planned inspection"},
    )

    assert response.status_code == 200
    assert response.json()["platform"]["is_available"] is False
    stored = client.get(f"/api/platforms/{platform['id']}", headers=headers).json()
    assert stored["unavailable_reason"] == "Planned inspection"


def test_platform_closure_requires_a_reason(client) -> None:
    headers = session_headers()
    platform = client.get("/api/platforms", headers=headers).json()[0]
    response = client.patch(
        f"/api/platforms/{platform['id']}",
        headers=headers,
        json={"is_available": False},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_all_demo_scenarios_are_available_and_restorable(client) -> None:
    headers = session_headers()
    scenarios = client.get("/api/scenarios").json()
    assert {item["key"] for item in scenarios} == {
        "normal-traffic",
        "congested-station",
        "multiple-delayed-trains",
        "platform-closure",
        "track-closure",
    }

    restored = client.post(
        "/api/scenarios/multiple-delayed-trains/restore", headers=headers
    )
    assert restored.status_code == 200
    overview = client.get("/api/overview", headers=headers).json()
    assert overview["scenario_key"] == "multiple-delayed-trains"
    assert overview["train_count"] == 20
    assert overview["delayed_train_count"] > 1

    closure = client.post("/api/scenarios/platform-closure/restore", headers=headers)
    assert closure.status_code == 200
    platforms = client.get("/api/platforms", headers=headers).json()
    assert sum(not item["is_available"] for item in platforms) == 1


def test_missing_or_invalid_session_header_is_rejected(client) -> None:
    missing = client.get("/api/trains")
    invalid = client.get("/api/trains", headers={"X-RailOps-Session": "not-a-uuid"})
    assert missing.status_code == 400
    assert invalid.status_code == 400
    assert missing.json()["error"]["code"] == "INVALID_SESSION"
