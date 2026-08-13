"""FastAPI dependency injection - Extended with auth."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from integrity_checker.config import get_settings
from integrity_checker.db.models import User
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


def get_token_from_header(authorization: str) -> str:
    """Extract Bearer token from authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.replace("Bearer ", "")


def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT token and return current user."""
    token = get_token_from_header(authorization)
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.auth.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Verify session exists and is not expired
    repo = Repository(db)
    session_record = repo.get_session_by_token(token)
    if not session_record:
        raise HTTPException(status_code=401, detail="Session not found")

    if session_record.expires_at < datetime.now(timezone.utc):
        repo.delete_session(token)
        raise HTTPException(status_code=401, detail="Token expired")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user_optional(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User | None:
    """Return current user or None if not authenticated."""
    if not authorization:
        return None

    try:
        return get_current_user(authorization, db)
    except HTTPException:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Raise 403 if user is not admin."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user