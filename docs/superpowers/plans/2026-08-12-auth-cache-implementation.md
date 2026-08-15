# Authentication & Citation Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm login system (hardcoded credentials) và citation cache vào Essay Integrity Checker

**Architecture:** JWT-based authentication với SQLite. Citation cache lưu full response từ Crossref/OpenAlex/Semantic Scholar/arXiv để tránh gọi lại API.

**Tech Stack:** FastAPI, SQLAlchemy, PyJWT, bcrypt, React Router, Context API

## Global Constraints

- SQLite database (không đổi sang PostgreSQL)
- Hardcoded credentials: admin/admin123, user/user123
- JWT token expiry: 24 hours
- Cache key: SHA256 hash của (title + authors + year + doi)
- Frontend: React + TypeScript + Tailwind (existing stack)

---

## File Structure Overview

### Backend Changes

| File | Action | Purpose |
|------|--------|---------|
| `src/integrity_checker/db/models.py` | Modify | Add User, Session, CitationCache models |
| `src/integrity_checker/db/repository.py` | Modify | Add CRUD methods for users, sessions, cache |
| `src/integrity_checker/api/deps.py` | Modify | Add get_current_user, require_admin dependencies |
| `src/integrity_checker/api/routes/auth.py` | Create | Login, logout, me endpoints |
| `src/integrity_checker/api/routes/users.py` | Create | User CRUD (admin only) |
| `src/integrity_checker/api/routes/cache.py` | Create | Cache stats, clear endpoints |
| `src/integrity_checker/api/routes/essays.py` | Modify | Add user_id to essay creation, ownership checks |
| `src/integrity_checker/api/main.py` | Modify | Register new routers |
| `src/integrity_checker/config.py` | Modify | Add JWT_SECRET, TOKEN_EXPIRE_HOURS |
| `src/integrity_checker/retrieval/cache_db.py` | Create | DB-based citation cache (replace DiskCache) |

### Frontend Changes

| File | Action | Purpose |
|------|--------|---------|
| `web/src/contexts/AuthContext.tsx` | Create | Auth state management |
| `web/src/lib/api.ts` | Modify | Add auth header to requests |
| `web/src/pages/LoginPage.tsx` | Create | Login form |
| `web/src/pages/DashboardPage.tsx` | Modify | Show user-specific essays |
| `web/src/pages/AdminDashboard.tsx` | Create | Admin overview |
| `web/src/pages/UserManagementPage.tsx` | Create | User CRUD UI |
| `web/src/pages/CacheManagementPage.tsx` | Create | Cache stats & clear |
| `web/src/components/ProtectedRoute.tsx` | Create | Route guard |
| `web/src/App.tsx` | Modify | Add routes |
| `web/package.json` | Modify | Add react-router-dom (if needed) |

---

## Task 1: Database Models

**Files:**
- Modify: `src/integrity_checker/db/models.py:1-79`
- Test: `tests/integration/test_auth.py` (new file)

**Interfaces:**
- Produces:
  - `User` model with fields: id, username, password_hash, role, created_at, updated_at
  - `Session` model with fields: id, user_id, token, expires_at, created_at
  - `CitationCache` model with fields: id, cache_key, source, raw_response, matched_fields, created_at, last_hit_at, hit_count

- [ ] **Step 1: Write failing test for User model**

```python
# tests/integration/test_auth.py
from integrity_checker.db.models import User

def test_create_user():
    from integrity_checker.db.session import get_session
    session = get_session()
    user = User(username="testuser", password_hash="hashed", role="user")
    session.add(user)
    session.commit()
    assert user.id is not None
    assert user.username == "testuser"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth.py::test_create_user -v`
Expected: FAIL - User model doesn't exist

