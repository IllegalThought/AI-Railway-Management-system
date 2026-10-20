from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.overview import router as overview_router
from app.api.network import router as network_router
from app.api.platforms import router as platforms_router
from app.api.scenarios import router as scenarios_router
from app.api.schedules import router as schedules_router
from app.api.trains import router as trains_router
from app.api.simulation import router as simulation_router
from app.api.incidents import router as incidents_router
from app.api.analytics import router as analytics_router


api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(trains_router)
api_router.include_router(platforms_router)
api_router.include_router(scenarios_router)
api_router.include_router(overview_router)
api_router.include_router(schedules_router)
api_router.include_router(network_router)
api_router.include_router(simulation_router)
api_router.include_router(incidents_router)
api_router.include_router(analytics_router)

