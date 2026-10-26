"""Auth routes — login, logout, me, register, activate, forgot-password, reset-password."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from integrity_checker.api.deps import get_current_user, get_db
from integrity_checker.api.services.email_service import get_email_service
from integrity_checker.billing.plans import get_user_subscription_summary
from integrity_checker.config import get_settings, is_test_runtime
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

logger = logging.getLogger(__name__)

router = APIRouter()

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


class _SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter for auth endpoints."""

    def __init__(self, max_attempts: int = 10, window_seconds: float = 60.0) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self.enforce_in_tests: bool = False

    def check(self, key: str) -> None:
        """Raise HTTP 429 if key has exceeded max_attempts within window_seconds."""
        if is_test_runtime() and not self.enforce_in_tests:
            return
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            history = [t for t in self._attempts.get(key, []) if t > cutoff]
            if len(history) >= self.max_attempts:
                self._attempts[key] = history
                raise HTTPException(
                    status_code=429,
                    detail="Too many authentication attempts. Please try again in a minute.",
                )
            self._attempts[key] = history

    def record_failure(self, key: str) -> None:
        """Record a failed attempt for key."""
        if is_test_runtime() and not self.enforce_in_tests:
            return
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            history = [t for t in self._attempts.get(key, []) if t > cutoff]
            history.append(now)
            self._attempts[key] = history

    def reset(self, key: str) -> None:
        """Clear attempts for key after a successful login."""
        with self._lock:
            self._attempts.pop(key, None)

    def clear_all(self) -> None:
        with self._lock:
            self._attempts.clear()


_login_rate_limiter = _SlidingWindowRateLimiter(max_attempts=10, window_seconds=60.0)


def _is_demo_enabled() -> bool:
    """Check if demo users should be enabled at runtime (never in production)."""
    settings = get_settings()
    app_env = (os.getenv("APP_ENV") or settings.app.env or "").strip().lower()
    demo_enabled = os.getenv("DEMO_USERS_ENABLED", "").strip().lower()

    # Never allow demo users in production
    if app_env in ("production", "prod", "live"):
        return False

    # Disabled explicitly
    if demo_enabled in ("false", "0", "no"):
        return False

    # Enabled explicitly (in non-production)
    if demo_enabled in ("true", "1", "yes"):
        return True

    # Auto-enable in test/dev environments
    if app_env in ("test", "testing", "development", "dev") or is_test_runtime():
        return True

    return False


def _get_hardcoded_users() -> dict[str, tuple[str, str]]:
    """Load hardcoded credentials if demo mode is enabled."""
    if not _is_demo_enabled():
        return {}

    return {
        "admin": ("admin123", "admin"),
        "teacher": ("teacher123", "teacher"),
        "user": ("user123", "user"),
    }


# Load hardcoded users - this is checked at runtime via _is_demo_enabled()
# Keeping this for backwards compatibility, but login should use _get_hardcoded_users()
HARDCODED_USERS: dict[str, tuple[str, str]] = {}  # Will be checked via _is_demo_enabled() in login

# Default emails for the hardcoded demo users (assigned on first login)
HARDCODED_USER_EMAILS = {
    "admin": "admin@example.com",
    "teacher": "teacher@example.com",
    "user": "user@example.com",
}

# Default full names for the hardcoded demo users
HARDCODED_USER_FULL_NAMES = {
    "admin": "Administrator",
    "teacher": "Demo Teacher",
    "user": "Demo User",
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)
    institution: str | None = Field(default=None, max_length=255)
    lang: str = "vi"


class RegisterResponse(BaseModel):
    message: str
    username: str
    email: str
    requires_activation: bool = True
    email_sent: bool = True


class ActivateAccountRequest(BaseModel):
    token: str


class ActivateAccountResponse(BaseModel):
    message: str
    username: str
    email: str
    activated: bool = True
    already_active: bool = False


class ResendActivationRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    lang: str = "vi"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    lang: str = "vi"


class VerifyResetTokenResponse(BaseModel):
    valid: bool
    username: str | None = None
    email: str | None = None
    reason: str | None = None
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=128)
    lang: str = "vi"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    role: str
    is_active: bool = True
    email_verified: bool = True
    avatar_url: str | None = None
    last_login_at: str | None = None
    created_at: str | None = None
    institution: str | None = None
    can_override_verdicts: bool = False
    plan_tier: str = "basic"
    billing_cycle: str | None = None
    subscription_status: str = "active"
    cancel_at_period_end: bool = False
    current_period_end: str | None = None
    quota: dict | None = None


