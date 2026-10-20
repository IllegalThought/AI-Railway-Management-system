from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.overview import router as overview_router
from app.api.platforms import router as platforms_router
from app.api.scenarios import router as scenarios_router
from app.api.trains import router as trains_router


api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(trains_router)
api_router.include_router(platforms_router)
api_router.include_router(scenarios_router)
api_router.include_router(overview_router)