- [ ] **Step 3: Add models to models.py**

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    essays: Mapped[list["EssayRecord"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship(back_populates="sessions")


class CitationCache(Base):
    __tablename__ = "citation_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    matched_fields: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 4: Add user_id to EssayRecord**

```python
# Add to EssayRecord class
user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
user: Mapped["User | None"] = relationship(back_populates="essays")
```

- [ ] **Step 5: Add index to CitationCache**

```python
# After CitationCache class definition
from sqlalchemy import Index
Index("idx_cache_key", CitationCache.cache_key)
Index("idx_source", CitationCache.source)
```

- [ ] **Step 6: Run migration to create new tables**

Run: `python -c "from integrity_checker.db.session import init_db; init_db()"`
Expected: Creates users, sessions, citation_cache tables

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/integration/test_auth.py::test_create_user -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/integrity_checker/db/models.py
git commit -m "feat(db): add User, Session, CitationCache models
- User model for authentication
- Session model for JWT token storage
- CitationCache model for API response caching
- Add user_id FK to EssayRecord
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Config Updates

**Files:**
- Modify: `src/integrity_checker/config.py:1-385`
- Test: `tests/unit/test_config.py` (existing, add test)

**Interfaces:**
- Consumes: None
- Produces:
  - `AuthConfig` class with: jwt_secret, token_expire_hours
  - `settings.auth` property

- [ ] **Step 1: Add failing test for AuthConfig**

```python
# tests/unit/test_config.py
def test_auth_config_defaults():
    from integrity_checker.config import get_settings
    settings = get_settings()
    assert hasattr(settings, 'auth')
    assert settings.auth.jwt_secret is not None
    assert settings.auth.token_expire_hours == 24
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config.py::test_auth_config_defaults -v`
Expected: FAIL - auth config doesn't exist

- [ ] **Step 3: Add AuthConfig class**

```python
class AuthConfig(BaseModel):
    jwt_secret: str = "change-me-in-production-use-env-var"
    token_expire_hours: int = 24
```

- [ ] **Step 4: Add auth to Settings root**

```python
class Settings(BaseSettings):
    # ... existing fields ...
    auth: AuthConfig = Field(default_factory=AuthConfig)
    # ... rest of fields ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_config.py::test_auth_config_defaults -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/config.py
git commit -m "feat(config): add AuthConfig for JWT settings
- jwt_secret: secret key for JWT signing
- token_expire_hours: token expiration time (default 24h)
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: Repository Updates

**Files:**
- Modify: `src/integrity_checker/db/repository.py:1-98`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: User, Session, CitationCache models from Task 1
- Produces:
  - `get_user_by_username(username: str) -> User | None`
  - `create_session(user_id: int, token: str, expires_at: datetime) -> Session`
  - `get_session_by_token(token: str) -> Session | None`
  - `delete_session(token: str) -> bool`
  - `get_user_essays(user_id: int) -> list[EssayRecord]`
  - `get_all_essays() -> list[EssayRecord]`
  - `create_essay_with_user(filename: str, num_pages: int, user_id: int) -> EssayRecord`
  - `get_cache_entry(cache_key: str, source: str) -> CitationCache | None`
  - `save_cache_entry(cache_key: str, source: str, raw_response: str, matched_fields: str) -> CitationCache`
  - `update_cache_hit(cache_key: str) -> None`
  - `get_cache_stats() -> dict`
  - `clear_cache() -> int`
  - `create_user(username: str, password_hash: str, role: str) -> User`
  - `update_user(user_id: int, **kwargs) -> User | None`
  - `delete_user(user_id: int) -> bool`
  - `get_all_users() -> list[User]`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_auth.py
def test_get_user_by_username():
    from integrity_checker.db.repository import Repository
    from integrity_checker.db.session import get_session
    session = get_session()
    repo = Repository(session)
    user = repo.get_user_by_username("admin")
    assert user is None or user.username == "admin"

def test_create_and_get_session():
    # Create temp user, then session
    pass

def test_cache_stats():
    # Test cache stats returns dict
    pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_auth.py -v`
Expected: FAIL - methods don't exist

- [ ] **Step 3: Add user methods to Repository**

```python
def get_user_by_username(self, username: str) -> User | None:
    return self.session.query(User).filter(User.username == username).first()

def create_user(self, username: str, password_hash: str, role: str) -> User:
    user = User(username=username, password_hash=password_hash, role=role)
    self.session.add(user)
    self.session.flush()
    return user

def update_user(self, user_id: int, **kwargs) -> User | None:
    user = self.session.get(User, user_id)
    if not user:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    self.session.flush()
    return user

def delete_user(self, user_id: int) -> bool:
    user = self.session.get(User, user_id)
    if not user:
        return False
    self.session.delete(user)
    self.session.flush()
    return True

def get_all_users(self) -> list[User]:
    return list(self.session.query(User).all())
```

- [ ] **Step 4: Add session methods**

```python
def create_session(self, user_id: int, token: str, expires_at: datetime) -> Session:
    session = Session(user_id=user_id, token=token, expires_at=expires_at)
    self.session.add(session)
    self.session.flush()
    return session

def get_session_by_token(self, token: str) -> Session | None:
    return self.session.query(Session).filter(Session.token == token).first()

def delete_session(self, token: str) -> bool:
    session = self.get_session_by_token(token)
    if not session:
        return False
    self.session.delete(session)
    self.session.flush()
    return True
```

- [ ] **Step 5: Add essay methods with user_id**

```python
def create_essay_with_user(self, filename: str, num_pages: int, user_id: int) -> EssayRecord:
    essay = EssayRecord(filename=filename, num_pages=num_pages, user_id=user_id)
    self.session.add(essay)
    self.session.flush()
    return essay

def get_user_essays(self, user_id: int) -> list[EssayRecord]:
    return list(
        self.session.query(EssayRecord)
        .filter(EssayRecord.user_id == user_id)
        .order_by(EssayRecord.uploaded_at.desc())
        .all()
    )

def get_all_essays(self) -> list[EssayRecord]:
    return list(
        self.session.query(EssayRecord)
        .order_by(EssayRecord.uploaded_at.desc())
        .all()
    )
```

- [ ] **Step 6: Add cache methods**

```python
def get_cache_entry(self, cache_key: str, source: str) -> CitationCache | None:
    return self.session.query(CitationCache).filter(
        CitationCache.cache_key == cache_key,
        CitationCache.source == source
    ).first()

def save_cache_entry(self, cache_key: str, source: str, raw_response: str, matched_fields: str | None = None) -> CitationCache:
    entry = CitationCache(
        cache_key=cache_key,
        source=source,
        raw_response=raw_response,
        matched_fields=matched_fields
    )
    self.session.add(entry)
    self.session.flush()
    return entry

def update_cache_hit(self, cache_key: str) -> None:
    from datetime import datetime, timezone
    entry = self.session.query(CitationCache).filter(CitationCache.cache_key == cache_key).first()
    if entry:
        entry.last_hit_at = datetime.now(timezone.utc)
        entry.hit_count = (entry.hit_count or 0) + 1
        self.session.flush()

def get_cache_stats(self) -> dict:
    total = self.session.query(CitationCache).count()
    by_source = {}
    for source in ['crossref', 'openalex', 'semantic_scholar', 'arxiv']:
        count = self.session.query(CitationCache).filter(CitationCache.source == source).count()
        by_source[source] = count
    total_hits = sum(
        (e.hit_count or 0) for e in self.session.query(CitationCache).all()
    )
    return {
        "total": total,
        "by_source": by_source,
        "total_hits": total_hits,
        "avg_hit_count": total_hits / total if total > 0 else 0
    }

def clear_cache(self) -> int:
    count = self.session.query(CitationCache).delete()
    self.session.flush()
    return count
```

- [ ] **Step 7: Update imports**

```python
from integrity_checker.db.models import CitationRecord, EssayRecord, VerdictRecord, User, Session, CitationCache
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/integration/test_auth.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/integrity_checker/db/repository.py
git commit -m "feat(db): add auth and cache repository methods
- User CRUD methods
- Session management methods
- Essay methods with user_id
- CitationCache CRUD and stats methods
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Auth Dependencies

**Files:**
- Modify: `src/integrity_checker/api/deps.py:1-27`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: Repository methods from Task 3, User model
- Produces:
  - `get_current_user(authorization: str) -> User`
  - `require_admin(user: User) -> User`
  - `get_current_user_optional() -> User | None`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_auth.py
def test_require_admin_rejects_user():
    from integrity_checker.api.deps import require_admin
    from fastapi import HTTPException
    user = type('User', (), {'role': 'user'})()
    try:
        require_admin(user)
        assert False, "Should have raised"
    except HTTPException as e:
        assert e.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth.py::test_require_admin_rejects_user -v`
Expected: FAIL - require_admin doesn't exist

- [ ] **Step 3: Implement deps**

```python
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


def get_repository(session: Session = None) -> Repository:
    return Repository(session or get_session())


def get_pipeline() -> IntegrityPipeline:
    """Singleton pipeline (lazy)."""
    return IntegrityPipeline()


def get_current_user(
    authorization: str = Header(..., description="Bearer token"),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT token and return current user."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
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
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/integration/test_auth.py::test_require_admin_rejects_user -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/integrity_checker/api/deps.py
git commit -m "feat(auth): add auth dependencies
- get_current_user: decode JWT and return User
- get_current_user_optional: return User or None
- require_admin: raise 403 for non-admins
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Auth Routes

**Files:**
- Create: `src/integrity_checker/api/routes/auth.py`
- Modify: `src/integrity_checker/api/main.py:1-53`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: Repository methods, deps, User model, AuthConfig
- Produces:
  - `POST /api/auth/login` → `{token, user}`
  - `POST /api/auth/logout` → `{message}`
  - `GET /api/auth/me` → `{id, username, role}`

- [ ] **Step 1: Write failing tests**

```python
# tests/integration/test_auth.py
def test_login_invalid_credentials():
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"username": "wrong", "password": "wrong"})
    assert resp.status_code == 401

