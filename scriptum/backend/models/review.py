"""SQLAlchemy ORM models for the SCRIPTUM database.

Defines all 6 tables: users, reviews, reviewer_results, files, feedback, metrics.
Uses UUID primary keys, JSON columns for flexible data, and proper foreign key
relationships with cascade deletes.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    """User account (optional, for multi-user deployment)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Review(Base):
    """A paper review session with its configuration and results."""

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    paper_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    journal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain_general: Mapped[str | None] = mapped_column(String(100), nullable=True)
    domain_specific: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # JSON result data
    desk_check_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped[User | None] = relationship(back_populates="reviews")
    reviewer_results: Mapped[list["ReviewerResult"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    feedback_entries: Mapped[list["Feedback"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    metric_entries: Mapped[list["Metric"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )


class ReviewerResult(Base):
    """Individual reviewer agent output for a review."""

    __tablename__ = "reviewer_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    review: Mapped[Review] = relationship(back_populates="reviewer_results")


class File(Base):
    """An uploaded file (PDF, .tex, .bib) associated with a review."""

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    review: Mapped[Review] = relationship(back_populates="files")


class Feedback(Base):
    """User feedback on a completed review."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reviews.id"), nullable=False)
    rating: Mapped[int | None] = mapped_column(nullable=True)
    category_ratings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
    )

    # Relationships
    review: Mapped[Review] = relationship(back_populates="feedback_entries")


class Metric(Base):
    """Observability metric recorded during a review."""

    __tablename__ = "metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    review_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("reviews.id"), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    review: Mapped[Review | None] = relationship(back_populates="metric_entries")


class ChatMessage(Base):
    """A chat message between the user and the meta reviewer for a review."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    review: Mapped[Review] = relationship(back_populates="chat_messages")
