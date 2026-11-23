"""Durable, Bounded Operational Error Recorder and Server-Side Sanitizer.

Provides safe, bounded, asynchronous error recording for the FinEx platform.
Guarantees:
1. Strict Timeout & Resource Bounds: Database writes are bounded by a 250ms timeout.
   Recording failures or slow storage NEVER block, hang, or delay normal HTTP requests.
2. Allowlisted Error Codes & Generic Messages: Arbitrary exception text and raw traces
   are replaced with safe, allowlisted codes and standardized messages.
3. Route Template Tracking: Records route templates (e.g. /users/{user_id}) instead of
   raw URL paths that might embed sensitive tokens, IDs, or parameters.
4. Validated Metadata: Correlation IDs, user IDs, and HTTP methods are strictly bounded
   and validated before persistence.
5. Recursion Protection: ContextVar guards prevent re-entrant recording calls.
6. Concurrency-Safe Pruning: Background retention pruning is guarded by an asyncio Lock
   and throttled to prevent database overload under high concurrency.
"""

import asyncio
import contextvars
import logging
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, FrozenSet, Optional, Tuple

from backend.app.database import AsyncSessionLocal
from backend.app.models.monitoring import ErrorEvent
from fastapi import Request
from sqlalchemy import delete, func, select

logger = logging.getLogger("finex.error_recorder")

# Resource & Timeout Bounds
MAX_STORED_ERRORS = 5000
RETENTION_DAYS = 30
RECORDING_TIMEOUT_SECONDS = 0.25  # 250ms hard limit for request-path logging
PRUNE_TIMEOUT_SECONDS = 1.0  # 1s hard limit for background maintenance pruning
PRUNE_THROTTLE_SECONDS = 300  # Prune at most once per 5 minutes under load

# Recursion guard to prevent infinite re-entrant recording loops
_is_recording_ctx: contextvars.ContextVar[bool] = contextvars.ContextVar("_is_recording_ctx", default=False)

# Concurrency lock and timestamp for storage pruning
_prune_lock = asyncio.Lock()
_last_prune_timestamp: float = 0.0

ALLOWLISTED_METHODS: FrozenSet[str] = frozenset({"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"})

# =============================================================================
# 1. Allowlisted Error Codes & Safe Generic Message Catalog
# =============================================================================

# Catalog mapping: error_code -> (category, safe_generic_message, default_feature_area)
ERROR_CATALOG: Dict[str, Tuple[str, str, str]] = {
    # 5xx Server Errors
    "INTERNAL_SERVER_ERROR": (
        "SERVER_ERROR",
        "An unexpected server error occurred.",
        "System",
    ),
    "DATABASE_ERROR": (
        "DATABASE",
        "Database operation failed or timed out.",
        "System",
    ),
    "UPSTREAM_API_ERROR": (
        "UPSTREAM_API",
        "Upstream market data or service dependency is unavailable.",
        "Market Data",
    ),
    "CIRCUIT_BREAKER_OPEN": (
        "UPSTREAM_API",
        "Market data circuit breaker is open. Fallback active.",
        "Market Data",
    ),
    "SERVICE_UNAVAILABLE": (
        "UPSTREAM_API",
        "Upstream service temporarily unavailable.",
        "System",
    ),
    "TIMEOUT_ERROR": (
        "SERVER_ERROR",
        "Operation timed out before completion.",
        "System",
    ),
    # 4xx Client / Security / Rate Limit Errors
    "RATE_LIMIT_EXCEEDED": (
        "RATE_LIMIT",
        "API rate limit exceeded. Request throttled.",
        "System",
    ),
    "VALIDATION_ERROR": (
        "VALIDATION",
        "Request payload failed validation schema.",
        "System",
    ),
    "AUTHENTICATION_REQUIRED": (
        "AUTHENTICATION",
        "Authentication required or credentials expired.",
        "Auth",
    ),
    "UNAUTHORIZED": (
        "AUTHENTICATION",
        "Authentication required or credentials expired.",
        "Auth",
    ),
    "PERMISSION_DENIED": (
        "AUTHENTICATION",
        "Administrative access restricted to platform owner.",
        "Auth",
    ),
    "FORBIDDEN": (
        "AUTHENTICATION",
        "Administrative access restricted to platform owner.",
        "Auth",
    ),
    "RESOURCE_NOT_FOUND": (
        "NOT_FOUND",
        "The requested resource was not found.",
        "System",
    ),
    "CONFLICT": (
        "CONFLICT",
        "Resource state conflict detected.",
        "System",
    ),
    "BAD_REQUEST": (
        "CLIENT_ERROR",
        "Malformed request syntax or parameters.",
        "System",
    ),
    "HTTP_EXCEPTION": (
        "CLIENT_ERROR",
        "Client HTTP request failed validation.",
        "System",
    ),
    "PAYLOAD_TOO_LARGE": (
        "CLIENT_ERROR",
        "Request payload size exceeds maximum allowed limit.",
        "System",
    ),
    # FinEx Domain-Specific Errors
    "ORDER_REJECTED": (
        "CLIENT_ERROR",
        "Paper order execution was rejected by safeguard checks.",
        "Paper Trading",
    ),
    "INSUFFICIENT_FUNDS": (
        "CLIENT_ERROR",
        "Insufficient cash balance for simulated execution.",
        "Paper Trading",
    ),
    "MARKET_FEED_DISCONNECTED": (
        "UPSTREAM_API",
        "Market data stream is temporarily disconnected.",
        "Market Data",
    ),
}