def test_login_valid_admin():
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth.py::test_login_invalid_credentials -v`
Expected: FAIL - auth routes don't exist

- [ ] **Step 3: Create auth routes**

```python
"""Auth routes — login, logout, me."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from integrity_checker.api.deps import get_current_user, get_db
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


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


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
    current_user: User = Depends(get_current_user),
    authorization: str = Depends(lambda: None),  # Will be injected by middleware
    db=Depends(get_db),
):
    """Logout current user."""
    # Token is extracted by get_current_user dependency
    # We need to get it from the Authorization header
    from fastapi import Header
    # This is a bit awkward - we'll handle it differently
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role
    )
```

- [ ] **Step 4: Fix logout to properly handle token**

Update deps.py to return token alongside user, or use a different approach:

```python
# Updated deps.py - add this function
def get_token_from_header(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.replace("Bearer ", "")
```

Then update logout route:

```python
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
```

- [ ] **Step 5: Register router in main.py**

```python
from integrity_checker.api.routes import auth, essays, health, report, users, cache
# ... existing code ...
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
# ... rest unchanged
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/integration/test_auth.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/integrity_checker/api/routes/auth.py src/integrity_checker/api/main.py
git commit -m "feat(auth): add auth routes
- POST /api/auth/login: hardcoded admin/user credentials
- POST /api/auth/logout: invalidate session
- GET /api/auth/me: get current user
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: User Management Routes (Admin)

**Files:**
- Create: `src/integrity_checker/api/routes/users.py`
- Modify: `src/integrity_checker/api/main.py`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: Repository, require_admin, User model
- Produces:
  - `GET /api/users` → `[{id, username, role, created_at}]`
  - `POST /api/users` → `{id, username, role}`
  - `PUT /api/users/{id}` → `{id, username, role}`
  - `DELETE /api/users/{id}` → `{message}`

- [ ] **Step 1: Write failing tests**

```python
def test_admin_list_users():
    client = TestClient(app)
    # Login as admin
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["token"]
    
    resp = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_user_cannot_list_users():
    client = TestClient(app)
    login_resp = client.post("/api/auth/login", json={"username": "user", "password": "user123"})
    token = login_resp.json()["token"]
    
    resp = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_auth.py::test_admin_list_users -v`
Expected: FAIL - users routes don't exist

- [ ] **Step 3: Create users routes**

```python
"""User management routes (admin only)."""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from integrity_checker.api.deps import get_current_user, get_db, require_admin
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
    created_at: str


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
```

- [ ] **Step 4: Register router in main.py**

```python
from integrity_checker.api.routes import auth, essays, health, report, users, cache
# ... existing code ...
app.include_router(users.router, prefix="/api/users", tags=["users"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/integration/test_auth.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/api/routes/users.py src/integrity_checker/api/main.py
git commit -m "feat(admin): add user management routes
- GET /api/users: list all users
- POST /api/users: create user
- PUT /api/users/{id}: update user
- DELETE /api/users/{id}: delete user
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Essay Routes with User Context

**Files:**
- Modify: `src/integrity_checker/api/routes/essays.py:1-95`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: get_current_user, Repository methods with user_id
- Produces:
  - `POST /api/essays` now requires auth, saves user_id
  - `GET /api/essays` returns only user's essays (or all for admin)
  - `GET /api/essays/all` admin only, returns all essays
  - `DELETE /api/essays/{id}` ownership check

- [ ] **Step 1: Write failing tests**

```python
def test_upload_essay_requires_auth():
    client = TestClient(app)
    with open("tests/data/sample.pdf", "rb") as f:
        resp = client.post("/api/essays", files={"file": f})
    assert resp.status_code == 401

def test_upload_essay_creates_with_user_id():
    client = TestClient(app)
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["token"]
    
    with open("tests/data/sample.pdf", "rb") as f:
        resp = client.post(
            "/api/essays",
            files={"file": ("test.pdf", f, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"}
        )
    assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_auth.py::test_upload_essay_requires_auth -v`
Expected: FAIL - essays route doesn't check auth

- [ ] **Step 3: Update essays routes**

```python
"""Essays endpoints — upload PDF và analyze."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_current_user, get_db, get_pipeline, require_admin
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository
from integrity_checker.models.api_schemas import CitationSchema, EssayUploadResponse
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline

