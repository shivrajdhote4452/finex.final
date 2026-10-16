import collections
import contextvars
import time
import uuid
from typing import Callable, Dict, List, Optional

from backend.app.core.errors import build_error_response
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="none")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates an X-Correlation-ID for each request,
    tracks response execution latency, and appends identifiers to response headers.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        cid = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        if not cid:
            cid = str(uuid.uuid4())

        request.state.correlation_id = cid
        token = correlation_id_ctx.set(cid)

        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Correlation-ID"] = cid
            response.headers["X-Request-ID"] = cid
            response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
            return response
        except Exception:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            response = build_error_response(
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred. The incident has been recorded for review.",
                correlation_id=cid,
            )
            response.headers["X-Correlation-ID"] = cid
            response.headers["X-Request-ID"] = cid
            response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
            return response
        finally:
            correlation_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to attach defensive HTTP security headers to all responses,
    preventing MIME-sniffing, clickjacking, cross-site leakage, and framing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        path = request.url.path
        if any(p in path for p in ["/docs", "/redoc", "/openapi.json"]):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' https://cdn.jsdelivr.net; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "img-src 'self' data: https: https://fastapi.tiangolo.com; "
                "connect-src 'self' *; "
                "worker-src 'self' blob:; "
                "frame-ancestors 'none';"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' *; "
                "frame-ancestors 'none';"
            )
        return response



class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding-window rate limiter per client IP / auth token.
    Enforces distinct limits for auth / heavy endpoints vs standard routes.
    """

    def __init__(
        self,
        app,
        default_limit: int = 120,
        auth_limit: int = 30,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.window_seconds = window_seconds
        # Mapping: client_key -> deque of timestamps
        self.records: Dict[str, collections.deque] = collections.defaultdict(collections.deque)

    def _get_client_key(self, request: Request) -> str:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            return f"auth:{auth[7:]}"
        client_host = request.client.host if request.client else "unknown"

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        # Exempt health, metrics, documentation
        if any(path.startswith(prefix) for prefix in ["/api/v1/health", "/health", "/docs", "/redoc", "/openapi.json"]):
            return await call_next(request)

        # Determine limit based on endpoint sensitivity
        is_auth = "/auth/" in path or "/spending/upload" in path
        limit = self.auth_limit if is_auth else self.default_limit

        client_key = f"{self._get_client_key(request)}:{'auth' if is_auth else 'std'}"
        now = time.time()
        window_start = now - self.window_seconds

        queue = self.records[client_key]
        # Evict timestamps outside the window
        while queue and queue[0] < window_start:
            queue.popleft()

        if len(queue) >= limit:
            cid = getattr(request.state, "correlation_id", "none")
            retry_after = int(self.window_seconds - (now - queue[0])) + 1
            response = build_error_response(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded ({limit} req/{self.window_seconds}s). Please retry after {retry_after} seconds.",
                correlation_id=cid,
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(retry_after)
            return response

        queue.append(now)
        remaining = max(0, limit - len(queue))

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(self.window_seconds)
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces maximum request payload sizes:
    - 15 MB for file upload routes (CSV spending statement)
    - 2 MB for generic JSON payload endpoints
    """

    def __init__(self, app, max_upload_bytes: int = 15 * 1024 * 1024, max_json_bytes: int = 2 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_bytes = max_upload_bytes
        self.max_json_bytes = max_json_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                is_upload = "/spending/upload" in request.url.path
                max_allowed = self.max_upload_bytes if is_upload else self.max_json_bytes

                if length > max_allowed:
                    cid = getattr(request.state, "correlation_id", "none")
                    return build_error_response(
                        status_code=413,
                        code="PAYLOAD_TOO_LARGE",
                        message=f"Request size ({length} bytes) exceeds the maximum allowed limit ({max_allowed} bytes).",
                        correlation_id=cid,
                    )
            except ValueError:
                pass

        return await call_next(request)