# Defense-in-depth sanitization patterns for residual messages
REDACTION_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    # Email addresses
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    # Bearer tokens
    (
        re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
        "Bearer [REDACTED_TOKEN]",
    ),
    # JWT tokens
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "[REDACTED_JWT]",
    ),
    # Common secret/credential key-value pairs
    (
        re.compile(
            r'(?i)(["\']?(?:password|passwd|secret_key|secret|api_key|token|auth_token|access_token|private_key|totp)["\']?\s*[:=]\s*["\']?)([^"\'\s,;}{]+)(["\']?)'
        ),
        r"\1[REDACTED]\3",
    ),
    # Credit card / 16-digit PAN numbers
    (
        re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
        "[REDACTED_CARD]",
    ),
    # Local Windows & Unix file system paths
    (
        re.compile(r"(?:[A-Za-z]:\\[\w\s.\\-]+|[/\\](?:home|Users|var|opt|tmp|app)[\w\s./\\-]+)"),
        "[REDACTED_PATH]",
    ),
)


# =============================================================================
# 2. Metadata Sanitizers & Route Template Extractors
# =============================================================================


def sanitize_correlation_id(cid: Optional[str]) -> str:
    """Validates and bounds correlation IDs to alphanumeric and safe delimiter chars."""
    if not cid:
        return uuid.uuid4().hex
    clean = str(cid).strip()
    if len(clean) <= 64 and re.match(r"^[a-zA-Z0-9_\-\.:]{1,64}$", clean):
        return clean
    return uuid.uuid4().hex


def sanitize_user_id(uid: Optional[str]) -> Optional[str]:
    """Validates and bounds user IDs to prevent injection or leaking arbitrary structures."""
    if not uid:
        return None
    clean = str(uid).strip()
    if len(clean) <= 64 and re.match(r"^[a-zA-Z0-9_\-]{1,64}$", clean):
        return clean
    return None


def sanitize_method(method: Optional[str]) -> str:
    """Restricts HTTP method to known allowlisted verbs."""
    if not method:
        return "UNKNOWN"
    m = str(method).strip().upper()
    return m if m in ALLOWLISTED_METHODS else "UNKNOWN"