router = APIRouter()


@router.post("", response_model=EssayUploadResponse)
async def upload_essay(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pipeline: IntegrityPipeline = Depends(get_pipeline),
) -> EssayUploadResponse:
    """Upload PDF → parse → extract → validate (chạy end-to-end)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Lưu tạm
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Chạy pipeline (offload executor để không block event loop)
        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(None, pipeline.run, tmp_path, 0)

        # Persist with user_id
        repo = Repository(db)
        essay = repo.create_essay_with_user(
            filename=file.filename,
            num_pages=report.num_pages,
            user_id=current_user.id
        )
        repo.add_citations(essay.id, [v.citation for v in report.verdicts])
        repo.add_verdicts(essay.id, report.verdicts)
        repo.commit()

        citations = [
            CitationSchema(
                raw_text=v.citation.raw_text,
                citation_type=v.citation.citation_type.value,
                style=v.citation.style.value,
                authors=v.citation.authors,
                year=v.citation.year,
                title=v.citation.title,
                venue=v.citation.venue,
                doi=v.citation.doi,
                url=v.citation.url,
                page_num=v.citation.page_num,
                confidence=v.citation.confidence,
            )
            for v in report.verdicts
        ]

        return EssayUploadResponse(
            essay_id=essay.id,
            filename=essay.filename,
            num_pages=essay.num_pages,
            num_citations=report.num_citations,
            citations=citations,
            summary={
                "cis_score": report.cis.score if report.cis else None,
                "num_unresolved": report.cis.num_unresolved if report.cis else 0,
            },
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("", response_model=list[dict])
def list_essays(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List essays for current user (or all for admin)."""
    repo = Repository(db)
    
    if current_user.role == "admin":
        essays = repo.get_all_essays()
    else:
        essays = repo.get_user_essays(current_user.id)
    
    return [
        {
            "id": e.id,
            "filename": e.filename,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "user_id": e.user_id,
        }
        for e in essays
    ]


