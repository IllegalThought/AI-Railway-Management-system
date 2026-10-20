from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.services.exceptions import ApplicationError


def register_error_handlers(app: FastAPI) -> None:
    def validation_response(errors) -> JSONResponse:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            details.append(
                {
                    "field": location or None,
                    "message": str(error.get("msg", "Invalid value.")),
                    "type": error.get("type"),
                }
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": details,
                }
            },
        )

    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request, exc: ApplicationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": []}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return validation_response(exc.errors())

    @app.exception_handler(ValidationError)
    async def handle_domain_validation_error(
        _request: Request, exc: ValidationError
    ) -> JSONResponse:
        return validation_response(exc.errors())

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        _request: Request, _exc: SQLAlchemyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "The database operation could not be completed.",
                    "details": [],
                }
            },
        )