def extract_route_template(request: Optional[Request], fallback_path: Optional[str] = None) -> str:
    """Extracts the route template (e.g. /users/{user_id}) instead of raw paths with IDs."""
    if request is not None:
        try:
            # 1. Starlette stores matched route pattern in scope['route']
            route = request.scope.get("route")
            if route and hasattr(route, "path") and route.path:
                return str(route.path)[:255]
        except Exception:
            pass

        raw_path = request.url.path or "unknown"
    else:
        raw_path = fallback_path or "unknown"

    # 2. Scrub sensitive parameters from raw path if no template was resolved
    clean_path = raw_path
    # Scrub UUIDs
    clean_path = re.sub(
        r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "/{uuid}",
        clean_path,
    )
    # Scrub FinEx entity IDs (usr-, ord-, acc-, tx-, sec-, tok-)
    clean_path = re.sub(
        r"/(?:usr|ord|acc|tx|sec|tok)-[a-zA-Z0-9_\-]+",
        "/{id}",
        clean_path,
    )
    # Scrub raw integer IDs
    clean_path = re.sub(r"/\d+(?=/|$)", "/{id}", clean_path)
    # Scrub reset tokens / long hex or base64 hashes
    clean_path = re.sub(r"/[a-zA-Z0-9_\-]{24,}", "/{token}", clean_path)

    return clean_path[:255]


def sanitize_error_message(message: Any, max_length: int = 500) -> str:
    """Sanitizes an exception or error message string server-side."""
    if message is None:
        return "Unknown error details"

    text = str(message).strip()
    if not text:
        return "Empty error message"

    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)

    if len(text) > max_length:
        text = text[:max_length] + " [TRUNCATED]"

    return text


def resolve_feature_area(path: str) -> str:
    """Determines feature area safely from clean path or route template."""
    clean_path = path.lower()
    if "/auth" in clean_path or "/users" in clean_path:
        return "Auth"
    elif "/market" in clean_path:
        return "Market Data"
    elif "/charts" in clean_path:
        return "Charts"
    elif "/paper" in clean_path or "/orders" in clean_path:
        return "Paper Trading"
    elif "/portfolio" in clean_path:
        return "Portfolio"
    elif "/ai" in clean_path or "/gemini" in clean_path or "/chat" in clean_path:
        return "AI Assistant"
    elif "/risk" in clean_path:
        return "Risk Assessment"
    elif "/spending" in clean_path:
        return "Spending"
    elif "/goals" in clean_path:
        return "Goals"
    elif "/admin" in clean_path:
        return "Admin"
    elif "/health" in clean_path:
        return "Health"
    return "System"


