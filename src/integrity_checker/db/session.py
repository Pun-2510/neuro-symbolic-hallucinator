"""SQLAlchemy session factory."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from integrity_checker.config import get_settings
from integrity_checker.db.models import Base


_engine: Engine | None = None
_engine_url: str | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Lazy singleton engine — automatically rebinds if database.url changes."""
    global _engine, _engine_url, _SessionLocal
    settings = get_settings()
    url = settings.database.url
    if _engine is None or _engine_url != url:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        kwargs: dict = {
            "echo": settings.database.echo,
            "connect_args": connect_args,
        }
        if url == "sqlite:///:memory:":
            kwargs["poolclass"] = StaticPool
        _engine = create_engine(url, **kwargs)
        _engine_url = url
        _SessionLocal = None
    return _engine


def get_session() -> Session:
    """Trả về session mới. Caller chịu trách nhiệm close."""
    global _SessionLocal
    engine = get_engine()
    if _SessionLocal is None:
        _ensure_db_initialized()
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
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
        2026-10-15 (v1.15) — users table gained institution, can_override_verdicts
            for teacher support. classes + class_memberships tables are created
            by Base.metadata.create_all (no ALTER needed — fresh tables).
        2026-10-21 (v1.16) — citations + verdicts tables gained context, the
            surrounding PDF text of a citation, so the Document Inspector can
            render the sentence a citation appears in.
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
        if "context" not in cit_cols:
            conn.exec_driver_sql(
                "ALTER TABLE citations ADD COLUMN context TEXT"
            )

        # --- verdicts (v1.16 citation context) ---
        verdict_cols = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(verdicts)").fetchall()
        }
        if "context" not in verdict_cols:
            conn.exec_driver_sql(
                "ALTER TABLE verdicts ADD COLUMN context TEXT"
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

        # --- users (v1.15 — teacher support) ---
        if "institution" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN institution VARCHAR(255)")
        if "can_override_verdicts" not in user_cols:
            conn.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN can_override_verdicts INTEGER DEFAULT 0"
            )

        # --- Clean up any historical orphan rows ---
        conn.exec_driver_sql(
            "DELETE FROM citations WHERE essay_id NOT IN (SELECT id FROM essays)"
        )
        conn.exec_driver_sql(
            "DELETE FROM verdicts WHERE essay_id NOT IN (SELECT id FROM essays)"
        )


def _ensure_db_initialized() -> None:
    """Ensure all migrations have run and tables exist.

    Order matters: create_all FIRST so that any ALTER TABLE for fresh DBs
    (where tables don't exist yet) can find their target tables. Skipping
    this order causes "no such table: X" on first run with a clean DB.
    """
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _run_inline_migrations(engine)


def init_db() -> None:
    """Public entry-point — used by FastAPI startup and CLI tools."""
    _ensure_db_initialized()
