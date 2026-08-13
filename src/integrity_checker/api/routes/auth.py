"""Auth routes — login, logout, me."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from integrity_checker.api.deps import get_current_user, get_db, get_token_from_header
from integrity_checker.config import get_settings
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


# Hardcoded credentials
HARDCODED_USERS = {
    "admin": ("admin123", "admin"),
    "user": ("user123", "user"),
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    role: str


class MessageResponse(BaseModel):
    message: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _create_token(user: User) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auth.token_expire_hours)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.auth.jwt_secret, algorithm="HS256")
    return token, expires_at


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db=Depends(get_db)):
    """Login with username/password."""
    # Check hardcoded credentials
    if request.username not in HARDCODED_USERS:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    expected_password, role = HARDCODED_USERS[request.username]
    if request.password != expected_password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    repo = Repository(db)

    # Get or create user in DB
    user = repo.get_user_by_username(request.username)
    if not user:
        # Create user with hashed password
        password_hash = _hash_password(request.password)
        user = repo.create_user(request.username, password_hash, role)
        repo.commit()

    # Create session
    token, expires_at = _create_token(user)
    repo.create_session(user.id, token, expires_at)
    repo.commit()

    return LoginResponse(
        token=token,
        user={"id": user.id, "username": user.username, "role": user.role}
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    token: str = Depends(get_token_from_header),
    db=Depends(get_db),
):
    """Logout current user."""
    repo = Repository(db)
    repo.delete_session(token)
    repo.commit()
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role
    )
