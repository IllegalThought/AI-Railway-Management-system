from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_error_handlers
from app.schemas.railway import TrainCreate
from app.services.exceptions import DuplicateRecordError


def build_error_test_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.post("/validated")
    def validated_route(_payload: TrainCreate) -> dict[str, str]:
        return {"message": "Input accepted."}

    @app.get("/duplicate")
    def duplicate_route() -> None:
        raise DuplicateRecordError("The requested record already exists.")

    return app


def test_request_validation_uses_structured_english_error() -> None:
    with TestClient(build_error_test_app()) as client:
        response = client.post(
            "/validated",
            json={
                "identifier": "RA-606",
                "priority": 9,
                "arrival_minute": 100,
                "departure_minute": 120,
                "minimum_dwell_minutes": 10,
                "length_meters": 200,
            },
        )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Request validation failed."
    assert body["details"][0]["field"] == "priority"


def test_application_error_uses_typed_error_shape() -> None:
    with TestClient(build_error_test_app()) as client:
        response = client.get("/duplicate")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "DUPLICATE_RECORD",
            "message": "The requested record already exists.",
            "details": [],
        }
    }