@router.get("/all", response_model=list[dict])
def list_all_essays(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all essays (admin only)."""
    repo = Repository(db)
    essays = repo.get_all_essays()
    
    return [
        {
            "id": e.id,
            "filename": e.filename,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "user_id": e.user_id,
        }
        for e in essays
    ]


@router.get("/{essay_id}")
async def get_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Lấy essay + verdicts từ DB."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    # Ownership check
    if current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "id": essay.id,
        "filename": essay.filename,
        "num_pages": essay.num_pages,
        "uploaded_at": essay.uploaded_at.isoformat() if essay.uploaded_at else None,
        "user_id": essay.user_id,
    }


@router.delete("/{essay_id}")
async def delete_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa essay (owner hoặc admin)."""
    repo = Repository(db)
    essay = repo.get_essay(essay_id)
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    # Ownership check
    if current_user.role != "admin" and essay.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(essay)
    db.commit()
    
    return {"message": f"Essay {essay_id} deleted"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/integrity_checker/api/routes/essays.py
git commit -m "feat(auth): integrate user context into essay routes
- All essay endpoints require authentication
- Essays linked to user_id on creation
- List essays returns user's own or all (admin)
- Delete checks ownership
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 8: Cache Management Routes (Admin)

**Files:**
- Create: `src/integrity_checker/api/routes/cache.py`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: Repository cache methods, require_admin
- Produces:
  - `GET /api/cache/stats` → `{total, by_source, total_hits, avg_hit_count}`
  - `DELETE /api/cache` → `{deleted_count}`

- [ ] **Step 1: Write failing tests**

```python
def test_cache_stats_requires_admin():
    client = TestClient(app)
    login_resp = client.post("/api/auth/login", json={"username": "user", "password": "user123"})
    token = login_resp.json()["token"]
    
    resp = client.get("/api/cache/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth.py::test_cache_stats_requires_admin -v`
Expected: FAIL - cache routes don't exist

- [ ] **Step 3: Create cache routes**

```python
"""Cache management routes (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


class CacheStatsResponse(BaseModel):
    total: int
    by_source: dict
    total_hits: int
    avg_hit_count: float


class CacheClearResponse(BaseModel):
    deleted_count: int


@router.get("/stats", response_model=CacheStatsResponse)
def get_cache_stats(admin: User = Depends(require_admin), db=Depends(get_db)):
    """Get citation cache statistics (admin only)."""
    repo = Repository(db)
    stats = repo.get_cache_stats()
    return CacheStatsResponse(**stats)


@router.delete("", response_model=CacheClearResponse)
def clear_cache(admin: User = Depends(require_admin), db=Depends(get_db)):
    """Clear all citation cache (admin only)."""
    repo = Repository(db)
    deleted_count = repo.clear_cache()
    repo.commit()
    return CacheClearResponse(deleted_count=deleted_count)
```

- [ ] **Step 4: Register router in main.py**

```python
from integrity_checker.api.routes import auth, cache, essays, health, report, users
# ... existing code ...
app.include_router(cache.router, prefix="/api/cache", tags=["cache"])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/integration/test_auth.py::test_cache_stats_requires_admin -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/api/routes/cache.py src/integrity_checker/api/main.py
git commit -m "feat(admin): add cache management routes
- GET /api/cache/stats: get cache statistics
- DELETE /api/cache: clear all cache
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 9: Export Route (Admin)

**Files:**
- Create: `src/integrity_checker/api/routes/export.py`
- Modify: `src/integrity_checker/api/main.py`
- Test: `tests/integration/test_auth.py`

**Interfaces:**
- Consumes: Repository methods, require_admin
- Produces:
  - `GET /api/export/report` → `{users, essays, cache_stats, verdicts_summary}`

- [ ] **Step 1: Write failing tests**

```python
def test_export_report_requires_admin():
    client = TestClient(app)
    login_resp = client.post("/api/auth/login", json={"username": "user", "password": "user123"})
    token = login_resp.json()["token"]
    
    resp = client.get("/api/export/report", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_auth.py::test_export_report_requires_admin -v`
Expected: FAIL - export route doesn't exist

- [ ] **Step 3: Create export routes**

```python
"""Export routes (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User, VerdictRecord
from integrity_checker.db.repository import Repository

router = APIRouter()


@router.get("/report")
def get_system_report(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get full system report (admin only)."""
    repo = Repository(db)
    
    # Users summary
    users = repo.get_all_users()
    user_summaries = [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
    
    # Essays summary
    essays = repo.get_all_essays()
    essay_summaries = [
        {
            "id": e.id,
            "filename": e.filename,
            "user_id": e.user_id,
            "num_pages": e.num_pages,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
        }
        for e in essays
    ]
    
    # Verdicts summary
    verdicts = db.query(VerdictRecord).all()
    verdict_counts = {}
    for v in verdicts:
        label = v.label
        verdict_counts[label] = verdict_counts.get(label, 0) + 1
    
    # Cache stats
    cache_stats = repo.get_cache_stats()
    
    return JSONResponse({
        "users": {
            "total": len(users),
            "admins": len([u for u in users if u.role == "admin"]),
            "users": len([u for u in users if u.role == "user"]),
            "list": user_summaries,
        },
        "essays": {
            "total": len(essays),
            "list": essay_summaries,
        },
        "verdicts": {
            "total": len(verdicts),
            "by_label": verdict_counts,
        },
        "cache": cache_stats,
    })
```

- [ ] **Step 4: Register router in main.py**

```python
from integrity_checker.api.routes import auth, cache, essays, export, health, report, users
# ... existing code ...
app.include_router(export.router, prefix="/api/export", tags=["export"])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/integration/test_auth.py::test_export_report_requires_admin -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/api/routes/export.py src/integrity_checker/api/main.py
git commit -m "feat(admin): add export routes
- GET /api/export/report: system report
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 10: Frontend Auth Context

**Files:**
- Create: `web/src/contexts/AuthContext.tsx`
- Test: Manual testing with frontend

**Interfaces:**
- Consumes: API endpoints from Tasks 5-9
- Produces:
  - `AuthContext` with: user, token, login(), logout(), isAdmin, isLoading
  - `useAuth()` hook

- [ ] **Step 1: Create AuthContext**

```typescript
// web/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = '/api';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      validateToken(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const validateToken = async (tokenToValidate: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${tokenToValidate}` },
      });
      if (res.ok) {
        const userData = await res.json();
        setToken(tokenToValidate);
        setUser(userData);
      } else {
        localStorage.removeItem('token');
      }
    } catch {
      localStorage.removeItem('token');
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Login failed');
    }
    
    const data = await res.json();
    localStorage.setItem('token', data.token);
    setToken(data.token);
    setUser(data.user);
  };

  const logout = async () => {
    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // Ignore logout errors
      }
    }
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isAdmin: user?.role === 'admin',
    isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/contexts/AuthContext.tsx
