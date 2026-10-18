"""SQLAlchemy 2.0 ORM Models for Spending & Transaction Management.

Task ID: S7-DAT-02
Author: Shivraj Dhote
Corresponds to DDL schema in data/ddl/061_spending.sql.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.models.core import Base
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TransactionUpload(Base):
    """File upload audit record."""

    __tablename__ = "transaction_uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="COMMITTED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="upload")

    __table_args__ = (UniqueConstraint("user_id", "file_hash_sha256", name="uq_upload_user_file_hash"),)


class TransactionCategory(Base):
    """Master category entity."""

    __tablename__ = "transaction_categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_essential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="category")


class Transaction(Base):
    """Transaction record with masked description for privacy protection."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    upload_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transaction_uploads.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(8), nullable=False)
    masked_description: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("transaction_categories.id"), nullable=False, index=True
    )
    categorization_method: Mapped[str] = mapped_column(String(16), nullable=False, default="RULE")
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("1.00"))
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dedupe_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    upload: Mapped[Optional["TransactionUpload"]] = relationship("TransactionUpload", back_populates="transactions")
    category: Mapped["TransactionCategory"] = relationship("TransactionCategory", back_populates="transactions")

    __table_args__ = (UniqueConstraint("user_id", "dedupe_hash", name="uq_transaction_user_dedupe"),)


class MonthlySpendingSummary(Base):
    """Monthly spending roll-up by user."""

    __tablename__ = "monthly_spending_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    total_debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total_credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    net_savings: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    savings_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    category_breakdown: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TransactionPreview(Base):
    """Durable preview storage for uncommitted CSV uploads across restarts and workers."""

    __tablename__ = "transaction_previews"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    duplicate_rows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    invalid_rows: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    committed_upload_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
