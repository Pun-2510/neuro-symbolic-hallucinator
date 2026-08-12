"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Index, JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    essays: Mapped[list["EssayRecord"]] = relationship(back_populates="user")


class Session(Base):
    """Session model for JWT token storage."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="sessions")


class CitationCache(Base):
    """Citation cache model for API response caching."""

    __tablename__ = "citation_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    matched_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)


# Indexes for CitationCache
Index("idx_cache_key", CitationCache.cache_key)
Index("idx_source", CitationCache.source)


class EssayRecord(Base):
    __tablename__ = "essays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    num_pages: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship(back_populates="essays")

    citations: Mapped[list["CitationRecord"]] = relationship(
        back_populates="essay", cascade="all, delete-orphan"
    )
    verdicts: Mapped[list["VerdictRecord"]] = relationship(
        back_populates="essay", cascade="all, delete-orphan"
    )


class CitationRecord(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    essay_id: Mapped[int] = mapped_column(ForeignKey("essays.id"), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    citation_type: Mapped[str] = mapped_column(String, default="unknown")
    style: Mapped[str] = mapped_column(String, default="unknown")
    authors: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    year: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    doi: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_num: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    essay: Mapped[EssayRecord] = relationship(back_populates="citations")


class VerdictRecord(Base):
    __tablename__ = "verdicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    essay_id: Mapped[int] = mapped_column(ForeignKey("essays.id"), nullable=False)
    citation_raw: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    triggered_rules: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    mismatched_fields: Mapped[str] = mapped_column(Text, default="[]")
    features: Mapped[str] = mapped_column(Text, default="{}")  # JSON object
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    essay: Mapped[EssayRecord] = relationship(back_populates="verdicts")


class AuditLog(Base):
    """Override của giảng viên — log lại để minh bạch."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verdict_id: Mapped[int] = mapped_column(ForeignKey("verdicts.id"), nullable=False)
    original_label: Mapped[str] = mapped_column(String, nullable=False)
    new_label: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))