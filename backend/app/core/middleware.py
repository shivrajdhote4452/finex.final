import contextvars
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="none")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates an X-Correlation-ID for each request,
    stores it in request.state and contextvars, and appends it to response headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cid = request.headers.get("X-Correlation-ID")
        if not cid:
            cid = str(uuid.uuid4())

        request.state.correlation_id = cid
        token = correlation_id_ctx.set(cid)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        except Exception:
            from backend.app.core.errors import build_error_response

            response = build_error_response(
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. The incident has been recorded for review.",
                correlation_id=cid,
            )
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            correlation_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to attach defensive HTTP security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