def resolve_safe_error_details(
    status_code: int,
    exc: Optional[Exception] = None,
    error_code: Optional[str] = None,
    raw_message: Optional[str] = None,
    endpoint: str = "",
) -> Tuple[str, str, str, str]:
    """Resolves allowlisted error code, category, safe generic message, and feature area.

    Returns:
        (resolved_code, category, safe_message, feature_area)
    """
    feature_area = resolve_feature_area(endpoint)
    exc_type_name = type(exc).__name__ if exc else ""
    exc_str = (str(exc).lower() if exc else "") + (" " + raw_message.lower() if raw_message else "")

    # 1. Check if error_code is in catalog
    if error_code and error_code in ERROR_CATALOG:
        cat, msg, default_feat = ERROR_CATALOG[error_code]
        return error_code, cat, msg, feature_area or default_feat

    # 2. Check for database errors
    if (
        "database" in exc_str
        or "sql" in exc_str
        or "asyncpg" in exc_str
        or "postgres" in exc_str
        or "psycopg" in exc_str
        or "operationalerror" in exc_type_name.lower()
    ):
        return (
            "DATABASE_ERROR",
            "DATABASE",
            "Database operation failed or timed out.",
            feature_area,
        )

    # 3. Check for upstream API errors
    if "angel" in exc_str or "smartapi" in exc_str or "smtp" in exc_str or "upstream" in exc_str:
        return (
            "UPSTREAM_API_ERROR",
            "UPSTREAM_API",
            "Upstream market data or service dependency is unavailable.",
            feature_area or "Market Data",
        )

    # 4. Map by HTTP Status Code
    if status_code >= 500:
        return (
            "INTERNAL_SERVER_ERROR",
            "SERVER_ERROR",
            "An unexpected server error occurred.",
            feature_area,
        )
    elif status_code == 422 or "validation" in exc_type_name.lower():
        return (
            "VALIDATION_ERROR",
            "VALIDATION",
            "Request payload failed validation schema.",
            feature_area,
        )
    elif status_code == 429 or "ratelimit" in exc_type_name.lower():
        return (
            "RATE_LIMIT_EXCEEDED",
            "RATE_LIMIT",
            "API rate limit exceeded. Request throttled.",
            feature_area,
        )
    elif status_code in (401, 403):
        code = "PERMISSION_DENIED" if status_code == 403 else "AUTHENTICATION_REQUIRED"
        msg = (
            "Administrative access restricted to platform owner."
            if status_code == 403
            else "Authentication required or credentials expired."
        )
        return code, "AUTHENTICATION", msg, feature_area
    elif status_code == 409:
        return "CONFLICT", "CONFLICT", "Resource state conflict detected.", feature_area
    elif status_code == 404:
        return (
            "RESOURCE_NOT_FOUND",
            "NOT_FOUND",
            "The requested resource was not found.",
            feature_area,
        )
    elif status_code == 413:
        return (
            "PAYLOAD_TOO_LARGE",
            "CLIENT_ERROR",
            "Request payload size exceeds maximum allowed limit.",
            feature_area,
        )
    else:
        return (
            "BAD_REQUEST",
            "CLIENT_ERROR",
            "Malformed request syntax or parameters.",
            feature_area,
        )


def categorize_error(
    status_code: int,
    exc: Optional[Exception] = None,
    path: str = "",
    message: Optional[str] = None,
) -> Tuple[str, str]:
    """Compatibility helper returning (category, feature_area)."""
    _, category, _, feature_area = resolve_safe_error_details(
        status_code=status_code, exc=exc, raw_message=message, endpoint=path
    )
    return category, feature_area


# =============================================================================
# 3. Concurrency-Safe Bounded Storage Pruning
# =============================================================================


async def prune_bounded_storage(session: Optional[Any] = None) -> None:
    """Enforces bounded retention under concurrency lock.

    Deletes events older than RETENTION_DAYS and keeps total events <= MAX_STORED_ERRORS.
    All exceptions are swallowed to prevent maintenance failures from disrupting services.
    """
    global _last_prune_timestamp

    # Concurrency guard: if another prune is already running, skip cleanly
    if _prune_lock.locked():
        return

    async with _prune_lock:
        try:
            if session is None:
                async with AsyncSessionLocal() as standalone_session:
                    await _execute_prune(standalone_session)
                    await standalone_session.commit()
            else:
                await _execute_prune(session)

            _last_prune_timestamp = time.monotonic()
        except Exception as prune_err:
            logger.debug(f"ErrorRecorder: Bounded retention pruning notice (non-fatal): {prune_err}")


