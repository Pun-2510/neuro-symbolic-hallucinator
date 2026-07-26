"""FastAPI dependency injection."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from integrity_checker.db.repository import Repository
from integrity_checker.db.session import get_session
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline


def get_db() -> Generator[Session, None, None]:
    """Yield DB session, close sau khi xong."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def get_repository(session: Session = None) -> Repository:  # type: ignore[assignment]
    return Repository(session or get_session())


def get_pipeline() -> IntegrityPipeline:
    """Singleton pipeline (lazy)."""
    return IntegrityPipeline()