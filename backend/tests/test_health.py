from app.config import Settings, get_settings
from app.main import create_app


def test_health_endpoint_reports_api_and_database_status(client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "RailOps AI API",
        "version": "0.9.0",
        "environment": "test",
        "database": "available",
        "message": "RailOps AI API is operational.",
    }


def test_openapi_documents_health_response(client) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == 200
    health_operation = response.json()["paths"]["/api/health"]["get"]
    assert health_operation["summary"] == "Check API and database health"
    assert "200" in health_operation["responses"]
    assert "503" in health_operation["responses"]


def test_app_factory_keeps_injected_settings_consistent_with_dependencies(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    assert get_settings().app_env == "development"

    test_settings = Settings(APP_ENV="test", DATABASE_URL="sqlite://")
    application = create_app(test_settings)

    assert application.dependency_overrides[get_settings]() is test_settings

