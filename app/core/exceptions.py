import logging
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    http_status: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, context: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context


class JobNotFoundError(AppError):
    http_status = 404
    code = "JOB_NOT_FOUND"

    def __init__(self, job_id: UUID) -> None:
        super().__init__(f"Generation job '{job_id}' was not found")


class CertificateNotFoundError(AppError):
    http_status = 404
    code = "CERTIFICATE_NOT_FOUND"

    def __init__(self, certificate_id: UUID) -> None:
        super().__init__(f"Certificate '{certificate_id}' was not found")


class CertificateNotReadyError(AppError):
    http_status = 409
    code = "CERTIFICATE_NOT_READY"

    def __init__(self, certificate_id: UUID, status: str, error_message: str | None = None) -> None:
        message = f"Certificate '{certificate_id}' is not available for download (status={status})"
        context = {"status": status}
        if error_message:
            context["error_message"] = error_message
        super().__init__(message, context=context)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message, "context": exc.context}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in err["loc"][1:]), "issue": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail)}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while processing request")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}},
        )
