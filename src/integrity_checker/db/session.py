"""SQLAlchemy session factory."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from integrity_checker.config import get_settings
from integrity_checker.db.models import Base


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Lazy singleton engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.database.url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(
            url,
            echo=settings.database.echo,
            connect_args=connect_args,
        )
    return _engine


def get_session() -> Session:
    """Trả về session mới. Caller chịu trách nhiệm close."""
    global _SessionLocal
    if _SessionLocal is None:
        _ensure_db_initialized()
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal()


def _run_inline_migrations(engine: Engine) -> None:
    """Apply incremental ALTER TABLE migrations not covered by create_all.

    History:
        2026-09-30 (v1.8) — citations table gained mapping_status,
            mapping_confidence, citation_link_json so the UI Citations tab can
            show the real linking verdict for each in-text occurrence (these
            fields were previously attached in-memory only).
        2026-10-03 (v1.10) — users table gained email, full_name, avatar_path,
            is_active, last_login_at to support account management (admin CRUD,
            self-profile edit, avatar upload).
    """
    with engine.begin() as conn:
        # --- citations ---
        cit_cols = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(citations)").fetchall()
        }
        if "mapping_status" not in cit_cols:
            conn.exec_driver_sql(
                "ALTER TABLE citations ADD COLUMN mapping_status VARCHAR"
            )
        if "mapping_confidence" not in cit_cols:
            conn.exec_driver_sql(
                "ALTER TABLE citations ADD COLUMN mapping_confidence FLOAT DEFAULT 0"
            )
        if "citation_link_json" not in cit_cols:
            conn.exec_driver_sql(
                "ALTER TABLE citations ADD COLUMN citation_link_json TEXT"
            )

        # --- users (v1.10 account management) ---
        user_cols = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        }
        if "email" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
            # Unique index (separate from column unique=True so existing DBs migrate)
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL"
            )
        if "full_name" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN full_name VARCHAR(120)")
        if "avatar_path" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(500)")
        if "is_active" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
        if "last_login_at" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN last_login_at DATETIME")


def _ensure_db_initialized() -> None:
    """Ensure all migrations have run and tables exist."""
    engine = get_engine()
    _run_inline_migrations(engine)
    Base.metadata.create_all(bind=engine)


def init_db() -> None:
    """Public entry-point — used by FastAPI startup and CLI tools."""
    _ensure_db_initialized()
