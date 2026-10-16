"""SQLAlchemy ORM Models for AI Assistant, Documents, and Retrieval Lineage.

Task ID: S4-DAT-01
Author: Shivraj Dhote
Date: 16 October 2026
"""

from datetime import datetime, timezone

from backend.app.models.core import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship


class DocumentRegistry(Base):
    __tablename__ = "document_registry"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)
    publisher = Column(String(100), nullable=False)
    publishing_date = Column(Date, nullable=False)
    reporting_period = Column(String(50), nullable=True)
    security_symbol = Column(String(20), nullable=True)
    isin = Column(String(20), nullable=True)
    source_url = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=False)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(64), primary_key=True)
    document_id = Column(String(64), ForeignKey("document_registry.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    section_title = Column(String(200), nullable=True)
    page_number = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=False)
    embedding_vector = Column(JSON, nullable=True)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("DocumentRegistry", back_populates="chunks")

    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunk"),)


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=False)

    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    intent_detected = Column(String(50), nullable=True)
    correlation_id = Column(String(64), nullable=False)
    latency_ms = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    is_fallback = Column(Boolean, default=False)
    citation_chunk_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("AIConversation", back_populates="messages")
    feedback = relationship("AIFeedback", back_populates="message", cascade="all, delete-orphan")


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(String(64), primary_key=True)
    message_id = Column(String(64), ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 or -1
    feedback_type = Column(String(50), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    message = relationship("AIMessage", back_populates="feedback")

    __table_args__ = (UniqueConstraint("user_id", "message_id", name="uq_user_message_feedback"),)


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"

    id = Column(String(64), primary_key=True)
    correlation_id = Column(String(64), nullable=False)
    conversation_id = Column(String(64), nullable=True)
    query_text = Column(Text, nullable=False)
    filter_metadata = Column(JSON, nullable=True)
    top_k = Column(Integer, nullable=False)
    retrieved_chunk_ids = Column(JSON, nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
