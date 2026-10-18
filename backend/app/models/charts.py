"""SQLAlchemy ORM Models for Chart Layouts, Drawings, Indicator Templates, and Replay Sessions.

Supports:
- Multi-chart synchronized layout configurations (single, dual_h, dual_v, quad)
- Time- and price-anchored persistent drawing annotations (trend lines, fibonacci, rects, text)
- Saved indicator configurations (SMA, EMA, BB, RSI, MACD, VWAP)
- Historical replay session state with simulated market clock
"""

from datetime import datetime, timezone

from backend.app.models.core import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship


class ChartLayout(Base):
    __tablename__ = "chart_layouts"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, default="Default Layout")
    layout_type = Column(String(20), nullable=False, default="single")  # single, dual_h, dual_v, quad
    active_symbols = Column(JSON, nullable=False, default=list)
    timeframes = Column(JSON, nullable=False, default=list)
    sync_crosshair = Column(Boolean, nullable=False, default=True)
    sync_time = Column(Boolean, nullable=False, default=True)
    sync_symbol = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")


class ChartDrawing(Base):
    __tablename__ = "chart_drawings"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    drawing_type = Column(
        String(30), nullable=False
    )  # trend_line, ray, horizontal_line, vertical_line, rectangle, text_note, fibonacci, ruler
    coordinates = Column(JSON, nullable=False)  # [{time: timestamp, price: float}, ...]
    properties = Column(JSON, nullable=False)  # {color: str, lineWidth: int, text: str, isLocked: bool}
    market = Column(String(10), nullable=False, default="NSE")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")


class ChartIndicatorTemplate(Base):
    __tablename__ = "chart_indicator_templates"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    indicators_config = Column(JSON, nullable=False)  # [{type: 'SMA', period: 20, color: '...'}, ...]
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")


class ReplaySession(Base):
    __tablename__ = "replay_sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_name = Column(String(100), nullable=False, default="Historical Replay Session")
    market = Column(String(20), nullable=False, default="NSE")
    simulated_clock = Column(DateTime(timezone=True), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    speed_multiplier = Column(Numeric(4, 2), nullable=False, default=1.00)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, PAUSED, STOPPED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User")
