"""
Database models for chat system.

Uses SQLAlchemy with SQLite for conversation and message persistence.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    Integer,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all database models."""

    pass


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class User(Base):
    """User account for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # User owns conversations
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # User owns analysis results
    analysis_results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Conversation(Base):
    """Represents a chat conversation/session."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Conversation context
    context_type: Mapped[str] = mapped_column(
        String(50), default="general"
    )  # "general", "analysis", "interpretation"
    analysis_query: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Associated survival query if any

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # User relationship - nullable for backwards compatibility
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    # Indexes
    __table_args__ = (
        Index("ix_conversations_created_at", "created_at"),
        Index("ix_conversations_updated_at", "updated_at"),
        Index("ix_conversations_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title})>"


class Message(Base):
    """Individual message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # For streaming support
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tool/function call results
    tool_calls: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Store any tool invocations

    # Query estimation if this message triggered one
    estimation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("query_estimations.id"), nullable=True
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    estimation: Mapped[Optional["QueryEstimation"]] = relationship(
        "QueryEstimation", back_populates="message"
    )

    # Indexes
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"


class QueryEstimation(Base):
    """Pre-flight estimation results for queries."""

    __tablename__ = "query_estimations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Original query
    original_query: Mapped[str] = mapped_column(Text, nullable=False)

    # Estimation results
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # 0.0 to 1.0
    estimated_datasets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    can_proceed: Mapped[bool] = mapped_column(Boolean, default=True)

    # Suggestions
    improved_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestions: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True
    )  # List of improvement suggestions

    # Validation flags
    has_survival_keywords: Mapped[bool] = mapped_column(Boolean, default=False)
    has_cancer_type: Mapped[bool] = mapped_column(Boolean, default=False)
    has_organism: Mapped[bool] = mapped_column(Boolean, default=False)
    has_gene_focus: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship back to message
    message: Mapped[Optional["Message"]] = relationship(
        "Message", back_populates="estimation"
    )

    # Indexes
    __table_args__ = (Index("ix_query_estimations_created_at", "created_at"),)

    def __repr__(self) -> str:
        return f"<QueryEstimation(id={self.id}, confidence={self.confidence_score})>"


class AnalysisResult(Base):
    """Persisted analysis results for shareable links and history."""

    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    n_datasets_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    n_datasets_with_survival: Mapped[int] = mapped_column(Integer, default=0)
    n_genes_found: Mapped[int] = mapped_column(Integer, default=0)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    result_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )

    # Relationship back to user
    user: Mapped[Optional["User"]] = relationship("User", back_populates="analysis_results")

    # Indexes
    __table_args__ = (
        Index("ix_analysis_results_user_id", "user_id"),
        Index("ix_analysis_results_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult(id={self.id}, query={self.query[:50]})>"
