from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    application = FastAPI(
        title=runtime_settings.app_name,
        version=runtime_settings.app_version,
        description=(
            "API foundation for the RailOps AI synthetic railway operations simulation. "
            "This service is not a certified railway signaling system."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/openapi.json",
    )
    if runtime_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=runtime_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    register_error_handlers(application)
    application.include_router(api_router)
    if settings is not None:
        def get_runtime_settings() -> Settings:
            return runtime_settings

        application.dependency_overrides[get_settings] = get_runtime_settings
    return application


app = create_app()

