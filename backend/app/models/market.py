"""SQLAlchemy 2.0 ORM Models for Market Data & Watchlists.

Task ID: S3-DAT-01
Corresponds to DDL schema in data/ddl/020_market.sql.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from backend.app.models.core import Base, User
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Security(Base):
    """Securities/instruments master entity."""

    __tablename__ = "securities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, default="NSE")
    canonical_id: Mapped[str] = mapped_column(String(70), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    provider_token: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    quotes: Mapped[List["MarketQuote"]] = relationship(
        "MarketQuote", back_populates="security", cascade="all, delete-orphan"
    )
    price_history: Mapped[List["MarketPriceHistory"]] = relationship(
        "MarketPriceHistory", back_populates="security", cascade="all, delete-orphan"
    )
    watchlist_items: Mapped[List["WatchlistItem"]] = relationship(
        "WatchlistItem", back_populates="security", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("symbol", "exchange", name="uq_securities_symbol_exchange"),)


class MarketQuote(Base):
    """Latest observation quotes with explicit source, cache and freshness metadata."""

    __tablename__ = "market_quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    open_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    high_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    low_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    close_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    previous_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    change: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="yfinance")
    served_from_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_delayed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    freshness_status: Mapped[str] = mapped_column(String(50), nullable=False, default="END_OF_DAY")

    security: Mapped["Security"] = relationship("Security", back_populates="quotes")

    @property
    def ltp(self) -> Decimal:
        return self.price

    @property
    def freshness(self) -> str:
        return self.freshness_status

    __table_args__ = (
        CheckConstraint("price > 0", name="chk_quote_price_positive"),
        UniqueConstraint("security_id", "observed_at", "source", name="uq_security_quote_observation"),
    )


class MarketPriceHistory(Base):
    """Historical daily OHLCV price bars for charting and valuation."""

    __tablename__ = "market_price_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    interval: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="1D")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    open_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    adj_close_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="yfinance")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    security: Mapped["Security"] = relationship("Security", back_populates="price_history")

    __table_args__ = (
        CheckConstraint(
            "open_price > 0 AND high_price > 0 AND low_price > 0 AND close_price > 0",
            name="chk_ohlcv_positive",
        ),
        CheckConstraint("volume >= 0", name="chk_volume_non_negative"),
        UniqueConstraint("security_id", "trade_date", "source", name="uq_price_history_natural_key"),
    )


class Watchlist(Base):
    """User-owned watchlist container."""

    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="My Watchlist")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User")
    items: Mapped[List["WatchlistItem"]] = relationship(
        "WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_watchlist_name"),)


class WatchlistItem(Base):
    """Individual instrument pinned in a user's watchlist."""

    __tablename__ = "watchlist_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    watchlist: Mapped["Watchlist"] = relationship("Watchlist", back_populates="items")
    security: Mapped["Security"] = relationship("Security", back_populates="watchlist_items")

    __table_args__ = (UniqueConstraint("watchlist_id", "security_id", name="uq_watchlist_security"),)
