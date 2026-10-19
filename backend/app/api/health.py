from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.common import ErrorResponse
from app.schemas.health import HealthResponse


router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API and database health",
    responses={503: {"model": ErrorResponse, "description": "Database unavailable"}},
)
def health_check(
    database: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> HealthResponse:
    database.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database="available",
        message="RailOps AI API is operational.",
    )

