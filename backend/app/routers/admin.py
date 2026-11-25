"""FinEx Common Admin Operations Router.

Provides secure, read-only operational visibility into platform activity,
registered users, paper orders, and backing service health.

Authorization:
- Strictly server-side enforced using `require_owner` dependency.
- Non-owners receive HTTP 403 Forbidden.
- Unauthenticated requests receive HTTP 401 Unauthorized.
- Sensitive credentials, password hashes, OAuth subjects, and private questionnaire
  answers are strictly excluded from all projections.
"""

import math
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import ValidationException
from backend.app.database import get_db
from backend.app.dependencies import get_angel_adapter
from backend.app.domain.user_store import user_store
from backend.app.models.core import User, UserProfile
from backend.app.models.monitoring import ErrorEvent
from backend.app.models.paper_trading import PaperOrder
from backend.app.routers.auth import require_owner
from backend.app.routers.health import check_db_ready
from backend.app.services.error_recorder import prune_if_due, sanitize_error_message
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/admin",
    tags=["Admin Operations"],
    dependencies=[Depends(require_owner)],
)


# =============================================================================
# Response Schemas (Strictly safe projections)
# =============================================================================


class AdminUserItem(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    country: Optional[str] = "IND"
    is_active: bool = True
    email_verified: bool = False
    onboarding_completed: bool = False
    risk_band: Optional[str] = None
    experience_level: Optional[str] = None
    created_at: Optional[str] = None


class AdminUsersResponse(BaseModel):
    users: List[AdminUserItem]
    total: int
    page: int
    limit: int
    total_pages: int


class AdminOrderItem(BaseModel):
    id: str
    user_id: str
    user_email: Optional[str] = None
    symbol: str
    side: str
    order_type: str
    quantity: float
    limit_price: Optional[float] = None
    fill_price: Optional[float] = None
    fee: float = 0.0
    status: str
    rejection_reason: Optional[str] = None
    created_at: Optional[str] = None


class AdminOrdersResponse(BaseModel):
    orders: List[AdminOrderItem]
    total: int
    page: int
    limit: int
    total_pages: int
    overall_total: int = 0
    status_counts: Dict[str, int] = Field(default_factory=dict)
    scope_notice: str = (
        "Persisted paper_orders records only. Client-side disconnects, pre-validation rejections, "
        "or unrecorded failures do not appear as order records."
    )


class AdminOverviewResponse(BaseModel):
    total_users: int = Field(..., description="Total registered platform users")
    verified_users: int = Field(..., description="Users with verified email or identity")
    unverified_users: int = Field(..., description="Users with unverified status")
    onboarding_completed_users: int = Field(..., description="Users that completed risk onboarding")
    total_orders: int = Field(..., description="Total recorded paper orders")
    orders_by_status: Dict[str, int] = Field(..., description="Order counts grouped by recorded status")
    recent_rejected_orders: List[AdminOrderItem] = Field(..., description="Recent rejected orders with safe reasons")
    recent_orders: List[AdminOrderItem] = Field(
        default_factory=list, description="Most recent recorded paper orders across all statuses"
    )
    orders_scope_notice: str = (
        "Counts reflect persisted paper_orders rows only; unpersisted request failures are not counted as orders."
    )


class AdminSystemHealthResponse(BaseModel):
    backend: Dict[str, Any]
    database: Dict[str, Any]
    market_data: Dict[str, Any]
    angel_one: Dict[str, Any]
    email: Dict[str, Any]


class AdminMeResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str = "owner"
    is_active: bool = True
    email_verified: bool = True


class AdminErrorItem(BaseModel):
    id: str
    correlation_id: Optional[str] = None
    endpoint: str
    method: str
    status_code: int
    error_type: str
    category: str
    feature_area: str
    sanitized_message: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None


class AdminErrorsResponse(BaseModel):
    errors: List[AdminErrorItem]
    total: int
    page: int
    limit: int
    total_pages: int
    scope_notice: str = (
        "Observability Scope: Real recorded server-side error events (400, 401, 403, 404, 413, 422, 429, 500, 503). "
        "Execution is bounded by a 250ms ceiling and per-process concurrency limits (max 5 simultaneous writes per worker); during storage degradation, "
        "events are dropped fail-open to protect local worker connection pool capacity. Unmatched routes are anonymized to /unmatched_route. "
        "Retention periodically prunes records older than 30 days or beyond the 5,000-row target. "
        "Does not capture client-side network loss, browser script crashes, or edge proxy drops before reaching the API."
    )


class AdminErrorSummaryResponse(BaseModel):
    total_errors: int
    server_errors_5xx: int
    client_errors_4xx: int
    last_24h_errors: int
    errors_by_category: Dict[str, int]
    errors_by_feature: Dict[str, int]
    scope_notice: str = (
        "Observability Scope: Real server-side recorded error events across 4xx and 5xx status codes with bounded execution timeout. "
        "Under storage degradation, events exceeding per-process concurrency limits or 250ms timeout are dropped fail-open. "
        "Edge drops and client-side browser network disconnects are not captured."
    )


# =============================================================================
# Shared Filter Validation & Date Helpers
# =============================================================================

_SAFE_FILTER_TEXT_RE = re.compile(r"^[A-Za-z0-9 _-]+$")
_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _escape_like_term(raw: str) -> str:
    """Escapes SQL LIKE/ILIKE wildcard characters in user search strings."""
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _validate_filter_token(value: Optional[str], field_name: str) -> Optional[str]:
    """Validates bounded filter tokens against safe alphanumeric/separator characters."""
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        return None
    if not _SAFE_FILTER_TEXT_RE.match(clean):
        raise ValidationException(
            f"Invalid {field_name} filter value. Only letters, numbers, spaces, underscores, and hyphens are allowed."
        )
    return clean


def _parse_filter_timestamp(raw_value: Optional[str], *, end_of_day: bool, field_name: str) -> Optional[datetime]:
    """Parses YYYY-MM-DD or ISO-8601 date/time filter boundaries into UTC datetimes."""
    if raw_value is None:
        return None
    clean = raw_value.strip()
    if not clean:
        return None

    if _DATE_ONLY_RE.match(clean):
        try:
            parsed_date = date.fromisoformat(clean)
        except ValueError as exc:
            raise ValidationException(f"Invalid {field_name} date. Expected YYYY-MM-DD.") from exc
        if end_of_day:
            return datetime(
                parsed_date.year, parsed_date.month, parsed_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc
            )
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day, 0, 0, 0, 0, tzinfo=timezone.utc)

    iso_candidate = clean[:-1] + "+00:00" if clean.endswith("Z") else clean
    try:
        parsed_dt = datetime.fromisoformat(iso_candidate)
    except ValueError as exc:
        raise ValidationException(f"Invalid {field_name} format. Expected YYYY-MM-DD or ISO-8601 datetime.") from exc

    if parsed_dt.tzinfo is None:
        return parsed_dt.replace(tzinfo=timezone.utc)
    return parsed_dt.astimezone(timezone.utc)


