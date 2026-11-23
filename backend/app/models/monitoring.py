"""SQLAlchemy 2.0 ORM Models for Error Monitoring and Observability.

Defines the ErrorEvent entity for durable, bounded operational error tracking.
"""

import uuid
from datetime import datetime
from typing import Optional

from backend.app.models.core import Base
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class ErrorEvent(Base):
    """Durable, bounded operational error event log."""

    __tablename__ = "error_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    error_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    feature_area: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sanitized_message: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
