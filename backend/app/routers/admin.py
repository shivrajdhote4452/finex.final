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
from typing import Any, Dict, List, Optional

from backend.app.config import get_settings
from backend.app.core.envelope import create_response_envelope
from backend.app.database import get_db
from backend.app.dependencies import get_angel_adapter
from backend.app.domain.user_store import user_store
from backend.app.models.core import User, UserProfile
from backend.app.models.paper_trading import PaperOrder
from backend.app.routers.auth import require_owner
from backend.app.routers.health import check_db_ready
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


class AdminOverviewResponse(BaseModel):
    total_users: int = Field(..., description="Total registered platform users")
    verified_users: int = Field(..., description="Users with verified email or identity")
    unverified_users: int = Field(..., description="Users with unverified status")
    onboarding_completed_users: int = Field(..., description="Users that completed risk onboarding")
    total_orders: int = Field(..., description="Total paper orders submitted")
    orders_by_status: Dict[str, int] = Field(..., description="Order counts grouped by recorded status")
    recent_rejected_orders: List[AdminOrderItem] = Field(..., description="Recent rejected orders with reasons")


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


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/overview",
    summary="Admin Operational Overview",
    description="Returns aggregate counts of users, onboarding progress, orders by status, and recent rejections.",
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

    # 2. Paper order metrics
    total_orders_res = await db.execute(select(func.count(PaperOrder.id)))
    total_orders = total_orders_res.scalar() or 0

    status_counts_res = await db.execute(
        select(PaperOrder.status, func.count(PaperOrder.id)).group_by(PaperOrder.status)
    )
    orders_by_status: Dict[str, int] = {
        row[0]: int(row[1]) for row in status_counts_res.fetchall() if row[0] is not None
    }
    for st in ["FILLED", "REJECTED", "PENDING", "CANCELLED"]:
        orders_by_status.setdefault(st, 0)

    # 3. Recent rejected orders
    recent_rejected_stmt = (
        select(
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
            User.email.label("user_email"),
        )
        .outerjoin(User, PaperOrder.user_id == User.id)
        .where(PaperOrder.status == "REJECTED")
        .order_by(PaperOrder.created_at.desc())
        .limit(10)
    )
    recent_rejected_rows = (await db.execute(recent_rejected_stmt)).fetchall()

    recent_rejected_orders: List[Dict[str, Any]] = []
    for r in recent_rejected_rows:
        recent_rejected_orders.append(
            {
                "id": r.id,
                "user_id": r.user_id,
                "user_email": r.user_email,
                "symbol": r.symbol,
                "side": r.side,
                "order_type": r.order_type,
                "quantity": float(r.quantity) if r.quantity is not None else 0.0,
                "limit_price": float(r.limit_price) if r.limit_price is not None else None,
                "fill_price": float(r.fill_price) if r.fill_price is not None else None,
                "fee": float(r.fee) if r.fee is not None else 0.0,
                "status": r.status,
                "rejection_reason": r.rejection_reason or "Unspecified reason",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )

    overview_data = AdminOverviewResponse(
        total_users=total_users,
        verified_users=verified_users,
        unverified_users=unverified_users,
        onboarding_completed_users=onboarded_users,
        total_orders=total_orders,
        orders_by_status=orders_by_status,
        recent_rejected_orders=[AdminOrderItem(**o) for o in recent_rejected_orders],
    )
    return create_response_envelope(overview_data.model_dump(), correlation_id=cid)


@router.get(
    "/users",
    summary="Admin User Directory",
    description="Paginated and searchable directory of registered users with safe public projections.",
)
async def list_admin_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for email or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    email_verified: Optional[bool] = Query(None, description="Filter by verified email status"),
    onboarding_completed: Optional[bool] = Query(None, description="Filter by onboarding status"),
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")

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
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.email.ilike(term),
                UserProfile.display_name.ilike(term),
                UserProfile.full_name.ilike(term),
                User.id.ilike(term),
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

    # Count matching records
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order
    query = query.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
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
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    symbol: Optional[str] = Query(None, description="Filter by ticker symbol"),
    side: Optional[str] = Query(None, description="Filter by BUY or SELL side"),
    status: Optional[str] = Query(None, description="Filter by order status (FILLED, REJECTED, PENDING, etc.)"),
    search: Optional[str] = Query(None, description="Search symbol, rejection reason, or user email"),
    db: AsyncSession = Depends(get_db),
):
    cid = getattr(request.state, "correlation_id", "none")

    query = select(
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
        User.email.label("user_email"),
    ).outerjoin(User, PaperOrder.user_id == User.id)

    if symbol and symbol.strip():
        query = query.where(PaperOrder.symbol.ilike(f"%{symbol.strip()}%"))

    if side and side.strip():
        query = query.where(PaperOrder.side == side.strip().upper())

    if status and status.strip():
        query = query.where(PaperOrder.status == status.strip().upper())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                PaperOrder.symbol.ilike(term),
                PaperOrder.rejection_reason.ilike(term),
                User.email.ilike(term),
                PaperOrder.id.ilike(term),
            )
        )

    # Count matching records
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Paginate and order
    query = query.order_by(PaperOrder.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(query)).fetchall()

    order_items: List[AdminOrderItem] = []
    for r in rows:
        order_items.append(
            AdminOrderItem(
                id=r.id,
                user_id=r.user_id,
                user_email=r.user_email,
                symbol=r.symbol,
                side=r.side,
                order_type=r.order_type,
                quantity=float(r.quantity) if r.quantity is not None else 0.0,
                limit_price=float(r.limit_price) if r.limit_price is not None else None,
                fill_price=float(r.fill_price) if r.fill_price is not None else None,
                fee=float(r.fee) if r.fee is not None else 0.0,
                status=r.status,
                rejection_reason=r.rejection_reason,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
        )

    total_pages = max(1, math.ceil(total_count / limit))
    response_data = AdminOrdersResponse(
        orders=order_items,
        total=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
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
            "SMTP host configuration detected. "
            "It does not prove that email delivery to recipient inboxes is working."
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
