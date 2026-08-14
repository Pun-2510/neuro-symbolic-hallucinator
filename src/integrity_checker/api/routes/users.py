"""User management routes (admin only)."""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str | None


class MessageResponse(BaseModel):
    message: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@router.get("", response_model=list[UserResponse])
def list_users(
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """List all users (admin only)."""
    repo = Repository(db)
    users = repo.get_all_users()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            role=u.role,
            created_at=u.created_at.isoformat() if u.created_at else None
        )
        for u in users
    ]


@router.post("", response_model=UserResponse)
def create_user(
    request: UserCreate,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """Create new user (admin only)."""
    repo = Repository(db)

    # Check if username exists
    existing = repo.get_user_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Validate role
    if request.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")

    password_hash = _hash_password(request.password)
    user = repo.create_user(request.username, password_hash, request.role)
    repo.commit()

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: UserUpdate,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """Update user (admin only)."""
    repo = Repository(db)

    update_data = {}
    if request.username is not None:
        # Check if username exists (and not same user)
        existing = repo.get_user_by_username(request.username)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Username already exists")
        update_data["username"] = request.username

    if request.role is not None:
        if request.role not in ["admin", "user"]:
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
        update_data["role"] = request.role

    if request.password is not None:
        update_data["password_hash"] = _hash_password(request.password)

    user = repo.update_user(user_id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    repo.commit()

    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """Delete user (admin only)."""
    repo = Repository(db)

    # Cannot delete yourself
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    success = repo.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    repo.commit()

    return MessageResponse(message=f"User {user_id} deleted")