async def _execute_prune(session: Any) -> None:
    """Internal pruning execution bounded by query timeout."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    await session.execute(delete(ErrorEvent).where(ErrorEvent.created_at < cutoff))

    count_res = await session.execute(select(func.count(ErrorEvent.id)))
    total_count = count_res.scalar() or 0

    if total_count > MAX_STORED_ERRORS:
        overflow = total_count - MAX_STORED_ERRORS
        subq = select(ErrorEvent.id).order_by(ErrorEvent.created_at.asc()).limit(overflow)
        old_ids_res = await session.execute(subq)
        old_ids = [r[0] for r in old_ids_res.fetchall()]
        if old_ids:
            await session.execute(delete(ErrorEvent).where(ErrorEvent.id.in_(old_ids)))


# =============================================================================
# 4. Safe Asynchronous Error Event Recording
# =============================================================================


async def _persist_error_event(
    correlation_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    error_type: str,
    category: str,
    feature_area: str,
    sanitized_message: str,
    user_id: Optional[str],
) -> Optional[ErrorEvent]:
    """Persists error record in an isolated session with minimal lock time."""
    error_event = ErrorEvent(
        correlation_id=correlation_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        error_type=error_type,
        category=category,
        feature_area=feature_area,
        sanitized_message=sanitized_message,
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
    )

    async with AsyncSessionLocal() as session:
        session.add(error_event)
        await session.commit()
        await session.refresh(error_event)

    return error_event


async def record_error_event(
    request: Optional[Request] = None,
    exc: Optional[Exception] = None,
    status_code: int = 500,
    message: Optional[str] = None,
    raw_message: Optional[str] = None,
    correlation_id: Optional[str] = None,
    category: Optional[str] = None,
    feature_area: Optional[str] = None,
    endpoint: Optional[str] = None,
    method: Optional[str] = None,
    user_id: Optional[str] = None,
    error_type: Optional[str] = None,
    error_code: Optional[str] = None,
) -> Optional[ErrorEvent]:
    """Safely records an operational error event to database storage.

    FAIL-SAFE & BOUNDED GUARANTEES:
    1. Hard Timeout: Bounded by RECORDING_TIMEOUT_SECONDS (250ms). Unresponsive DB
       will never hang incoming user requests.
    2. Recursion Safe: Re-entrant calls within the same context return None immediately.
    3. Safe Code & Message: Unvetted exception traces are never persisted.
    4. Route Templates: Path parameters and tokens are stripped from recorded endpoints.
    5. No Request-Path Pruning: Pruning is decoupled and executed conditionally.
    """
    # Recursion guard
    if _is_recording_ctx.get():
        return None

    token = _is_recording_ctx.set(True)
    try:
        # 1. Resolve and bound metadata
        cid_raw = correlation_id
        if request is not None and not cid_raw:
            cid_raw = getattr(request.state, "correlation_id", None)
        resolved_cid = sanitize_correlation_id(cid_raw)

        resolved_method = sanitize_method(method or (request.method if request else None))
        resolved_endpoint = extract_route_template(request, fallback_path=endpoint)

        resolved_uid = sanitize_user_id(user_id)
        if request is not None and not resolved_uid:
            try:
                curr_user = getattr(request.state, "user", None)
                if isinstance(curr_user, dict):
                    resolved_uid = sanitize_user_id(curr_user.get("sub") or curr_user.get("user_id"))
            except Exception:
                pass

        # 2. Bounded status code
        safe_status = max(100, min(599, int(status_code)))

        # 3. Resolve error details via Allowlisted Catalog
        resolved_type = error_type or (type(exc).__name__ if exc else "ApiError")
        raw_msg = raw_message if raw_message is not None else message

        resolved_code, auto_category, safe_msg, auto_feature = resolve_safe_error_details(
            status_code=safe_status,
            exc=exc,
            error_code=error_code,
            raw_message=raw_msg,
            endpoint=resolved_endpoint,
        )

        final_category = category or auto_category
        final_feature = feature_area or auto_feature
        final_message = sanitize_error_message(safe_msg)

        # 4. Execute database write bounded by strict timeout
        return await asyncio.wait_for(
            _persist_error_event(
                correlation_id=resolved_cid,
                endpoint=resolved_endpoint,
                method=resolved_method,
                status_code=safe_status,
                error_type=resolved_type[:100],
                category=final_category[:50],
                feature_area=final_feature[:50],
                sanitized_message=final_message,
                user_id=resolved_uid,
            ),
            timeout=RECORDING_TIMEOUT_SECONDS,
        )

    except asyncio.TimeoutError:
        logger.warning(
            f"ErrorRecorder: Bounded database write timed out after {RECORDING_TIMEOUT_SECONDS}s (non-fatal fail-open)"
        )
        return None
    except Exception as exc_err:
        logger.warning(f"ErrorRecorder: Fail-safe intercepted error event recording failure (non-fatal): {exc_err}")
        return None
    finally:
        _is_recording_ctx.reset(token)
