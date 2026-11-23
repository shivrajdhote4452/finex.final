import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException as FastAPIHTTPException
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

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


class RateLimitException(FinExException):
    def __init__(
        self, message: str = "Rate limit exceeded. Please retry after the cooling window.", retry_after: int = 60
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.retry_after = retry_after


class PayloadTooLargeException(FinExException):
    def __init__(self, message: str = "Request payload exceeds permissible limit"):
        super().__init__(
            message=message,
            code="PAYLOAD_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    correlation_id: str,
    details: Optional[List[ErrorDetail]] = None,
    headers: Optional[Dict[str, str]] = None,
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
    content = payload.model_dump()
    content["detail"] = message  # Standard FastAPI/Starlette client and test compatibility
    return JSONResponse(status_code=status_code, content=content, headers=headers)


async def finex_exception_handler(request: Request, exc: FinExException) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown-correlation-id")
    logger.warning(
        f"FinExException [{exc.code}] on {request.method} {request.url.path}: {exc.message} (cid: {correlation_id})"
    )
    if exc.status_code >= 400:
        try:
            from backend.app.services.error_recorder import record_error_event

            await record_error_event(
                request=request,
                exc=exc,
                status_code=exc.status_code,
                message=exc.message,
                correlation_id=correlation_id,
            )
        except Exception as rec_err:
            logger.warning(f"Failed to record FinExException event: {rec_err}")

    headers = getattr(exc, "headers", None)
    if not headers and hasattr(exc, "retry_after"):
        headers = {"Retry-After": str(exc.retry_after)}
    return build_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        correlation_id=correlation_id,
        details=exc.details,
        headers=headers,
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

    try:
        from backend.app.services.error_recorder import record_error_event

        summary_issue = "; ".join(f"{d.field}: {d.issue}" for d in details[:3])
        await record_error_event(
            request=request,
            exc=exc,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Validation error: {summary_issue}",
            correlation_id=correlation_id,
        )
    except Exception as rec_err:
        logger.warning(f"Failed to record validation error event: {rec_err}")

    return build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request payload failed validation schema.",
        correlation_id=correlation_id,
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown-correlation-id")
    if isinstance(exc, (FastAPIHTTPException, StarletteHTTPException)):
        logger.warning(
            f"HTTPException [{exc.status_code}] on {request.method} {request.url.path}: {exc.detail} (cid: {correlation_id})"
        )
        if exc.status_code >= 400 and exc.status_code != 404:
            try:
                from backend.app.services.error_recorder import record_error_event

                await record_error_event(
                    request=request,
                    exc=exc,
                    status_code=exc.status_code,
                    message=str(exc.detail),
                    correlation_id=correlation_id,
                )
            except Exception as rec_err:
                logger.warning(f"Failed to record HTTPException event: {rec_err}")

        return build_error_response(
            status_code=exc.status_code,
            code="HTTP_EXCEPTION",
            message=str(exc.detail),
            correlation_id=correlation_id,
            headers=getattr(exc, "headers", None),
        )

    logger.error(
        f"Unhandled server error on {request.method} {request.url.path}: {str(exc)} (cid: {correlation_id})",
        exc_info=True,
    )

    try:
        from backend.app.services.error_recorder import record_error_event

        await record_error_event(
            request=request,
            exc=exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{type(exc).__name__}: {str(exc)}",
            correlation_id=correlation_id,
        )
    except Exception as rec_err:
        logger.warning(f"Failed to record unhandled server error event: {rec_err}")

    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message=f"{type(exc).__name__}: {str(exc)}",
        correlation_id=correlation_id,
    )