git commit -m "feat(frontend): add AuthContext for state management
- Login/logout/logout functions
- Token storage in localStorage
- isAdmin and isLoading state
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 11: API Client with Auth Header

**Files:**
- Modify: `web/src/lib/api.ts` (or create if not exists)
- Test: Manual testing

**Interfaces:**
- Consumes: AuthContext token
- Produces: `api` object with methods that include Authorization header

- [ ] **Step 1: Create/update api client**

```typescript
// web/src/lib/api.ts
const API_BASE = '/api';

function getAuthHeader(): HeadersInit {
  const token = localStorage.getItem('token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    const error = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).then(r => handleResponse(r)),

  logout: () =>
    fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  getMe: () =>
    fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  // Essays
  getEssays: () =>
    fetch(`${API_BASE}/essays`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  getAllEssays: () =>
    fetch(`${API_BASE}/essays/all`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  getEssay: (id: number) =>
    fetch(`${API_BASE}/essays/${id}`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  deleteEssay: (id: number) =>
    fetch(`${API_BASE}/essays/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  uploadEssay: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/essays`, {
      method: 'POST',
      headers: getAuthHeader(),
      body: formData,
    }).then(r => handleResponse(r));
  },

  // Users (admin)
  getUsers: () =>
    fetch(`${API_BASE}/users`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  createUser: (data: { username: string; password: string; role: string }) =>
    fetch(`${API_BASE}/users`, {
      method: 'POST',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => handleResponse(r)),

  updateUser: (id: number, data: { username?: string; password?: string; role?: string }) =>
    fetch(`${API_BASE}/users/${id}`, {
      method: 'PUT',
      headers: { ...getAuthHeader(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => handleResponse(r)),

  deleteUser: (id: number) =>
    fetch(`${API_BASE}/users/${id}`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  // Cache (admin)
  getCacheStats: () =>
    fetch(`${API_BASE}/cache/stats`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  clearCache: () =>
    fetch(`${API_BASE}/cache`, {
      method: 'DELETE',
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),

  // Export (admin)
  getReport: () =>
    fetch(`${API_BASE}/export/report`, {
      headers: getAuthHeader(),
    }).then(r => handleResponse(r)),
};
```

- [ ] **Step 2: Commit**

```bash
git add web/src/lib/api.ts
git commit -m "feat(frontend): add API client with auth headers
- All requests include Bearer token
- Auto-redirect to login on 401
- Typed API methods for all endpoints
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 12: Login Page

**Files:**
- Create: `web/src/pages/LoginPage.tsx`
- Test: Manual testing

**Interfaces:**
- Consumes: AuthContext.login
- Produces: Login form with username/password

- [ ] **Step 1: Create LoginPage**

```typescript
// web/src/pages/LoginPage.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Essay Integrity Checker</CardTitle>
          <CardDescription>Sign in to access the system</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium">
                Username
              </label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
              />
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-500">
            <p>Demo credentials:</p>
            <p className="font-mono mt-1">admin / admin123</p>
            <p className="font-mono">user / user123</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/LoginPage.tsx
git commit -m "feat(frontend): add LoginPage
- Username/password form
- Error display
- Demo credentials hint
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 13: Protected Route Component

**Files:**
- Create: `web/src/components/ProtectedRoute.tsx`
- Test: Manual testing

**Interfaces:**
- Consumes: AuthContext, children, adminOnly prop
- Produces: Redirect to /login if not authenticated

- [ ] **Step 1: Create ProtectedRoute**