class MessageResponse(BaseModel):
    message: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_response_dict(user: User) -> dict:
    sub = get_user_subscription_summary(user)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": bool(user.is_active),
        "email_verified": bool(getattr(user, "email_verified", True)),
        "avatar_url": user.avatar_path,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "institution": user.institution,
        "can_override_verdicts": bool(user.can_override_verdicts),
        "plan_tier": sub["plan_tier"],
        "billing_cycle": sub["billing_cycle"],
        "subscription_status": sub["subscription_status"],
        "cancel_at_period_end": sub["cancel_at_period_end"],
        "current_period_end": sub["current_period_end"],
        "quota": sub["quota"],
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
    """Login with username/email and password.

    Supports both hardcoded demo credentials (admin/user) and any user stored in
    the database. If a user exists in the DB, their stored password hash is used
    (allowing admin-created users and password changes to work). Hardcoded credentials
    create the user on first login if needed.
    """
    repo = Repository(db)
    user: User | None = None
    identifier = request.username.strip()
    rate_key = identifier.lower()
    _login_rate_limiter.check(rate_key)

    # Check DB first by username, then by email if identifier contains '@'
    db_user = repo.get_user_by_username(identifier)
    if not db_user and "@" in identifier:
        db_user = repo.get_user_by_email(identifier)

    if db_user:
        user = db_user
        if not _verify_password(request.password, user.password_hash):
            _login_rate_limiter.record_failure(rate_key)
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not user.is_active:
            if not getattr(user, "email_verified", True):
                raise HTTPException(
                    status_code=403,
                    detail="ACCOUNT_NOT_ACTIVATED: Account is not activated yet. Please check your email for the activation link.",
                )
            raise HTTPException(
                status_code=403,
                detail="ACCOUNT_DEACTIVATED: Your account has been deactivated by an administrator.",
            )
    else:
        # No DB user — check hardcoded credentials (for demo/admin accounts)
        hardcoded_users = _get_hardcoded_users()
        if identifier not in hardcoded_users:
            _login_rate_limiter.record_failure(rate_key)
            raise HTTPException(status_code=401, detail="Invalid username or password")
        expected_password, role = hardcoded_users[identifier]
        if request.password != expected_password:
            _login_rate_limiter.record_failure(rate_key)
            raise HTTPException(status_code=401, detail="Invalid username or password")
        # Create DB entry on first login for hardcoded users
        password_hash = _hash_password(request.password)
        user = repo.create_user(
            username=identifier,
            password_hash=password_hash,
            role=role,
            email=HARDCODED_USER_EMAILS.get(identifier),
            full_name=HARDCODED_USER_FULL_NAMES.get(identifier),
            is_active=True,
            email_verified=True,
        )

    _login_rate_limiter.reset(rate_key)

    # Stamp last_login_at every login
    repo.update_last_login(user.id)

    # Create session
    token, expires_at = _create_token(user)
    repo.create_session(user.id, token, expires_at)
    repo.commit()

    return LoginResponse(token=token, user=_to_response_dict(user))


@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, db=Depends(get_db)):
    """Self-register a new account (creates inactive user and sends HTML activation email)."""
    username = request.username.strip()
    if len(username) < 3 or len(username) > 50 or not _USERNAME_RE.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username must be 3-50 characters and contain only letters, numbers, dots, underscores, or hyphens.",
        )

    email = request.email.strip().lower()
    repo = Repository(db)

    if repo.get_user_by_username(username) or username in _get_hardcoded_users():
        raise HTTPException(status_code=400, detail="Username already exists")

    if repo.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = _hash_password(request.password)
    full_name = request.full_name.strip() if request.full_name else None
    institution = request.institution.strip() if request.institution else None

    user = repo.create_user(
        username=username,
        password_hash=password_hash,
        role="user",
        email=email,
        full_name=full_name,
        institution=institution,
        is_active=False,
        email_verified=False,
    )

    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auth.activation_expire_hours)
    raw_token, _ = repo.create_auth_token(user.id, "activation", expires_at)
    repo.commit()

    email_sent = True
    try:
        get_email_service().send_activation_email(
            to_email=email,
            username=username,
            full_name=full_name,
            raw_token=raw_token,
            institution=institution,
            lang=request.lang,
        )
    except Exception as exc:
        logger.error("Failed to dispatch activation email to %s: %s", email, exc)
        email_sent = False

    return RegisterResponse(
        message="Account created successfully. Please check your email to activate your account.",
        username=username,
        email=email,
        requires_activation=True,
        email_sent=email_sent,
    )


