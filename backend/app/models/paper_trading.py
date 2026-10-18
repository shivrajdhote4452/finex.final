"""SQLAlchemy ORM Models for Paper Trading, Orders, Trades, and Cash Ledger.

Task ID: S5-DAT-01
Author: Shivraj Dhote
Date: 16 October 2026
"""

import uuid
from datetime import datetime, timezone

from backend.app.models.core import Base
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship


class PaperAccount(Base):
    __tablename__ = "paper_accounts"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    account_number = Column(String(32), nullable=False, default=lambda: f"ACC-{uuid.uuid4().hex[:8].upper()}")
    initial_balance = Column(Numeric(14, 2), nullable=False, default=100000.00)
    current_cash = Column(Numeric(14, 2), nullable=False, default=100000.00)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="ACTIVE")
    reset_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    orders = relationship("PaperOrder", back_populates="account", cascade="all, delete-orphan")
    trades = relationship("PaperTrade", back_populates="account", cascade="all, delete-orphan")
    positions = relationship("PaperPosition", back_populates="account", cascade="all, delete-orphan")
    ledger_entries = relationship("PaperCashLedger", back_populates="account", cascade="all, delete-orphan")


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(String(64), primary_key=True)
    account_id = Column(String(64), ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL
    order_type = Column(String(20), nullable=False, default="MARKET")
    quantity = Column(Numeric(14, 4), nullable=False)
    limit_price = Column(Numeric(14, 2), nullable=True)
    fill_price = Column(Numeric(14, 2), nullable=True)
    fee = Column(Numeric(14, 2), nullable=False, default=0.00)
    status = Column(String(20), nullable=False, default="PENDING")
    rejection_reason = Column(String(255), nullable=True)
    idempotency_key = Column(String(128), nullable=False)
    execution_receipt = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    account = relationship("PaperAccount", back_populates="orders")
    trade = relationship("PaperTrade", back_populates="order", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("account_id", "idempotency_key", name="uq_paper_order_idempotency"),)


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(String(64), primary_key=True)
    order_id = Column(String(64), ForeignKey("paper_orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    account_id = Column(String(64), ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    price = Column(Numeric(14, 2), nullable=False)
    gross_value = Column(Numeric(14, 2), nullable=False)
    fee = Column(Numeric(14, 2), nullable=False, default=0.00)
    net_value = Column(Numeric(14, 2), nullable=False)
    execution_time = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    order = relationship("PaperOrder", back_populates="trade")
    account = relationship("PaperAccount", back_populates="trades")


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id = Column(String(64), primary_key=True)
    account_id = Column(String(64), ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    average_buy_price = Column(Numeric(14, 2), nullable=False)
    total_cost_basis = Column(Numeric(14, 2), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    account = relationship("PaperAccount", back_populates="positions")

    __table_args__ = (UniqueConstraint("account_id", "symbol", name="uq_paper_position_symbol"),)


class PaperCashLedger(Base):
    __tablename__ = "paper_cash_ledger"

    id = Column(String(64), primary_key=True)
    account_id = Column(String(64), ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False)
    entry_type = Column(String(30), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)
    reference_id = Column(String(64), nullable=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    account = relationship("PaperAccount", back_populates="ledger_entries")


class PaperProposal(Base):
    __tablename__ = "paper_proposals"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(String(64), ForeignKey("paper_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    instruction_text = Column(String(1000), nullable=False)
    conversation_id = Column(String(64), nullable=True, index=True)
    proposed_allocations = Column(
        JSON, nullable=False
    )  # List of {symbol, quantity, estimated_price, estimated_total, currency}
    requested_budget = Column(Numeric(14, 2), nullable=True)
    total_budget = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="PROPOSED")  # PROPOSED, ACCEPTED, REJECTED, EXPIRED, EXECUTED
    execution_receipts = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)

    account = relationship("PaperAccount")
