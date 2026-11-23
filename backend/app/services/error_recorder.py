"""Durable, Bounded Operational Error Recorder and Server-Side Sanitizer.

Provides safe, bounded, asynchronous error recording for the FinEx platform.
Guarantees:
1. Data Sanitization: Strictly redacts emails, tokens, credentials, and local file paths.
2. Safe Failure Handling: Failure to record an error NEVER breaks normal requests or crashes the server.
3. Bounded Retention: Prunes records older than 30 days or beyond the maximum storage ceiling.
4. Read-Only Surveillance: Only produces sanitized operational logs.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple

from backend.app.database import AsyncSessionLocal
from backend.app.models.monitoring import ErrorEvent
from fastapi import Request
from sqlalchemy import delete, func, select

logger = logging.getLogger("finex.error_recorder")

# Storage bounds
MAX_STORED_ERRORS = 5000
RETENTION_DAYS = 30

# Server-Side Redaction Regular Expressions
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
    # Common secret/credential key-value pairs (password=..., "password": "...", token=...)
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


def sanitize_error_message(message: Any, max_length: int = 500) -> str:
    """Sanitizes an exception or error message string server-side.

    Removes all emails, bearer tokens, JWTs, passwords, secrets, card numbers,
    and absolute filesystem paths. Truncates length to avoid memory/storage bloat.
    """
    if message is None:
        return "Unknown error details"

    text = str(message).strip()
    if not text:
        return "Empty error message"

    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)

    # Protect against huge trace dumps / memory blowups
    if len(text) > max_length:
        text = text[:max_length] + " [TRUNCATED]"

    return text


def categorize_error(
    status_code: int,
    exc: Optional[Exception] = None,
    path: str = "",
    message: Optional[str] = None,
) -> Tuple[str, str]:
    """Determines category and feature area based on HTTP status, exception type, path, and message.

    Returns:
        (category, feature_area)
    """
    clean_path = path.lower()

    # Determine Feature Area
    if "/auth" in clean_path or "/users" in clean_path:
        feature_area = "Auth"
    elif "/market" in clean_path:
        feature_area = "Market Data"
    elif "/charts" in clean_path:
        feature_area = "Charts"
    elif "/paper" in clean_path or "/orders" in clean_path:
        feature_area = "Paper Trading"
    elif "/portfolio" in clean_path:
        feature_area = "Portfolio"
    elif "/ai" in clean_path or "/gemini" in clean_path or "/chat" in clean_path:
        feature_area = "AI Assistant"
    elif "/risk" in clean_path:
        feature_area = "Risk Assessment"
    elif "/spending" in clean_path:
        feature_area = "Spending"
    elif "/goals" in clean_path:
        feature_area = "Goals"
    elif "/admin" in clean_path:
        feature_area = "Admin"
    elif "/health" in clean_path:
        feature_area = "Health"
    else:
        feature_area = "System"

    # Determine Category
    exc_type_name = type(exc).__name__ if exc else ""
    exc_str = (str(exc).lower() if exc else "") + (" " + message.lower() if message else "")

    if "database" in exc_str or "sql" in exc_str or "asyncpg" in exc_str or "operationalerror" in exc_type_name.lower():
        category = "DATABASE"
    elif "angel" in exc_str or "smartapi" in exc_str or "smtp" in exc_str or "upstream" in exc_str:
        category = "UPSTREAM_API"
    elif status_code >= 500:
        category = "SERVER_ERROR"
    elif status_code == 422 or "validation" in exc_type_name.lower():
        category = "VALIDATION"
    elif status_code == 429 or "ratelimit" in exc_type_name.lower():
        category = "RATE_LIMIT"
    elif status_code in (401, 403):
        category = "AUTHENTICATION"
    elif status_code == 409:
        category = "CONFLICT"
    elif status_code == 404:
        category = "NOT_FOUND"
    else:
        category = "CLIENT_ERROR"

    return category, feature_area


async def prune_bounded_storage(session: Optional[Any] = None) -> None:
    """Enforces bounded retention: deletes events older than RETENTION_DAYS and keeps max events <= MAX_STORED_ERRORS."""
    if session is None:
        try:
            async with AsyncSessionLocal() as standalone_session:
                await prune_bounded_storage(standalone_session)
                await standalone_session.commit()
        except Exception as prune_err:
            logger.warning(f"ErrorRecorder: Bounded retention pruning warning (non-fatal): {prune_err}")
        return

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
        # Delete old events beyond retention window
        await session.execute(delete(ErrorEvent).where(ErrorEvent.created_at < cutoff))

        # Check total count ceiling
        count_res = await session.execute(select(func.count(ErrorEvent.id)))
        total_count = count_res.scalar() or 0

        if total_count > MAX_STORED_ERRORS:
            # Find timestamp of the N-th newest record
            overflow = total_count - MAX_STORED_ERRORS
            subq = select(ErrorEvent.id).order_by(ErrorEvent.created_at.asc()).limit(overflow)
            old_ids_res = await session.execute(subq)
            old_ids = [r[0] for r in old_ids_res.fetchall()]
            if old_ids:
                await session.execute(delete(ErrorEvent).where(ErrorEvent.id.in_(old_ids)))
    except Exception as prune_err:
        logger.warning(f"ErrorRecorder: Bounded retention pruning warning (non-fatal): {prune_err}")


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
) -> Optional[ErrorEvent]:
    """Safely records an operational error event to database storage.

    FAIL-SAFE:
    All exceptions in this function are caught internally and logged to standard logging.
    This guarantees that failure to write to the error log NEVER breaks or delays the primary request.
    """
    try:
        # 1. Resolve request metadata safely
        resolved_endpoint = endpoint or "unknown"
        resolved_method = method or "UNKNOWN"
        resolved_user_id = user_id
        cid = correlation_id

        if request is not None:
            try:
                # Store route path only (NEVER query string or credentials)
                resolved_endpoint = request.url.path or resolved_endpoint
                resolved_method = request.method or resolved_method
                if not cid:
                    cid = getattr(request.state, "correlation_id", None)
                # User ID (opaque subject only, NEVER email or password)
                current_user = getattr(request.state, "user", None)
                if isinstance(current_user, dict):
                    resolved_user_id = current_user.get("sub") or current_user.get("user_id") or resolved_user_id
            except Exception:
                pass

        if not cid:
            cid = "none"

        # 2. Derive error type & message
        resolved_error_type = error_type or (type(exc).__name__ if exc else "ApiError")
        raw_msg = (
            raw_message
            if raw_message is not None
            else (message if message is not None else (str(exc) if exc else "An unhandled error occurred."))
        )
        sanitized_msg = sanitize_error_message(raw_msg)

        # 3. Categorize
        auto_category, auto_feature = categorize_error(
            status_code=status_code, exc=exc, path=resolved_endpoint, message=raw_msg
        )
        resolved_category = category or auto_category
        resolved_feature = feature_area or auto_feature

        # 4. Construct ErrorEvent
        error_event = ErrorEvent(
            correlation_id=cid,
            endpoint=resolved_endpoint,
            method=resolved_method[:10],
            status_code=status_code,
            error_type=resolved_error_type[:100],
            category=resolved_category[:50],
            feature_area=resolved_feature[:50],
            sanitized_message=sanitized_msg,
            user_id=resolved_user_id,
            created_at=datetime.now(timezone.utc),
        )

        # 5. Persist defensively with isolated session
        async with AsyncSessionLocal() as session:
            session.add(error_event)
            await session.commit()
            await session.refresh(error_event)

            # Periodically prune (lightweight retention enforcement)
            await prune_bounded_storage(session)
            await session.commit()

        return error_event

    except Exception as exc:
        # FAIL-SAFE: Never disrupt the caller if recording fails
        logger.warning(f"ErrorRecorder: Failed to record error event to storage (non-fatal): {exc}")
        return None
