"""User management routes (admin + self-service).

Admin endpoints under ``/api/users`` (CRUD for all users) require admin role.
Self-service endpoints under ``/api/users/me`` allow any authenticated user
to view/update their own profile, upload avatar, change password.
"""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, EmailStr, Field

from integrity_checker.api.deps import get_current_user, get_db, require_admin
from integrity_checker.api.services.avatar_service import get_avatar_service
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


# ---------- Schemas ----------


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=120)
    role: str = "user"
    is_active: bool = True


class UserUpdate(BaseModel):
    """Admin full-update — all fields optional except what's being changed."""

    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=120)
    role: str | None = None
    is_active: bool | None = None


class UserSelfUpdate(BaseModel):
    """Self-service profile update — username + role + is_active are NOT user-editable."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, max_length=120)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    role: str
    is_active: bool
    avatar_url: str | None
    last_login_at: str | None
    created_at: str | None


class MessageResponse(BaseModel):
    message: str


# ---------- Helpers ----------


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=bool(user.is_active),
        avatar_url=user.avatar_path,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


# ---------- Admin endpoints (existing, extended) ----------


@router.get("", response_model=list[UserResponse])
def list_users(
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """List all users (admin only)."""
    repo = Repository(db)
    users = repo.get_all_users()
    return [_to_response(u) for u in users]


@router.post("", response_model=UserResponse)
def create_user(
    request: UserCreate,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """Create new user (admin only)."""
    repo = Repository(db)

    if repo.get_user_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    if request.email and repo.get_user_by_email(request.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    if request.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")

    password_hash = _hash_password(request.password)
    user = repo.create_user(
        username=request.username,
        password_hash=password_hash,
        role=request.role,
        email=request.email,
        full_name=request.full_name,
        is_active=request.is_active,
    )
    repo.commit()
    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: UserUpdate,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """Update user (admin only)."""
    repo = Repository(db)

    existing = repo.get_user_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    update_data: dict = {}

    if request.username is not None and request.username != existing.username:
        dup = repo.get_user_by_username(request.username)
        if dup and dup.id != user_id:
            raise HTTPException(status_code=400, detail="Username already exists")
        update_data["username"] = request.username

    if request.email is not None and request.email != existing.email:
        dup = repo.get_user_by_email(request.email)
        if dup and dup.id != user_id:
            raise HTTPException(status_code=400, detail="Email already exists")
        update_data["email"] = request.email

    if request.full_name is not None:
        update_data["full_name"] = request.full_name

    if request.role is not None:
        if request.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
        update_data["role"] = request.role

    if request.is_active is not None:
        update_data["is_active"] = request.is_active

    if request.password is not None:
        update_data["password_hash"] = _hash_password(request.password)

    user = repo.update_user(user_id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    repo.commit()
    return _to_response(user)


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db=Depends(get_db),
):
    """Delete user (admin only). Cannot delete yourself."""
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    repo = Repository(db)
    user = repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Best-effort: clean up avatar file
    if user.avatar_path:
        get_avatar_service().delete(user.avatar_path)

    success = repo.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    repo.commit()
    return MessageResponse(message=f"User {user_id} deleted")


# ---------- Self-service endpoints ----------


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user full profile."""
    return _to_response(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    request: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update own email and/or full name."""
    repo = Repository(db)

    update_data: dict = {}
    if request.email is not None and request.email != current_user.email:
        dup = repo.get_user_by_email(request.email)
        if dup and dup.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already exists")
        update_data["email"] = request.email

    if request.full_name is not None:
        update_data["full_name"] = request.full_name

    if update_data:
        user = repo.update_user(current_user.id, **update_data)
        repo.commit()
        if user:
            return _to_response(user)

    return _to_response(current_user)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Upload avatar for the current user. Max 2MB, JPG/PNG/WEBP only."""
    avatar_svc = get_avatar_service()

    content = await file.read()
    mime = file.content_type or ""

    try:
        avatar_svc.validate(mime, len(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    avatar_url = avatar_svc.save(current_user.id, content, mime)

    repo = Repository(db)
    user = repo.update_user(current_user.id, avatar_path=avatar_url)
    repo.commit()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)


@router.delete("/me/avatar", response_model=UserResponse)
def delete_my_avatar(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove current user's avatar."""
    if current_user.avatar_path:
        get_avatar_service().delete(current_user.avatar_path)

    repo = Repository(db)
    user = repo.update_user(current_user.id, avatar_path=None)
    repo.commit()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)


@router.post("/me/password", response_model=MessageResponse)
def change_my_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """Change current user's password (requires current password)."""
    if not _verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if request.new_password == request.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from current")

    repo = Repository(db)
    repo.update_user(current_user.id, password_hash=_hash_password(request.new_password))
    repo.session.flush()  # Ensure the hash is written before commit
    repo.commit()
    return MessageResponse(message="Password changed successfully")
