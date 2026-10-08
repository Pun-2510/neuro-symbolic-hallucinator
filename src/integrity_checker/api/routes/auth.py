"""Auth routes — login, logout, me."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from integrity_checker.api.deps import get_current_user, get_db, get_token_from_header
from integrity_checker.config import get_settings
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


# Hardcoded credentials (MVP demo only)
HARDCODED_USERS = {
    "admin": ("admin123", "admin"),
    "user": ("user123", "user"),
}

# Default emails for the hardcoded demo users (assigned on first login)
HARDCODED_USER_EMAILS = {
    "admin": "admin@example.com",
    "user": "user@example.com",
}

# Default full names for the hardcoded demo users
HARDCODED_USER_FULL_NAMES = {
    "admin": "Administrator",
    "user": "Demo User",
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
    email: str | None = None
    full_name: str | None = None
    role: str
    is_active: bool = True
    avatar_url: str | None = None
    last_login_at: str | None = None
    created_at: str | None = None


class MessageResponse(BaseModel):
    message: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def _to_response_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": bool(user.is_active),
        "avatar_url": user.avatar_path,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _create_token(user: User) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auth.token_expire_hours)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),  # JWT requires sub to be a string
        "username": user.username,
        "role": user.role,
        "exp": expires_at,
        "iat": now,
        # jti ensures tokens are unique even when issued in the same second
        "jti": f"{user.id}-{now.timestamp()}",
    }
    token = jwt.encode(payload, settings.auth.jwt_secret, algorithm="HS256")
    return token, expires_at


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db=Depends(get_db)):
    """Login with username/password.

    Supports both hardcoded demo credentials (admin/user) and any user stored in
    the database. If a user exists in the DB, their stored password hash is used
    (allowing admin-created users and password changes to work). Hardcoded credentials
    create the user on first login if needed.
    """
    repo = Repository(db)
    user: User | None = None

    # Check DB first — if the user exists, use their stored password hash.
    # This allows admin-created users and password changes to work.
    db_user = repo.get_user_by_username(request.username)
    if db_user:
        user = db_user
        if not _verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
    else:
        # No DB user — check hardcoded credentials (for demo/admin accounts)
        if request.username not in HARDCODED_USERS:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        expected_password, role = HARDCODED_USERS[request.username]
        if request.password != expected_password:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        # Create DB entry on first login for hardcoded users
        password_hash = _hash_password(request.password)
        user = repo.create_user(
            username=request.username,
            password_hash=password_hash,
            role=role,
            email=HARDCODED_USER_EMAILS.get(request.username),
            full_name=HARDCODED_USER_FULL_NAMES.get(request.username),
        )

    # Stamp last_login_at every login
    repo.update_last_login(user.id)

    # Create session
    token, expires_at = _create_token(user)
    repo.create_session(user.id, token, expires_at)
    repo.commit()

    return LoginResponse(token=token, user=_to_response_dict(user))


@router.post("/logout", response_model=MessageResponse)
def logout(
    authorization: str | None = Header(None),
    db=Depends(get_db),
):
    """Logout current user.

    Gracefully handles missing/invalid/expired tokens by just deleting the session
    if it exists. This ensures the client-side logout always succeeds.
    """
    repo = Repository(db)

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        # Try to delete session - will silently succeed if session doesn't exist
        repo.delete_session(token)

    repo.commit()
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info (full profile)."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=bool(current_user.is_active),
        avatar_url=current_user.avatar_path,
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )
