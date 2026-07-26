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
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal()


def init_db() -> None:
    """Tạo tables (MVP — không dùng Alembic)."""
    Base.metadata.create_all(bind=get_engine())