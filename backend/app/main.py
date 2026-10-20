from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
            allow_headers=["Authorization", "Content-Type", "X-RailOps-Session"],
        )
    register_error_handlers(application)

    @application.middleware("http")
    async def release_security_controls(request: Request, call_next):
        """Apply bounded-request and browser hardening controls to every response."""

        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                request_size = int(content_length)
            except ValueError:
                request_size = runtime_settings.max_request_body_bytes + 1
            if request_size > runtime_settings.max_request_body_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": "The request body exceeds the configured size limit.",
                            "details": [],
                        }
                    },
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    application.include_router(api_router)
    if settings is not None:
        def get_runtime_settings() -> Settings:
            return runtime_settings

        application.dependency_overrides[get_settings] = get_runtime_settings
    return application


app = create_app()

