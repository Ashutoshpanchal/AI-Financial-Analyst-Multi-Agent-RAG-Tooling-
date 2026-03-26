from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=422, detail=detail)


class ServiceError(AppException):
    def __init__(self, detail: str = "Internal service error"):
        super().__init__(status_code=500, detail=detail)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler — converts AppException into a consistent JSON error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )
