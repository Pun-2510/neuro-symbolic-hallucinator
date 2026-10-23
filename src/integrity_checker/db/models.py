"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import Index, JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Role literals (v1.15 — Phase 3 teacher role).
# Backward compat: giữ "user" cho student, thêm "teacher" mới.
UserRoleLiteral = Literal["user", "teacher", "admin"]
VALID_USER_ROLES: tuple[str, ...] = ("user", "teacher", "admin")


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model for authentication + account management."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")
    # Account management fields (added v1.10 — see db/session.py migrations)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    # v1.15 (Phase 3) — teacher-specific fields
    institution: Mapped[str | None] = mapped_column(String(255), nullable=True)
    can_override_verdicts: Mapped[bool] = mapped_column(Integer, default=0)
    # v1.17 — email verification status (1 for admin/demo/verified, 0 for pending activation)
    email_verified: Mapped[bool] = mapped_column(Integer, default=1)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    auth_tokens: Mapped[list["AuthToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    essays: Mapped[list["EssayRecord"]] = relationship(back_populates="user")
    taught_classes: Mapped[list["Class"]] = relationship(
        "Class", back_populates="teacher", foreign_keys="Class.teacher_id"
    )
    memberships: Mapped[list["ClassMembership"]] = relationship(
        "ClassMembership", back_populates="student", foreign_keys="ClassMembership.student_id",
        cascade="all, delete-orphan",
    )


class Session(Base):
    """Session model for JWT token storage."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="sessions")


class AuthToken(Base):
    """One-time cryptographic tokens for account activation and password reset."""

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_type: Mapped[str] = mapped_column(String(30), nullable=False)  # "activation" | "password_reset"
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="auth_tokens")


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
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    num_pages: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # v1.2 — full pipeline output (JSON serialized)
    style_profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cis_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User | None"] = relationship(back_populates="essays")

    citations: Mapped[list["CitationRecord"]] = relationship(
        back_populates="essay", cascade="all, delete-orphan", passive_deletes=True
    )
    verdicts: Mapped[list["VerdictRecord"]] = relationship(
        back_populates="essay", cascade="all, delete-orphan", passive_deletes=True
    )


class CitationRecord(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    essay_id: Mapped[int] = mapped_column(ForeignKey("essays.id", ondelete="CASCADE"), nullable=False)
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

    # NEW v1.8 — linking layer persisted so the UI Citations tab can
    # display the real mapping_status / citation_link for every occurrence
    # (previously these were attached in-memory only and became null when
    # reloaded from the DB, which made every in-text render as "Linked").
    mapping_status: Mapped[str | None] = mapped_column(String, nullable=True)
    mapping_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    citation_link_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # NEW v1.16 — surrounding text of the citation in the PDF, so the
    # Document Inspector can show the sentence the citation sits in.
    # Nullable: older rows (and citations with no extractable context) stay NULL.
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    essay: Mapped[EssayRecord] = relationship(back_populates="citations")


class VerdictRecord(Base):
    __tablename__ = "verdicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    essay_id: Mapped[int] = mapped_column(ForeignKey("essays.id", ondelete="CASCADE"), nullable=False)
    citation_raw: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    triggered_rules: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    mismatched_fields: Mapped[str] = mapped_column(Text, default="[]")
    features: Mapped[str] = mapped_column(Text, default="{}")  # JSON object
    validated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # v1.2 — Citation Integrity (linking layer)
    mapping_status: Mapped[str | None] = mapped_column(String, nullable=True, default="matched")
    mapping_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    style_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    domain_exception: Mapped[bool] = mapped_column(Integer, default=0)  # SQLite bool

    # v1.2 — Override
    is_overridden: Mapped[bool] = mapped_column(Integer, default=0)
    override_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[str | None] = mapped_column(String, nullable=True)

    # NEW v1.16 — surrounding text of the citation in the PDF, so the
    # Document Inspector can show the sentence the citation sits in.
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    essay: Mapped[EssayRecord] = relationship(back_populates="verdicts")


class AuditLog(Base):
    """Override của giảng viên — log lại để minh bạch."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verdict_id: Mapped[int] = mapped_column(ForeignKey("verdicts.id", ondelete="CASCADE"), nullable=False)
    original_label: Mapped[str] = mapped_column(String, nullable=False)
    new_label: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# v1.15 (Phase 3) — Teacher / Class models
# ---------------------------------------------------------------------------


class Class(Base):
    """Một lớp học do 1 teacher phụ trách, có nhiều students (qua ClassMembership)."""

    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    teacher: Mapped["User"] = relationship("User", foreign_keys=[teacher_id], back_populates="taught_classes")
    memberships: Mapped[list["ClassMembership"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan"
    )


class ClassMembership(Base):
    """Many-to-many User ↔ Class. Student enrolled in N classes."""

    __tablename__ = "class_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    class_: Mapped["Class"] = relationship(back_populates="memberships")
    student: Mapped["User"] = relationship("User", foreign_keys=[student_id], back_populates="memberships")