"""Chart Workspace, Drawings, Templates, and Replay Session Router.

Task ID: TradingView-Style Analytical Workspace (Sections 8A-8K)
Exposes:
- GET /charts/layouts: List saved multi-chart layout presets
- POST /charts/layouts: Save or update desktop/mobile layout arrangement
- DELETE /charts/layouts/{id}: Delete layout
- GET /charts/drawings/{symbol}: Fetch drawings anchored to time & price coordinates
- POST /charts/drawings: Create or persist drawing annotation
- DELETE /charts/drawings/{id}: Delete single drawing
- DELETE /charts/drawings/clear/{symbol}: Clear drawings for symbol
- GET /charts/indicator-templates: User's saved indicator combinations
- POST /charts/indicator-templates: Save indicator preset
- GET /charts/replay/session: Fetch active replay session & simulated clock
- POST /charts/replay/session: Initialize or advance historical replay clock
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.core.envelope import create_response_envelope
from backend.app.core.errors import NotFoundException
from backend.app.database import get_db
from backend.app.models.charts import (
    ChartDrawing,
    ChartIndicatorTemplate,
    ChartLayout,
    ReplaySession,
)
from backend.app.routers.auth import get_current_user_id
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/charts", tags=["Chart Workspace & Replay"])


# --- Schemas ---


class SaveLayoutRequest(BaseModel):
    name: str = Field("Default Layout", max_length=100)
    layout_type: str = Field("single", description="single, dual_h, dual_v, quad")
    active_symbols: List[str] = Field(default_factory=lambda: ["RELIANCE"])
    timeframes: List[str] = Field(default_factory=lambda: ["1D"])
    sync_crosshair: bool = True
    sync_time: bool = True
    sync_symbol: bool = False
    is_default: bool = False


class SaveDrawingRequest(BaseModel):
    id: Optional[str] = None
    symbol: str = Field(..., max_length=20)
    drawing_type: str = Field(
        ..., description="trend_line, ray, horizontal_line, vertical_line, rectangle, text_note, fibonacci, ruler"
    )
    coordinates: List[Dict[str, Any]] = Field(..., description="Anchored points with time and price coordinates")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Visual properties (color, lineWidth, text, locked)"
    )
    market: str = "NSE"


class SaveIndicatorTemplateRequest(BaseModel):
    name: str = Field(..., max_length=100)
    indicators_config: List[Dict[str, Any]] = Field(
        ..., description="List of configured indicators and their parameters"
    )
    is_default: bool = False


class ReplaySessionRequest(BaseModel):
    session_name: Optional[str] = "NSE Historical Replay"
    market: str = "NSE"
    simulated_clock: Optional[str] = Field(None, description="ISO timestamp for simulated clock")
    start_date: Optional[str] = "2026-08-01"
    end_date: Optional[str] = "2026-10-16"
    speed_multiplier: Optional[float] = 1.00
    status: Optional[str] = "ACTIVE"


# --- Layout Endpoints ---


@router.get("/layouts")
async def list_chart_layouts(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch saved chart layouts for authenticated user."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = select(ChartLayout).where(ChartLayout.user_id == user_id).order_by(desc(ChartLayout.updated_at))
    res = await db.execute(stmt)
    layouts = res.scalars().all()

    return create_response_envelope(
        data={
            "layouts": [
                {
                    "id": lay.id,
                    "name": lay.name,
                    "layout_type": lay.layout_type,
                    "active_symbols": lay.active_symbols,
                    "timeframes": lay.timeframes,
                    "sync_crosshair": lay.sync_crosshair,
                    "sync_time": lay.sync_time,
                    "sync_symbol": lay.sync_symbol,
                    "is_default": lay.is_default,
                    "updated_at": lay.updated_at.isoformat() if lay.updated_at else None,
                }
                for lay in layouts
            ],
            "total": len(layouts),
        },
        correlation_id=cid,
    )


@router.post("/layouts")
async def save_chart_layout(
    request: Request,
    payload: SaveLayoutRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Save or update chart layout preset."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    layout_id = f"lay-{uuid.uuid4().hex[:12]}"
    layout = ChartLayout(
        id=layout_id,
        user_id=user_id,
        name=payload.name,
        layout_type=payload.layout_type,
        active_symbols=payload.active_symbols,
        timeframes=payload.timeframes,
        sync_crosshair=payload.sync_crosshair,
        sync_time=payload.sync_time,
        sync_symbol=payload.sync_symbol,
        is_default=payload.is_default,
    )
    db.add(layout)
    await db.commit()

    return create_response_envelope(
        data={"layout_id": layout_id, "name": payload.name, "status": "SAVED"},
        correlation_id=cid,
    )


@router.delete("/layouts/{layout_id}")
async def delete_chart_layout(
    request: Request,
    layout_id: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a saved chart layout."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = select(ChartLayout).where(ChartLayout.id == layout_id, ChartLayout.user_id == user_id)
    res = await db.execute(stmt)
    layout = res.scalar_one_or_none()
    if not layout:
        raise NotFoundException(message=f"Layout '{layout_id}' not found.")

    await db.delete(layout)
    await db.commit()

    return create_response_envelope(data={"deleted_id": layout_id, "status": "DELETED"}, correlation_id=cid)


# --- Drawing Endpoints ---


@router.get("/drawings/{symbol}")
async def get_chart_drawings(
    request: Request,
    symbol: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Fetch persistent drawings for symbol and user, anchored to time/price coordinates."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    clean_sym = symbol.upper()

    stmt = (
        select(ChartDrawing)
        .where(
            ChartDrawing.user_id == user_id,
            ChartDrawing.symbol == clean_sym,
        )
        .order_by(ChartDrawing.created_at)
    )
    res = await db.execute(stmt)
    drawings = res.scalars().all()

    return create_response_envelope(
        data={
            "symbol": clean_sym,
            "drawings": [
                {
                    "id": d.id,
                    "symbol": d.symbol,
                    "drawing_type": d.drawing_type,
                    "coordinates": d.coordinates,
                    "properties": d.properties,
                    "market": d.market,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in drawings
            ],
            "total": len(drawings),
        },
        correlation_id=cid,
    )


@router.post("/drawings")
async def save_chart_drawing(
    request: Request,
    payload: SaveDrawingRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Save or update drawing annotation anchored to instrument coordinates."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    clean_sym = payload.symbol.upper()

    drawing_id = payload.id or f"drw-{uuid.uuid4().hex[:12]}"

    # Check if exists
    stmt = select(ChartDrawing).where(ChartDrawing.id == drawing_id, ChartDrawing.user_id == user_id)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        existing.coordinates = payload.coordinates
        existing.properties = payload.properties
        existing.drawing_type = payload.drawing_type
        existing.updated_at = datetime.now(timezone.utc)
    else:
        drawing = ChartDrawing(
            id=drawing_id,
            user_id=user_id,
            symbol=clean_sym,
            drawing_type=payload.drawing_type,
            coordinates=payload.coordinates,
            properties=payload.properties,
            market=payload.market,
        )
        db.add(drawing)

    await db.commit()

    return create_response_envelope(
        data={"drawing_id": drawing_id, "symbol": clean_sym, "status": "SAVED"},
        correlation_id=cid,
    )


@router.delete("/drawings/{drawing_id}")
async def delete_chart_drawing(
    request: Request,
    drawing_id: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete single drawing by ID."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = select(ChartDrawing).where(ChartDrawing.id == drawing_id, ChartDrawing.user_id == user_id)
    res = await db.execute(stmt)
    drawing = res.scalar_one_or_none()
    if not drawing:
        raise NotFoundException(message=f"Drawing '{drawing_id}' not found.")

    await db.delete(drawing)
    await db.commit()

    return create_response_envelope(data={"deleted_id": drawing_id, "status": "DELETED"}, correlation_id=cid)


@router.delete("/drawings/clear/{symbol}")
async def clear_chart_drawings(
    request: Request,
    symbol: str,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Clear all drawings for symbol and caller."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))
    clean_sym = symbol.upper()

    stmt = delete(ChartDrawing).where(ChartDrawing.user_id == user_id, ChartDrawing.symbol == clean_sym)
    await db.execute(stmt)
    await db.commit()

    return create_response_envelope(data={"symbol": clean_sym, "status": "CLEARED"}, correlation_id=cid)


# --- Indicator Templates ---


@router.get("/indicator-templates")
async def list_indicator_templates(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List caller's saved indicator templates."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = (
        select(ChartIndicatorTemplate)
        .where(ChartIndicatorTemplate.user_id == user_id)
        .order_by(desc(ChartIndicatorTemplate.updated_at))
    )
    res = await db.execute(stmt)
    templates = res.scalars().all()

    return create_response_envelope(
        data={
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "indicators_config": t.indicators_config,
                    "is_default": t.is_default,
                }
                for t in templates
            ],
            "total": len(templates),
        },
        correlation_id=cid,
    )


@router.post("/indicator-templates")
async def save_indicator_template(
    request: Request,
    payload: SaveIndicatorTemplateRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Save an indicator template preset."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    tpl_id = f"tpl-{uuid.uuid4().hex[:12]}"
    template = ChartIndicatorTemplate(
        id=tpl_id,
        user_id=user_id,
        name=payload.name,
        indicators_config=payload.indicators_config,
        is_default=payload.is_default,
    )
    db.add(template)
    await db.commit()

    return create_response_envelope(
        data={"template_id": tpl_id, "name": payload.name, "status": "SAVED"}, correlation_id=cid
    )


# --- Replay Session Controls ---


@router.get("/replay/session")
async def get_replay_session(
    request: Request,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get active historical replay session and simulated clock."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = (
        select(ReplaySession)
        .where(ReplaySession.user_id == user_id, ReplaySession.status != "STOPPED")
        .order_by(desc(ReplaySession.updated_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        # Default baseline historical session
        sim_clock = datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
        return create_response_envelope(
            data={
                "has_active_session": False,
                "simulated_clock": sim_clock.isoformat(),
                "market": "NSE",
                "feed_label": "Historical Replay (Default)",
                "status": "INACTIVE",
            },
            correlation_id=cid,
        )

    return create_response_envelope(
        data={
            "session_id": session.id,
            "session_name": session.session_name,
            "market": session.market,
            "simulated_clock": session.simulated_clock.isoformat(),
            "start_date": session.start_date.isoformat(),
            "end_date": session.end_date.isoformat(),
            "speed_multiplier": float(session.speed_multiplier),
            "status": session.status,
            "feed_label": "Historical Replay",
            "has_active_session": True,
        },
        correlation_id=cid,
    )


@router.post("/replay/session")
async def set_replay_session(
    request: Request,
    payload: ReplaySessionRequest,
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Initialize or update historical replay clock."""
    from datetime import date

    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    sim_clock = (
        datetime.fromisoformat(payload.simulated_clock.replace("Z", "+00:00"))
        if payload.simulated_clock
        else datetime(2026, 10, 16, 10, 0, 0, tzinfo=timezone.utc)
    )

    stmt = (
        select(ReplaySession)
        .where(ReplaySession.user_id == user_id, ReplaySession.status != "STOPPED")
        .order_by(desc(ReplaySession.updated_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if session:
        session.simulated_clock = sim_clock
        session.status = payload.status or session.status
        session.speed_multiplier = Decimal(str(payload.speed_multiplier or 1.0))
        session.updated_at = datetime.now(timezone.utc)
    else:
        session = ReplaySession(
            id=f"rep-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            session_name=payload.session_name or "Historical Replay Session",
            market=payload.market or "NSE",
            simulated_clock=sim_clock,
            start_date=date.fromisoformat(payload.start_date or "2026-08-01"),
            end_date=date.fromisoformat(payload.end_date or "2026-10-16"),
            speed_multiplier=Decimal(str(payload.speed_multiplier or 1.0)),
            status=payload.status or "ACTIVE",
        )
        db.add(session)

    await db.commit()

    return create_response_envelope(
        data={
            "session_id": session.id,
            "simulated_clock": session.simulated_clock.isoformat(),
            "status": session.status,
            "speed_multiplier": float(session.speed_multiplier),
        },
        correlation_id=cid,
    )


@router.post("/replay/step")
async def step_replay_clock(
    request: Request,
    step_days: int = Query(1, ge=1, le=30),
    current_user: dict = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Step the simulated replay clock forward by given number of days."""
    cid = getattr(request.state, "correlation_id", None)
    user_id = str(current_user.get("sub", current_user.get("user_id", "usr-shivraj-001")))

    stmt = (
        select(ReplaySession)
        .where(ReplaySession.user_id == user_id, ReplaySession.status != "STOPPED")
        .order_by(desc(ReplaySession.updated_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()

    if not session:
        raise NotFoundException(message="No active replay session. Create one via POST /charts/replay/session first.")

    session.simulated_clock += timedelta(days=step_days)
    session.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return create_response_envelope(
        data={
            "session_id": session.id,
            "simulated_clock": session.simulated_clock.isoformat(),
            "stepped_days": step_days,
        },
        correlation_id=cid,
    )
