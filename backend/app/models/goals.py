"""SQLAlchemy 2.0 ORM Models for Financial Goals.

Task ID: S7-DAT-01
Author: Shivraj Dhote
Corresponds to DDL schema in data/ddl/060_goals.sql.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.models.core import Base
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class FinancialGoal(Base):
    """User financial goal entity with target date and return assumptions."""

    __tablename__ = "financial_goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    assumed_annual_return_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("8.00"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    contributions: Mapped[List["GoalContribution"]] = relationship(
        "GoalContribution", back_populates="goal", cascade="all, delete-orphan"
    )
    projections: Mapped[List["GoalProjection"]] = relationship(
        "GoalProjection", back_populates="goal", cascade="all, delete-orphan"
    )


class GoalContribution(Base):
    """Append-only audit record of user contribution towards a goal."""

    __tablename__ = "goal_contributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    goal: Mapped["FinancialGoal"] = relationship("FinancialGoal", back_populates="contributions")


class GoalProjection(Base):
    """Historical versioned projection snapshot."""

    __tablename__ = "goal_projections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    formula_version: Mapped[str] = mapped_column(String(32), nullable=False, default="fv_compound_monthly_v1.0")
    months_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    projected_future_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    required_monthly_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    shortfall_surplus: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    assumptions_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    goal: Mapped["FinancialGoal"] = relationship("FinancialGoal", back_populates="projections")
