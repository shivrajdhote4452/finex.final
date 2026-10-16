import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("finex.errors")


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(None, description="Path to offending field")
    issue: str = Field(..., description="Description of the specific problem")


class ErrorPayload(BaseModel):
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable safe explanation")
    details: Optional[List[ErrorDetail]] = Field(default=None, description="Detailed field errors")


class ErrorMeta(BaseModel):
    correlation_id: str = Field(..., description="Tracing UUID")
    timestamp: str = Field(..., description="UTC ISO-8601 timestamp")
    version: str = Field("v1", description="API version")


class ApiErrorResponse(BaseModel):
    success: bool = Field(False, description="Always false for error responses")
    error: ErrorPayload = Field(..., description="Error body")
    meta: ErrorMeta = Field(..., description="Request metadata")


class FinExException(Exception):
    """Base application exception for FinEx."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[ErrorDetail]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class NotFoundException(FinExException):
    def __init__(self, message: str = "Resource not found", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UnauthorizedException(FinExException):
    def __init__(self, message: str = "Authentication required", code: str = "UNAUTHORIZED"):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(FinExException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConflictException(FinExException):
    def __init__(self, message: str, code: str = "CONFLICT", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationException(FinExException):
    def __init__(self, message: str = "Validation failed", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ServiceUnavailableException(FinExException):
    def __init__(self, message: str = "Upstream service temporarily unavailable"):
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
    details: Optional[List[ErrorDetail]] = None,
) -> JSONResponse:
    payload = ApiErrorResponse(
        success=False,
        error=ErrorPayload(
            code=code,
            message=message,
            details=details,
        ),
        meta=ErrorMeta(
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="v1",
        ),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def finex_exception_handler(request: Request, exc: FinExException) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown-correlation-id")
    logger.warning(
        f"FinExException [{exc.code}] on {request.method} {request.url.path}: {exc.message} (cid: {correlation_id})"
    )
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        correlation_id=correlation_id,
        details=exc.details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown-correlation-id")
    details = []
    for err in exc.errors():
        field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
        details.append(ErrorDetail(field=field_path, issue=err.get("msg", "Invalid value")))

    logger.info(
        f"Validation error on {request.method} {request.url.path}: {len(details)} errors (cid: {correlation_id})"
    )
    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request payload failed validation schema.",
        correlation_id=correlation_id,
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown-correlation-id")
    logger.error(
        f"Unhandled server error on {request.method} {request.url.path}: {str(exc)} (cid: {correlation_id})",
        exc_info=True,
    )
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. The incident has been recorded for review.",
        correlation_id=correlation_id,
    )
