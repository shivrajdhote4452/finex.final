"""SQLAlchemy 2.0 ORM Models for Core Operational Storage.

Task ID: S1-DAT-02
Corresponds to DDL schema in data/ddl/001_core.sql.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base class for all FinEx operational database entities."""

    pass


class User(Base):
    """Core user account entity supporting OAuth and local identity stubs."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="google")
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    consents: Mapped[List["UserConsent"]] = relationship(
        "UserConsent", back_populates="user", cascade="all, delete-orphan"
    )
    portfolios: Mapped[List["Portfolio"]] = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    events: Mapped[List["ApplicationEvent"]] = relationship("ApplicationEvent", back_populates="user")

    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_users_provider_subject"),)


class UserProfile(Base):
    """Investor profile details, experience levels, and questionnaire progress."""

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(3), nullable=False, default="IND")
    experience_level: Mapped[str] = mapped_column(String(50), nullable=False, default="BEGINNER")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")


class UserConsent(Base):
    """Audit-compliant explicit consent tracking for terms, privacy and paper disclaimer."""

    __tablename__ = "user_consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_version: Mapped[str] = mapped_column(String(50), nullable=False)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    privacy_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    educational_disclaimer_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="consents")

    __table_args__ = (UniqueConstraint("user_id", "consent_version", name="uq_user_consent_version"),)


class Portfolio(Base):
    """User portfolio container holding individual equity, ETF, and mutual fund positions."""

    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="My Primary Portfolio")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    holdings: Mapped[List["PortfolioHolding"]] = relationship(
        "PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan"
    )


class PortfolioHolding(Base):
    """Granular asset holding position within a user's portfolio."""

    __tablename__ = "portfolio_holdings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False, default="EQUITY")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    cost_basis_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_holdings_quantity_positive"),
        CheckConstraint("cost_basis_per_share >= 0", name="chk_holdings_cost_basis_non_negative"),
        UniqueConstraint("portfolio_id", "symbol", "purchase_date", name="uq_portfolio_symbol_purchase"),
    )


class ApplicationEvent(Base):
    """Operational audit and lineage event log for correlation tracking."""

    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="events")