```typescript
// web/src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
  adminOnly?: boolean;
}

export function ProtectedRoute({ children, adminOnly = false }: ProtectedRouteProps) {
  const { user, isLoading, isAdmin } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/ProtectedRoute.tsx
git commit -m "feat(frontend): add ProtectedRoute component
- Redirect to login if not authenticated
- Redirect to dashboard if not admin
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 14: Dashboard Pages

**Files:**
- Modify: `web/src/pages/DashboardPage.tsx`
- Create: `web/src/pages/AdminDashboard.tsx`
- Test: Manual testing

**Interfaces:**
- Consumes: AuthContext, api client
- Produces: Dashboard with essays list, stats

- [ ] **Step 1: Create/update DashboardPage**

```typescript
// web/src/pages/DashboardPage.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Button } from '../components/ui/button';

interface Essay {
  id: number;
  filename: string;
  num_pages: number;
  uploaded_at: string;
  user_id: number;
}

export function DashboardPage() {
  const { user, isAdmin, logout } = useAuth();
  const [essays, setEssays] = useState<Essay[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadEssays();
  }, []);

  const loadEssays = async () => {
    try {
      const data = await api.getEssays();
      setEssays(data);
    } catch (err) {
      console.error('Failed to load essays:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this essay?')) return;
    try {
      await api.deleteEssay(id);
      setEssays(essays.filter(e => e.id !== id));
    } catch (err) {
      console.error('Failed to delete essay:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-sm text-gray-500">Welcome, {user?.username}</p>
          </div>
          <div className="flex gap-4 items-center">
            {isAdmin && (
              <Button variant="outline" onClick={() => navigate('/dashboard/admin')}>
                Admin Dashboard
              </Button>
            )}
            <Button variant="outline" onClick={() => navigate('/upload')}>
              Upload Essay
            </Button>
            <Button variant="ghost" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h2 className="text-lg font-medium text-gray-900">Your Essays</h2>
          <p className="text-sm text-gray-500">{essays.length} essay(s) analyzed</p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
          </div>
        ) : essays.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow">
            <p className="text-gray-500">No essays yet. Upload one to get started!</p>
            <Button className="mt-4" onClick={() => navigate('/upload')}>
              Upload Essay
            </Button>
          </div>
        ) : (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {essays.map((essay) => (
                <li key={essay.id}>
                  <div className="px-4 py-4 sm:px-6 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-indigo-600 truncate">
                        {essay.filename}
                      </p>
                      <p className="mt-1 flex items-center text-sm text-gray-500">
                        {essay.num_pages} pages • {new Date(essay.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-2 ml-4">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/essay/${essay.id}`)}
                      >
                        View
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(essay.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Create AdminDashboard**

```typescript
// web/src/pages/AdminDashboard.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Button } from '../components/ui/button';

interface Report {
  users: { total: number; admins: number; users: number };
  essays: { total: number };
  verdicts: { total: number; by_label: Record<string, number> };
  cache: { total: number; by_source: Record<string, number>; total_hits: number };
}

export function AdminDashboard() {
  const { logout } = useAuth();
  const [report, setReport] = useState<Report | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    try {
      const data = await api.getReport();
      setReport(data);
    } catch (err) {
      console.error('Failed to load report:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!confirm('Clear all cache? This cannot be undone.')) return;
    try {
      const result = await api.clearCache();
      alert(`Cleared ${result.deleted_count} cache entries`);
      loadReport();
    } catch (err) {
      console.error('Failed to clear cache:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-sm text-gray-500">System Overview</p>
          </div>
          <div className="flex gap-4 items-center">
            <Button variant="outline" onClick={() => navigate('/admin/users')}>
              Manage Users
            </Button>
            <Button variant="outline" onClick={() => navigate('/dashboard')}>
              User Dashboard
            </Button>
            <Button variant="ghost" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
          </div>
        ) : report ? (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500">Total Users</p>
                <p className="text-3xl font-bold">{report.users.total}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {report.users.admins} admins, {report.users.users} users
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500">Total Essays</p>
                <p className="text-3xl font-bold">{report.essays.total}</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500">Total Verdicts</p>
                <p className="text-3xl font-bold">{report.verdicts.total}</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <p className="text-sm text-gray-500">Cache Entries</p>
                <p className="text-3xl font-bold">{report.cache.total}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {report.cache.total_hits} hits total
                </p>
              </div>
            </div>

            {/* Cache by Source */}
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-medium">Cache by Source</h2>
                <Button size="sm" variant="destructive" onClick={handleClearCache}>
                  Clear Cache
                </Button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(report.cache.by_source).map(([source, count]) => (
                  <div key={source} className="text-center">
                    <p className="text-2xl font-bold">{count as number}</p>
                    <p className="text-sm text-gray-500 capitalize">{source.replace('_', ' ')}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Verdicts by Label */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-lg font-medium mb-4">Verdicts by Label</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {Object.entries(report.verdicts.by_label).map(([label, count]) => (
                  <div key={label} className="text-center">
                    <p className="text-2xl font-bold">{count as number}</p>
                    <p className="text-sm text-gray-500">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500">Failed to load report</p>
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/DashboardPage.tsx web/src/pages/AdminDashboard.tsx
git commit -m "feat(frontend): add dashboard pages
- DashboardPage: user's essays list
- AdminDashboard: system overview with stats
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 15: User Management Page

**Files:**
- Create: `web/src/pages/UserManagementPage.tsx`
- Test: Manual testing

**Interfaces:**
- Consumes: AuthContext, api client
- Produces: User CRUD table

- [ ] **Step 1: Create UserManagementPage**

```typescript
// web/src/pages/UserManagementPage.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../lib/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';

interface User {
  id: number;
  username: string;
  role: string;
  created_at: string;
}

export function UserManagementPage() {
  const { logout } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '', role: 'user' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await api.createUser(formData);
      setShowForm(false);
      setFormData({ username: '', password: '', role: 'user' });
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this user?')) return;
    try {
      await api.deleteUser(id);
      setUsers(users.filter(u => u.id !== id));
    } catch (err) {
      console.error('Failed to delete user:', err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <div className="flex gap-4 items-center">
            <Button variant="outline" onClick={() => navigate('/dashboard/admin')}>
              Back to Admin
            </Button>
            <Button variant="ghost" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-4 flex justify-between items-center">
          <h2 className="text-lg font-medium">Users ({users.length})</h2>
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : 'Add User'}
          </Button>
        </div>

        {showForm && (
          <div className="bg-white p-6 rounded-lg shadow mb-6">
            <h3 className="text-md font-medium mb-4">Create New User</h3>
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-md text-sm mb-4">
                {error}
              </div>
            )}
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Username</label>
                  <Input
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Password</label>
                  <Input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Role</label>
                  <select
                    className="w-full p-2 border rounded-md"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
              <Button type="submit">Create User</Button>
            </form>
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
          </div>
        ) : (
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Username</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{user.username}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${user.role === 'admin' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <Button size="sm" variant="ghost" onClick={() => handleDelete(user.id)}>
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/pages/UserManagementPage.tsx
git commit -m "feat(frontend): add UserManagementPage
- User list table
- Create user form
- Delete user action
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 16: App Routes

**Files:**
- Modify: `web/src/App.tsx`
- Test: Manual testing

**Interfaces:**
- Consumes: All pages and components created
- Produces: Complete routing with auth protection

- [ ] **Step 1: Update App.tsx**

```typescript
// web/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { UserManagementPage } from './pages/UserManagementPage';
// Import existing pages
import { UploadPage } from './pages/UploadPage';
import { EssayPage } from './pages/EssayPage';
import { HistoryPage } from './pages/HistoryPage';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute adminOnly>
                <UserManagementPage />
              </ProtectedRoute>
            }
          />

          {/* Existing routes - add auth protection */}
          <Route
            path="/upload"
            element={
              <ProtectedRoute>
                <UploadPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/essay/:id"
            element={
              <ProtectedRoute>
                <EssayPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <HistoryPage />
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
```

- [ ] **Step 2: Commit**

```bash
git add web/src/App.tsx
git commit -m "feat(frontend): add routing with auth protection
- ProtectedRoute wrapper for all protected pages
- Admin-only routes for admin pages
- Default redirect to dashboard
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 17: Integration Test

**Files:**
- Update: `tests/integration/test_auth.py`
- Test: Run full integration test suite

**Interfaces:**
- Consumes: All backend routes
- Produces: All tests passing

- [ ] **Step 1: Run all auth tests**

Run: `pytest tests/integration/test_auth.py -v`
Expected: All PASS

- [ ] **Step 2: Run API tests**

Run: `pytest tests/integration/test_api.py -v`
Expected: All PASS (with auth added)

- [ ] **Step 3: Commit final test changes**

```bash
git add tests/integration/test_auth.py
git commit -m "test(auth): add auth integration tests
- Login tests for admin and user
- Protected route tests
- User management tests
- Cache management tests
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Database Models | `db/models.py` |
| 2 | Config Updates | `config.py` |
| 3 | Repository Updates | `db/repository.py` |
| 4 | Auth Dependencies | `api/deps.py` |
| 5 | Auth Routes | `api/routes/auth.py` |
| 6 | User Routes | `api/routes/users.py` |
| 7 | Essay Routes Update | `api/routes/essays.py` |
| 8 | Cache Routes | `api/routes/cache.py` |
| 9 | Export Routes | `api/routes/export.py` |
| 10 | AuthContext | `contexts/AuthContext.tsx` |
| 11 | API Client | `lib/api.ts` |
| 12 | Login Page | `pages/LoginPage.tsx` |
| 13 | ProtectedRoute | `components/ProtectedRoute.tsx` |
| 14 | Dashboard Pages | `pages/DashboardPage.tsx`, `AdminDashboard.tsx` |
| 15 | User Management Page | `pages/UserManagementPage.tsx` |
| 16 | App Routes | `App.tsx` |
| 17 | Integration Tests | `tests/integration/test_auth.py` |

---

## Self-Review Checklist

- [ ] All hardcoded credentials (admin/admin123, user/user123) documented
- [ ] JWT secret and expiry documented
- [ ] All new API endpoints tested
- [ ] All frontend pages implemented with auth
- [ ] Protected routes properly redirect
- [ ] Error handling for auth failures
- [ ] Admin-only routes protected
- [ ] Ownership checks on essay operations