def _perform_account_activation(raw_token: str, db) -> ActivateAccountResponse:
    repo = Repository(db)
    token_row = repo.get_auth_token(raw_token, "activation")
    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid activation token.")

    user = repo.get_user_by_id(token_row.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if token_row.used_at is not None:
        if user.is_active and getattr(user, "email_verified", False):
            return ActivateAccountResponse(
                message="Account is already activated. You can sign in now.",
                username=user.username,
                email=user.email or "",
                activated=True,
                already_active=True,
            )
        raise HTTPException(
            status_code=400,
            detail="This activation link has already been used. Please request a new activation email.",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(token_row.expires_at) < now:
        raise HTTPException(
            status_code=400,
            detail="Activation link has expired. Please request a new activation email.",
        )

    repo.update_user(user.id, is_active=True, email_verified=True)
    repo.mark_auth_token_used(token_row)
    repo.commit()

    return ActivateAccountResponse(
        message="Account activated successfully! You can now sign in.",
        username=user.username,
        email=user.email or "",
        activated=True,
        already_active=False,
    )


@router.post("/activate", response_model=ActivateAccountResponse)
def activate_account(request: ActivateAccountRequest, db=Depends(get_db)):
    """Activate an account using the one-time token sent via email."""
    return _perform_account_activation(request.token, db)


@router.get("/activate", response_model=ActivateAccountResponse)
def activate_account_get(token: str = Query(..., min_length=1), db=Depends(get_db)):
    """GET variant of account activation for direct token verification."""
    return _perform_account_activation(token, db)


@router.post("/resend-activation", response_model=MessageResponse)
def resend_activation(request: ResendActivationRequest, db=Depends(get_db)):
    """Resend the account activation email by email or username."""
    identifier = request.identifier.strip()
    repo = Repository(db)

    user = repo.get_user_by_email(identifier) if "@" in identifier else repo.get_user_by_username(identifier)
    if not user:
        user = repo.get_user_by_username(identifier) or repo.get_user_by_email(identifier)

    if not user or not user.email:
        raise HTTPException(
            status_code=404,
            detail="No account found matching that username or email.",
        )

    if user.is_active and getattr(user, "email_verified", True):
        raise HTTPException(
            status_code=400,
            detail="Account is already activated. You can sign in now.",
        )

    now = datetime.now(timezone.utc)
    if not is_test_runtime():
        latest = repo.get_latest_auth_token_for_user(user.id, "activation")
        if latest and (now - _ensure_utc(latest.created_at)).total_seconds() < 60:
            raise HTTPException(
                status_code=429,
                detail="Please wait 60 seconds before requesting another activation email.",
            )

    settings = get_settings()
    expires_at = now + timedelta(hours=settings.auth.activation_expire_hours)
    raw_token, _ = repo.create_auth_token(user.id, "activation", expires_at)
    repo.commit()

    try:
        get_email_service().send_activation_email(
            to_email=user.email,
            username=user.username,
            full_name=user.full_name,
            raw_token=raw_token,
            institution=user.institution,
            lang=request.lang,
        )
    except Exception as exc:
        logger.error("Failed to dispatch resent activation email to %s: %s", user.email, exc)

    return MessageResponse(
        message="A new activation email has been sent. Please check your inbox."
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: ForgotPasswordRequest, db=Depends(get_db)):
    """Issue a one-time password reset token and send the HTML reset email."""
    email = request.email.strip().lower()
    repo = Repository(db)
    user = repo.get_user_by_email(email)

    generic_msg = "If an account with that email exists, a password reset link has been sent."
    if not user or not user.email:
        return MessageResponse(message=generic_msg)

    now = datetime.now(timezone.utc)
    if not is_test_runtime():
        latest = repo.get_latest_auth_token_for_user(user.id, "password_reset")
        if latest and (now - _ensure_utc(latest.created_at)).total_seconds() < 30:
            # Return identical 200 response to avoid account enumeration oracle
            return MessageResponse(message=generic_msg)

    settings = get_settings()
    expires_at = now + timedelta(minutes=settings.auth.reset_expire_minutes)
    raw_token, _ = repo.create_auth_token(user.id, "password_reset", expires_at)
    repo.commit()

    try:
        get_email_service().send_password_reset_email(
            to_email=user.email,
            username=user.username,
            full_name=user.full_name,
            raw_token=raw_token,
            lang=request.lang,
        )
    except Exception as exc:
        logger.error("Failed to dispatch password reset email to %s: %s", user.email, exc)

    return MessageResponse(message=generic_msg)


@router.get("/verify-reset-token", response_model=VerifyResetTokenResponse)
def verify_reset_token(token: str = Query(..., min_length=1), db=Depends(get_db)):
    """Verify whether a password reset token is valid before showing the new password form."""
    repo = Repository(db)
    token_row = repo.get_auth_token(token, "password_reset")
    if not token_row:
        return VerifyResetTokenResponse(
            valid=False,
            reason="invalid",
            message="Invalid password reset link.",
        )

    if token_row.used_at is not None:
        return VerifyResetTokenResponse(
            valid=False,
            reason="used",
            message="This password reset link has already been used.",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(token_row.expires_at) < now:
        return VerifyResetTokenResponse(
            valid=False,
            reason="expired",
            message="This password reset link has expired.",
        )

    user = repo.get_user_by_id(token_row.user_id)
    if not user:
        return VerifyResetTokenResponse(
            valid=False,
            reason="invalid",
            message="User account not found.",
        )

    return VerifyResetTokenResponse(
        valid=True,
        username=user.username,
        email=user.email,
        message="Token is valid.",
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(request: ResetPasswordRequest, db=Depends(get_db)):
    """Reset a user's password using a valid password_reset token and revoke old sessions."""
    repo = Repository(db)
    token_row = repo.get_auth_token(request.token, "password_reset")
    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid password reset token.")

    if token_row.used_at is not None:
        raise HTTPException(
            status_code=400,
            detail="This password reset link has already been used.",
        )

    now = datetime.now(timezone.utc)
    if _ensure_utc(token_row.expires_at) < now:
        raise HTTPException(
            status_code=400,
            detail="Password reset link has expired. Please request a new one.",
        )

    user = repo.get_user_by_id(token_row.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    update_fields: dict = {"password_hash": _hash_password(request.new_password)}
    # If user had not activated via email yet, proving email ownership via reset link activates it
    if not getattr(user, "email_verified", True):
        update_fields["email_verified"] = True
        update_fields["is_active"] = True

    repo.update_user(user.id, **update_fields)
    repo.mark_auth_token_used(token_row)
    repo.delete_user_sessions(user.id)
    repo.commit()

    if user.email:
        try:
            get_email_service().send_password_changed_email(
                to_email=user.email,
                username=user.username,
                full_name=user.full_name,
                lang=request.lang,
            )
        except Exception as exc:
            logger.warning("Could not send password changed notification to %s: %s", user.email, exc)

    return MessageResponse(
        message="Password has been reset successfully. You can now sign in with your new password."
    )


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
        token = authorization[7:].strip()
        # Try to delete session - will silently succeed if session doesn't exist
        repo.delete_session(token)

    repo.commit()
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info (full profile)."""
    return UserResponse(**_to_response_dict(current_user))


@router.get("/dev/latest-email")
def get_latest_dev_email(email: str = Query(..., min_length=3)):
    """Dev/test-only helper to inspect the latest transactional email sent to an address."""
    settings = get_settings()
    app_env = (os.getenv("APP_ENV") or settings.app.env or "").strip().lower()
    demo_enabled = os.getenv("DEMO_USERS_ENABLED", "").strip().lower() in ("true", "1", "yes")
    if not demo_enabled:
        if app_env in ("production", "prod", "live"):
            raise HTTPException(status_code=404, detail="Not found")
        if app_env not in ("development", "dev", "test", "testing") and not is_test_runtime():
            raise HTTPException(status_code=404, detail="Not found")
        if not settings.app.debug and not is_test_runtime():
            raise HTTPException(status_code=404, detail="Not found")

    target = email.strip().lower()
    outbox = get_email_service().outbox
    for msg in reversed(outbox):
        if msg.to_email.strip().lower() == target:
            return {
                "to_email": msg.to_email,
                "subject": msg.subject,
                "template_type": msg.template_type,
                "action_url": msg.action_url,
                "token": msg.token,
                "delivered_via_smtp": msg.delivered_via_smtp,
                "sent_at": msg.sent_at.isoformat(),
            }
    raise HTTPException(status_code=404, detail="No email found for recipient")