def _parse_date_range(
    date_from: Optional[str], date_to: Optional[str]
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parses optional start/end boundaries and enforces chronological order."""
    parsed_from = _parse_filter_timestamp(date_from, end_of_day=False, field_name="date_from")
    parsed_to = _parse_filter_timestamp(date_to, end_of_day=True, field_name="date_to")
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise ValidationException("date_from must not be after date_to.")
    return parsed_from, parsed_to


_ALLOWED_ORDER_SIDES = frozenset({"BUY", "SELL"})
_ALLOWED_ORDER_STATUSES = frozenset({"FILLED", "REJECTED", "PENDING", "CANCELLED"})
_SAFE_ORDER_SYMBOL_RE = re.compile(r"^[A-Za-z0-9._&-]+$")
_ORDER_TRACE_MARKERS = ("traceback", 'file "', "sqlalchemy", "asyncpg", "psycopg", "stack trace")

_ADMIN_ORDER_COLUMNS = (
    PaperOrder.id,
    PaperOrder.user_id,
    PaperOrder.symbol,
    PaperOrder.side,
    PaperOrder.order_type,
    PaperOrder.quantity,
    PaperOrder.limit_price,
    PaperOrder.fill_price,
    PaperOrder.fee,
    PaperOrder.status,
    PaperOrder.rejection_reason,
    PaperOrder.created_at,
)


def _sanitize_admin_order_reason(raw_reason: Optional[str], status_val: Optional[str]) -> Optional[str]:
    """Returns an honest, balance-free, credential-safe failure detail for admin display."""
    clean = (raw_reason or "").strip()
    if not clean:
        return "Failure reason unavailable" if status_val == "REJECTED" else None

    lowered = clean.lower()
    if any(marker in lowered for marker in _ORDER_TRACE_MARKERS):
        return "Failure details withheld for safety"

    # Protect private cash balances, share holding quantities, and personal budget caps
    if "insufficient virtual cash" in lowered or "available: ₹" in lowered or "available: rs" in lowered:
        return "Insufficient virtual cash balance for requested order."
    if "insufficient holding quantity" in lowered or "you hold " in lowered:
        return "Insufficient holding quantity for requested sell order."
    if "exceeds authorized budget limit" in lowered:
        return "Order cost exceeds configured budget guardrail."

    sanitized = sanitize_error_message(clean, max_length=240)
    if "[REDACTED]" in sanitized:
        return "Failure details withheld for safety"
    return sanitized


def _serialize_admin_order(row: Any) -> AdminOrderItem:
    """Projects a PaperOrder database row into a sanitized read-only admin schema without user email PII."""
    return AdminOrderItem(
        id=row.id,
        user_id=row.user_id,
        user_email=None,
        symbol=row.symbol,
        side=row.side,
        order_type=row.order_type,
        quantity=float(row.quantity) if row.quantity is not None else 0.0,
        limit_price=float(row.limit_price) if row.limit_price is not None else None,
        fill_price=float(row.fill_price) if row.fill_price is not None else None,
        fee=float(row.fee) if row.fee is not None else 0.0,
        status=row.status,
        rejection_reason=_sanitize_admin_order_reason(row.rejection_reason, row.status),
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


async def _get_order_status_summary(db: AsyncSession) -> tuple[int, Dict[str, int]]:
    """Computes total persisted paper orders and grouped status counts in a single query."""
    status_counts_res = await db.execute(
        select(PaperOrder.status, func.count(PaperOrder.id)).group_by(PaperOrder.status)
    )
    orders_by_status: Dict[str, int] = {
        row[0]: int(row[1]) for row in status_counts_res.fetchall() if row[0] is not None
    }
    total_orders = sum(orders_by_status.values())
    for st in ("FILLED", "REJECTED", "PENDING", "CANCELLED"):
        orders_by_status.setdefault(st, 0)
    return total_orders, orders_by_status


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/overview",
    summary="Admin Operational Overview",
    description="Returns aggregate counts of users, onboarding progress, orders by status, and recent orders.",
)
async def get_admin_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")

    # 1. User metrics
    total_users_res = await db.execute(select(func.count(User.id)))
    total_users = total_users_res.scalar() or 0

    verified_users_res = await db.execute(
        select(func.count(User.id)).where((User.email_verified.is_(True)) | (User.is_verified.is_(True)))
    )
    verified_users = verified_users_res.scalar() or 0
    unverified_users = max(0, total_users - verified_users)

    onboarded_res = await db.execute(
        select(func.count(UserProfile.id)).where(UserProfile.onboarding_completed.is_(True))
    )
    onboarded_users = onboarded_res.scalar() or 0

    # 2. Paper order metrics (single GROUP BY query)
    total_orders, orders_by_status = await _get_order_status_summary(db)

    # 3. Recent recorded orders across all statuses (single-table, newest first)
    recent_orders_stmt = (
        select(*_ADMIN_ORDER_COLUMNS).order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc()).limit(10)
    )
    recent_order_rows = (await db.execute(recent_orders_stmt)).fetchall()
    recent_orders = [_serialize_admin_order(r) for r in recent_order_rows]

    # 4. Recent rejected orders with sanitized safeguard details
    recent_rejected_stmt = (
        select(*_ADMIN_ORDER_COLUMNS)
        .where(PaperOrder.status == "REJECTED")
        .order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc())
        .limit(10)
    )
    recent_rejected_rows = (await db.execute(recent_rejected_stmt)).fetchall()
    recent_rejected_orders = [_serialize_admin_order(r) for r in recent_rejected_rows]

    overview_data = AdminOverviewResponse(
        total_users=total_users,
        verified_users=verified_users,
        unverified_users=unverified_users,
        onboarding_completed_users=onboarded_users,
        total_orders=total_orders,
        orders_by_status=orders_by_status,
        recent_rejected_orders=recent_rejected_orders,
        recent_orders=recent_orders,
    )
    return create_response_envelope(overview_data.model_dump(), correlation_id=cid)


@router.get(
    "/users",
    summary="Admin User Directory",
    description="Paginated and searchable directory of registered users with safe public projections.",
)
async def list_admin_users(
    request: Request,
    page: int = Query(1, ge=1, le=10000, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=120, description="Search by name or email"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    email_verified: Optional[bool] = Query(None, description="Filter by verified email status"),
    onboarding_completed: Optional[bool] = Query(None, description="Filter by onboarding status"),
    date_from: Optional[str] = Query(
        None, max_length=40, description="Include users registered at or after date/datetime"
    ),
    date_to: Optional[str] = Query(
        None, max_length=40, description="Include users registered at or before date/datetime"
    ),
    sort_order: Literal["desc", "asc"] = Query(
        "desc", description="Sort order by registration date (desc = newest first)"
    ),
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")

    parsed_from, parsed_to = _parse_date_range(date_from, date_to)

    query = select(
        User.id,
        User.email,
        User.is_active,
        User.email_verified,
        User.is_verified,
        User.created_at,
        UserProfile.full_name,
        UserProfile.display_name,
        UserProfile.country,
        UserProfile.experience_level,
        UserProfile.onboarding_completed,
        UserProfile.risk_band,
    ).outerjoin(UserProfile, User.id == UserProfile.user_id)

    if search and search.strip():
        escaped = _escape_like_term(search.strip())
        term = f"%{escaped}%"
        query = query.where(
            or_(
                User.email.ilike(term, escape="\\"),
                UserProfile.display_name.ilike(term, escape="\\"),
                UserProfile.full_name.ilike(term, escape="\\"),
            )
        )

    if is_active is not None:
        query = query.where(User.is_active.is_(is_active))

    if email_verified is not None:
        if email_verified:
            query = query.where((User.email_verified.is_(True)) | (User.is_verified.is_(True)))
        else:
            query = query.where(
                (User.email_verified.is_(False) | User.email_verified.is_(None))
                & (User.is_verified.is_(False) | User.is_verified.is_(None))
            )

    if onboarding_completed is not None:
        if onboarding_completed:
            query = query.where(UserProfile.onboarding_completed.is_(True))
        else:
            query = query.where(
                UserProfile.onboarding_completed.is_(False) | UserProfile.onboarding_completed.is_(None)
            )

    if parsed_from is not None:
        query = query.where(User.created_at >= parsed_from)

    if parsed_to is not None:
        query = query.where(User.created_at <= parsed_to)

    # Count matching records
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order deterministically (default: newest registered first)
    if sort_order == "asc":
        query = query.order_by(User.created_at.asc(), User.id.asc())
    else:
        query = query.order_by(User.created_at.desc(), User.id.desc())

    query = query.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(query)).fetchall()

    user_items: List[AdminUserItem] = []
    for r in rows:
        user_items.append(
            AdminUserItem(
                id=r.id,
                email=r.email,
                display_name=r.display_name or (r.full_name.split(" ")[0] if r.full_name else None),
                full_name=r.full_name,
                country=r.country or "IND",
                is_active=bool(r.is_active),
                email_verified=bool(r.email_verified or r.is_verified),
                onboarding_completed=bool(r.onboarding_completed),
                risk_band=r.risk_band,
                experience_level=r.experience_level or "BEGINNER",
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )

    total_pages = max(1, math.ceil(total_count / limit))
    response_data = AdminUsersResponse(
        users=user_items,
        total=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )
    return create_response_envelope(response_data.model_dump(), correlation_id=cid)


@router.get(
    "/orders",
    summary="Admin Paper Trading Orders",
    description="Paginated and filterable paper trading order records across all platform accounts.",
)
async def list_admin_orders(
    request: Request,
    page: int = Query(1, ge=1, le=1000, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    symbol: Optional[str] = Query(None, max_length=20, description="Filter by exact ticker symbol"),
    side: Optional[str] = Query(None, max_length=10, description="Filter by BUY or SELL side"),
    status: Optional[str] = Query(
        None,
        max_length=20,
        description="Filter by recorded order status (FILLED, REJECTED, PENDING, CANCELLED)",
    ),
    date_from: Optional[str] = Query(
        None, max_length=40, description="Include orders created at or after date/datetime"
    ),
    date_to: Optional[str] = Query(
        None, max_length=40, description="Include orders created at or before date/datetime"
    ),
    sort_order: Literal["desc", "asc"] = Query(
        "desc", description="Sort order by creation timestamp (desc = newest first)"
    ),
    search: Optional[str] = Query(None, max_length=80, description="Search by ticker symbol or order ID"),
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")

    parsed_from, parsed_to = _parse_date_range(date_from, date_to)

    clean_symbol: Optional[str] = None
    if symbol is not None and symbol.strip():
        candidate_sym = symbol.strip().upper()
        if not _SAFE_ORDER_SYMBOL_RE.match(candidate_sym):
            raise ValidationException("Invalid symbol filter value.")
        clean_symbol = candidate_sym

    clean_side: Optional[str] = None
    if side is not None and side.strip():
        candidate_side = side.strip().upper()
        if candidate_side not in _ALLOWED_ORDER_SIDES:
            raise ValidationException("Invalid side filter. Expected BUY or SELL.")
        clean_side = candidate_side

    clean_status: Optional[str] = None
    if status is not None and status.strip():
        candidate_status = status.strip().upper()
        if candidate_status not in _ALLOWED_ORDER_STATUSES:
            raise ValidationException("Invalid status filter. Expected one of FILLED, REJECTED, PENDING, or CANCELLED.")
        clean_status = candidate_status

    conditions = []

    if clean_symbol:
        conditions.append(PaperOrder.symbol == clean_symbol)

    if clean_side:
        conditions.append(PaperOrder.side == clean_side)

    if clean_status:
        conditions.append(PaperOrder.status == clean_status)

    if parsed_from is not None:
        conditions.append(PaperOrder.created_at >= parsed_from)

    if parsed_to is not None:
        conditions.append(PaperOrder.created_at <= parsed_to)

    if search and search.strip():
        escaped = _escape_like_term(search.strip())
        term = f"%{escaped}%"
        conditions.append(
            or_(
                PaperOrder.symbol.ilike(term, escape="\\"),
                PaperOrder.id.ilike(term, escape="\\"),
            )
        )

    # Single-table COUNT without User join or redundant subquery wrapper
    count_stmt = select(func.count(PaperOrder.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Platform status distribution (single GROUP BY query for Overview metrics)
    overall_total, status_counts = await _get_order_status_summary(db)

    query = select(*_ADMIN_ORDER_COLUMNS)
    if conditions:
        query = query.where(*conditions)

    if sort_order == "asc":
        query = query.order_by(PaperOrder.created_at.asc(), PaperOrder.id.asc())
    else:
        query = query.order_by(PaperOrder.created_at.desc(), PaperOrder.id.desc())

    query = query.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(query)).fetchall()
    order_items = [_serialize_admin_order(r) for r in rows]

    total_pages = max(1, math.ceil(total_count / limit))
    response_data = AdminOrdersResponse(
        orders=order_items,
        total=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
        overall_total=overall_total,
        status_counts=status_counts,
    )
    return create_response_envelope(response_data.model_dump(), correlation_id=cid)


@router.get(
    "/system-health",
    summary="Admin System & Integration Diagnostics",
    description="Reports backend process, database connectivity, market feed mode, and integration states.",
)
async def get_admin_system_health(request: Request):
    cid = getattr(request.state, "correlation_id", "none")
    settings = get_settings()

    # 1. Database readiness
    try:
        import asyncio

        db_status = await asyncio.wait_for(check_db_ready(), timeout=5.0)
    except asyncio.TimeoutError:
        db_status = {"status": "down", "error": "Database health check timed out after 5.0s"}
    except Exception as e:
        db_status = {"status": "down", "error": f"{type(e).__name__}: Database check failed"}

    # 2. Market feed diagnostics
    try:
        angel = get_angel_adapter()
        angel_diag = angel.get_configuration_status()
        angel_diag["verification_note"] = (
            "Configuration reflects present environment credentials. "
            "It does not prove that live market data or exchange streaming is working."
        )
    except Exception as e:
        angel_diag = {
            "is_configured": False,
            "error": str(e),
            "status": "unavailable",
            "verification_note": (
                "Configuration reflects present environment credentials. "
                "It does not prove that live market data or exchange streaming is working."
            ),
        }

    # 3. Email diagnostics
    smtp_configured = bool(getattr(settings, "SMTP_HOST", None))
    email_diag = {
        "is_configured": smtp_configured,
        "host": settings.SMTP_HOST if smtp_configured else "Unavailable / Not configured",
        "port": getattr(settings, "SMTP_PORT", 587) if smtp_configured else None,
        "use_tls": getattr(settings, "SMTP_USE_TLS", True) if smtp_configured else None,
        "from_email": getattr(settings, "EMAILS_FROM_EMAIL", "noreply@finexai.tech"),
        "verification_note": (
            "SMTP host configuration detected. It does not prove that email delivery to recipient inboxes is working."
        ),
    }

    # 4. Market configuration
    market_data_diag = {
        "mode": getattr(settings, "MARKET_DATA_MODE", "SIMULATED"),
        "allow_fixtures": bool(getattr(settings, "MARKET_ALLOW_FIXTURES", False)),
        "enable_demo_simulation": bool(getattr(settings, "ENABLE_DEMO_SIMULATION", False)),
    }

    # 5. Backend process
    backend_diag = {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT.value
        if hasattr(settings.ENVIRONMENT, "value")
        else str(settings.ENVIRONMENT),
        "version": "v1.2.2-database-online",
    }

    response_data = AdminSystemHealthResponse(
        backend=backend_diag,
        database=db_status,
        market_data=market_data_diag,
        angel_one=angel_diag,
        email=email_diag,
    )
    return create_response_envelope(response_data.model_dump(), correlation_id=cid)


@router.get(
    "/me",
    summary="Admin Current Identity",
    description="Returns authenticated owner profile and permissions.",
)
async def get_admin_me(
    request: Request,
    current_user: dict = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")
    uid = current_user.get("sub")
    user = await user_store.get_user_by_id_db(uid, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Owner user not found.")

    me_data = AdminMeResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.name or "Platform Owner",
        role="owner",
        is_active=user.is_active,
        email_verified=bool(user.email_verified or user.is_verified),
    )
    return create_response_envelope(me_data.model_dump(), correlation_id=cid)


@router.get(
    "/errors",
    summary="Admin Error Monitoring Log",
    description="Paginated, searchable directory of real recorded server-side operational error events.",
)
async def get_admin_errors(
    request: Request,
    page: int = Query(1, ge=1, le=10000, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status_code: Optional[int] = Query(None, ge=100, le=599, description="Filter by exact HTTP status code"),
    category: Optional[str] = Query(
        None, max_length=50, description="Filter by category (e.g. SERVER_ERROR, VALIDATION)"
    ),
    feature_area: Optional[str] = Query(
        None, max_length=50, description="Filter by feature area (e.g. Auth, Market Data)"
    ),
    date_from: Optional[str] = Query(None, max_length=40, description="Include events at or after date/datetime"),
    date_to: Optional[str] = Query(None, max_length=40, description="Include events at or before date/datetime"),
    sort_order: Literal["desc", "asc"] = Query("desc", description="Sort order by created_at (desc = newest first)"),
    search: Optional[str] = Query(
        None,
        max_length=120,
        description="Search correlation ID, endpoint, category, feature area, error type, or sanitized message",
    ),
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")

    clean_category = _validate_filter_token(category, "category")
    clean_feature = _validate_filter_token(feature_area, "feature_area")
    parsed_from, parsed_to = _parse_date_range(date_from, date_to)

    # Opportunistically execute retention pruning if interval has elapsed
    await prune_if_due(session=db)

    query = select(ErrorEvent)

    if status_code is not None:
        query = query.where(ErrorEvent.status_code == status_code)

    if clean_category:
        query = query.where(ErrorEvent.category == clean_category.upper())

    if clean_feature:
        query = query.where(func.lower(ErrorEvent.feature_area) == clean_feature.lower())

    if parsed_from is not None:
        query = query.where(ErrorEvent.created_at >= parsed_from)

    if parsed_to is not None:
        query = query.where(ErrorEvent.created_at <= parsed_to)

    if search and search.strip():
        escaped = _escape_like_term(search.strip())
        term = f"%{escaped}%"
        query = query.where(
            or_(
                ErrorEvent.correlation_id.ilike(term, escape="\\"),
                ErrorEvent.endpoint.ilike(term, escape="\\"),
                ErrorEvent.category.ilike(term, escape="\\"),
                ErrorEvent.feature_area.ilike(term, escape="\\"),
                ErrorEvent.error_type.ilike(term, escape="\\"),
                ErrorEvent.sanitized_message.ilike(term, escape="\\"),
            )
        )

    # Count matching records
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order deterministically (default: latest errors first)
    if sort_order == "asc":
        query = query.order_by(ErrorEvent.created_at.asc(), ErrorEvent.id.asc())
    else:
        query = query.order_by(ErrorEvent.created_at.desc(), ErrorEvent.id.desc())

    query = query.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(query)).scalars().all()

    items = [
        AdminErrorItem(
            id=r.id,
            correlation_id=r.correlation_id,
            endpoint=r.endpoint,
            method=r.method,
            status_code=r.status_code,
            error_type=r.error_type,
            category=r.category,
            feature_area=r.feature_area,
            sanitized_message=r.sanitized_message,
            user_id=r.user_id,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]

    total_pages = max(1, math.ceil(total_count / limit))
    response_data = AdminErrorsResponse(
        errors=items,
        total=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )
    return create_response_envelope(response_data.model_dump(), correlation_id=cid)


@router.get(
    "/errors/summary",
    summary="Admin Error Monitoring Summary Statistics",
    description="Aggregate counts of server errors, client errors, recent 24h events, and category breakdown.",
)
async def get_admin_errors_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    total_errors = (await db.execute(select(func.count(ErrorEvent.id)))).scalar() or 0
    server_errors_5xx = (
        await db.execute(select(func.count(ErrorEvent.id)).where(ErrorEvent.status_code >= 500))
    ).scalar() or 0
    client_errors_4xx = (
        await db.execute(
            select(func.count(ErrorEvent.id)).where((ErrorEvent.status_code >= 400) & (ErrorEvent.status_code < 500))
        )
    ).scalar() or 0
    recent_24h_errors = (
        await db.execute(select(func.count(ErrorEvent.id)).where(ErrorEvent.created_at >= day_ago))
    ).scalar() or 0

    cat_rows = (
        await db.execute(select(ErrorEvent.category, func.count(ErrorEvent.id)).group_by(ErrorEvent.category))
    ).fetchall()
    errors_by_category = {r[0]: int(r[1]) for r in cat_rows if r[0]}

    feat_rows = (
        await db.execute(select(ErrorEvent.feature_area, func.count(ErrorEvent.id)).group_by(ErrorEvent.feature_area))
    ).fetchall()
    errors_by_feature = {r[0]: int(r[1]) for r in feat_rows if r[0]}

    summary_data = AdminErrorSummaryResponse(
        total_errors=total_errors,
        server_errors_5xx=server_errors_5xx,
        client_errors_4xx=client_errors_4xx,
        last_24h_errors=recent_24h_errors,
        errors_by_category=errors_by_category,
        errors_by_feature=errors_by_feature,
    )
    return create_response_envelope(summary_data.model_dump(), correlation_id=cid)
