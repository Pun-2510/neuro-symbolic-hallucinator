# Plan: Full Account Management (CRUD + Profile + Avatar)

## Context

Hệ thống hiện tại có `User` model **rất tối giản** (`id`, `username`, `password_hash`, `role`, `created_at`, `updated_at`) — không có email, full_name, hay avatar. Backend đã có `GET/POST/PUT/DELETE /api/users` cho admin nhưng chỉ thao tác trên username/role/password, và chưa có endpoint `/api/users/me` để user tự cập nhật profile. Frontend có Dashboard nhưng chưa có trang quản lý account.

**Mục tiêu:** Bổ sung đầy đủ chức năng account management:
- Extend `User` model: thêm `email`, `full_name`, `avatar_path`, `is_active`, `last_login_at`
- Trang admin `/admin/users`: CRUD users (search, filter, pagination, edit modal, delete confirm)
- Trang self `/profile`: user tự sửa email, full_name, avatar; đổi password
- Avatar upload (local FS, 2MB, JPG/PNG/WEBP)
- Auto-migration (SQLite `ALTER TABLE` pattern đã có ở `db/session.py`)
- Tests backend (pytest) + Playwright UI tests
- Cập nhật `AuthContext` để sync `full_name`, `avatar_url` trong local state
- Cập nhật Sidebar (AppLayout) để hiển thị avatar + link đến /profile

**Decision (APPROVED by user):**
- ✅ Full Account Management (admin + self-profile)
- ✅ Local filesystem cho avatar (`data/avatars/`)
- ✅ 2MB, JPG/PNG/WEBP

---

## Architecture

### Backend (FastAPI + SQLAlchemy)

```
src/integrity_checker/
├── db/
│   ├── models.py          [MODIFY] Thêm email, full_name, avatar_path, is_active, last_login_at
│   ├── repository.py      [MODIFY] Update User CRUD: create_user accept email/full_name, get_user_by_email
│   └── session.py         [MODIFY] Thêm ALTER TABLE migration cho users
├── api/
│   ├── routes/
│   │   ├── users.py       [MODIFY] Extend UserCreate/Update/Response + thêm GET/PATCH /me, POST /me/avatar
│   │   └── auth.py        [MODIFY] Thêm /me trả về full profile, update last_login_at
│   ├── deps.py            [NO CHANGE] get_current_user đã đủ
│   └── main.py            [NO CHANGE] route registration đã có
└── api/services/
    └── avatar_service.py  [NEW] Handle avatar upload, save to data/avatars/, validate MIME/size
```

### Frontend (React + Vite + Tailwind)

```
web/src/
├── pages/
│   ├── AccountManagementPage.tsx  [NEW] Admin CRUD all users
│   ├── ProfilePage.tsx            [NEW] Self-profile edit + avatar upload + change password
│   └── ...                        [NO CHANGE]
├── components/
│   ├── AppLayout.tsx              [MODIFY] Sidebar user info dùng avatar, link /profile
│   ├── UserFormDialog.tsx         [NEW] Create/Edit user modal
│   ├── DeleteUserDialog.tsx       [NEW] Confirm delete
│   └── AvatarUpload.tsx           [NEW] Drag-drop avatar upload
├── api/
│   └── client.ts                  [MODIFY] Thêm user CRUD methods + avatar upload
├── contexts/
│   └── AuthContext.tsx            [MODIFY] Extend User type với email/full_name/avatar_url
├── lib/
│   └── api.ts                     [MODIFY] Mirror API methods
└── router.tsx                     [MODIFY] Thêm /admin/users, /profile routes
```

---

## Implementation Plan

### Phase 1: Backend — DB Schema + Migration

**File:** `src/integrity_checker/db/models.py`

Thêm fields vào `User`:
```python
email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
avatar_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
is_active: Mapped[bool] = mapped_column(Integer, default=1)  # SQLite bool
last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**File:** `src/integrity_checker/db/session.py`

Mở rộng `_run_inline_migrations`:
```python
# Thêm ALTER TABLE cho users: email, full_name, avatar_path, is_active, last_login_at
```

**File:** `src/integrity_checker/db/repository.py`

Extend methods:
- `create_user(username, password_hash, role, email=None, full_name=None) -> User`
- `update_user(user_id, **kwargs) -> User | None` (đã generic, không cần đổi)
- `get_user_by_email(email) -> User | None` (NEW)
- `update_last_login(user_id) -> None` (NEW)

### Phase 2: Backend — Avatar Service

**File:** `src/integrity_checker/api/services/avatar_service.py` (NEW)

```python
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 2 * 1024 * 1024  # 2MB

class AvatarService:
    def __init__(self, data_dir: Path = Path("data/avatars")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, user_id: int, content: bytes, mime: str) -> str:
        # Validate MIME, size
        # Map mime → extension: image/jpeg → .jpg, image/png → .png, image/webp → .webp
        # Save to data/avatars/{user_id}.{ext}
        # Return relative path: /data/avatars/123.jpg

    def get_path(self, user_id: int, ext: str) -> Path: ...
    def delete(self, avatar_path: str) -> None: ...
```

**File:** `src/integrity_checker/api/main.py`

Mount static file serving cho `data/avatars/`:
```python
app.mount("/api/avatars", StaticFiles(directory="data/avatars"), name="avatars")
```

### Phase 3: Backend — Routes

**File:** `src/integrity_checker/api/routes/users.py`

```python
# Extend existing schemas
class UserCreate(BaseModel):
    username: str
    password: str
    email: EmailStr | None = None
    full_name: str | None = None
    role: str = "user"
    is_active: bool = True

class UserUpdate(BaseModel):  # partial update via PUT/PATCH
    username: str | None = None
    password: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    role: str
    is_active: bool
    avatar_url: str | None  # computed from avatar_path
    last_login_at: str | None
    created_at: str | None

# Existing endpoints: list, create, update, delete (extend schemas)

# NEW endpoints (self-service)
@router.get("/me", response_model=UserResponse)  # /api/users/me
def get_me(current_user: User = Depends(get_current_user)): ...

@router.patch("/me", response_model=UserResponse)  # self-profile update
def update_me(request: UserSelfUpdate, current_user=...): ...

@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(file: UploadFile = File(...), current_user=...): ...

@router.post("/me/password", response_model=MessageResponse)
def change_my_password(request: PasswordChange, current_user=...): ...
```

Add endpoint: `GET /api/users/{id}/avatar` (serve file) — or just use StaticFiles mount.

**File:** `src/integrity_checker/api/routes/auth.py`

- Update `/auth/me` để trả về full profile (email, full_name, avatar_url)
- Update login: set `last_login_at`

### Phase 4: Frontend — API Client + Types

**File:** `web/src/api/client.ts`

```typescript
export interface User {
  id: number;
  username: string;
  email: string | null;
  full_name: string | null;
  role: 'admin' | 'user';
  is_active: boolean;
  avatar_url: string | null;
  last_login_at: string | null;
  created_at: string | null;
}

export const api = {
  // User CRUD (admin)
  listUsers: () => request<User[]>('/users'),
  createUser: (data: UserCreate) => request<User>('/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id: number, data: UserUpdate) => request<User>(`/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteUser: (id: number) => request<MessageResponse>(`/users/${id}`, { method: 'DELETE' }),

  // Self-service
  getMe: () => request<User>('/users/me'),
  updateMe: (data: Partial<UserUpdate>) => request<User>('/users/me', { method: 'PATCH', body: JSON.stringify(data) }),
  uploadMyAvatar: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<User>('/users/me/avatar', { method: 'POST', body: fd });
  },
  changeMyPassword: (current: string, new_: string) =>
    request<MessageResponse>('/users/me/password', { method: 'POST', body: JSON.stringify({ current_password: current, new_password: new_ }) }),
};
```

**File:** `web/src/contexts/AuthContext.tsx`

Extend `User` interface, expose `refreshUser()`, sync after avatar upload.

### Phase 5: Frontend — Account Management Page (Admin)

**File:** `web/src/pages/AccountManagementPage.tsx` (NEW)

- Admin-only check (redirect to /dashboard if not admin)
- Table: ID, Avatar, Username, Full Name, Email, Role, Active, Last Login, Created, Actions
- Search bar (filter by username, email, full_name)
- Role filter (All, Admin, User)
- Status filter (All, Active, Inactive)
- "Create User" button → mở UserFormDialog
- Per-row: Edit (open UserFormDialog with data), Delete (open DeleteUserDialog)
- Loading + error states
- Pagination (nếu >20 users)

**File:** `web/src/components/UserFormDialog.tsx` (NEW)

Modal dùng Radix Dialog (đã install):
- Form: username, full_name, email, password (only for create), role (select), is_active (checkbox)
- Validation: required fields, email format, password min length
- Submit → gọi api.createUser hoặc api.updateUser
- Loading state + error display

**File:** `web/src/components/DeleteUserDialog.tsx` (NEW)

Modal confirm: "Bạn có chắc muốn xóa user X? Hành động này không thể hoàn tác."
- Disable nếu currentUser.id === user.id
- Show count of essays owned (warning)

### Phase 6: Frontend — Profile Page (Self)

**File:** `web/src/pages/ProfilePage.tsx` (NEW)

Layout:
- Left: Avatar upload section (AvatarUpload component, drag-drop or click)
- Right: Form (username readonly, full_name, email), Save button
- Below: Change password section (current + new + confirm)
- Display role, member since, last login

**File:** `web/src/components/AvatarUpload.tsx` (NEW)

- Drag-drop or click-to-browse
- Accept: .jpg, .png, .webp
- Max 2MB (validate client-side)
- Preview sau khi chọn
- Upload button → calls api.uploadMyAvatar
- Show current avatar nếu có

### Phase 7: Frontend — Sidebar + Routing

**File:** `web/src/components/AppLayout.tsx`

- Hiển thị avatar (img nếu có, fallback User icon)
- Link "/profile" trên user info area
- Add "Account Management" nav item (admin only) → /admin/users

**File:** `web/src/router.tsx`

```typescript
{ path: '/profile', element: <ProfilePage /> },
{ path: '/admin/users', element: <AccountManagementPage /> },
```

### Phase 8: Backend — Tests

**File:** `tests/unit/test_user_management.py` (NEW)

Coverage:
- `create_user` success (admin) + validation (duplicate username, invalid role, invalid email)
- `create_user` requires admin (regular user → 403)
- `list_users` returns all (admin), 403 (regular)
- `update_user` partial update (admin)
- `update_user` cannot delete self
- `delete_user` admin only, cannot delete self
- `get_me` returns full profile
- `update_me` allows user to change email/full_name
- `change_my_password` validates current password
- `upload_avatar` valid JPG/PNG/WEBP
- `upload_avatar` rejects >2MB
- `upload_avatar` rejects non-image MIME
- Migration: new columns exist after running

**File:** `tests/integration/test_user_api.py` (NEW)

End-to-end với FastAPI TestClient (existing pattern from `tests/integration/test_auth.py`).

### Phase 9: Playwright UI Tests

**File:** `web/tests/e2e/account-management.spec.ts` (NEW)

Coverage:
- Admin sees /admin/users link in sidebar
- Admin can create user (fill form, submit, see in table)
- Admin can edit user (change role, full_name)
- Admin can search/filter users
- Admin cannot delete self (button disabled or error)
- Admin can deactivate user
- Regular user cannot see /admin/users (redirected or 403)
- Regular user can access /profile
- User can update profile (email, full_name)
- User can change password (with current password)
- User can upload avatar (valid file → success, oversized → error)
- Avatar displays in sidebar after upload
- AuthContext syncs new user info after profile update

---

## Key Files (Critical)

| File | Action | Notes |
|------|--------|-------|
| `src/integrity_checker/db/models.py` | Modify | Add 5 fields to User |
| `src/integrity_checker/db/session.py` | Modify | Add 5 ALTER TABLE migrations |
| `src/integrity_checker/db/repository.py` | Modify | Add get_user_by_email, update_last_login, extend create_user |
| `src/integrity_checker/api/services/avatar_service.py` | Create | NEW — save/validate/delete avatar |
| `src/integrity_checker/api/main.py` | Modify | Mount /api/avatars static |
| `src/integrity_checker/api/routes/users.py` | Modify | Add /me, /me/avatar, /me/password endpoints; extend schemas |
| `src/integrity_checker/api/routes/auth.py` | Modify | Update /me response + last_login_at |
| `web/src/api/client.ts` | Modify | Add User type, user CRUD + avatar methods |
| `web/src/contexts/AuthContext.tsx` | Modify | Extend User type, add refreshUser() |
| `web/src/components/AppLayout.tsx` | Modify | Avatar display + nav links |
| `web/src/router.tsx` | Modify | Add /profile, /admin/users routes |
| `web/src/components/UserFormDialog.tsx` | Create | NEW — modal form |
| `web/src/components/DeleteUserDialog.tsx` | Create | NEW — confirm dialog |
| `web/src/components/AvatarUpload.tsx` | Create | NEW — dropzone + preview |
| `web/src/pages/AccountManagementPage.tsx` | Create | NEW — admin CRUD |
| `web/src/pages/ProfilePage.tsx` | Create | NEW — self-profile |
| `tests/unit/test_user_management.py` | Create | NEW — backend unit tests |
| `tests/integration/test_user_api.py` | Create | NEW — API integration tests |
| `web/tests/e2e/account-management.spec.ts` | Create | NEW — Playwright UI tests |

---

## Reused Patterns

- **Repository pattern** — `Repository` class in `db/repository.py` already provides `create_user`, `update_user`, `delete_user`, `get_user_by_username` — extend them rather than rewriting
- **Inline migration** — follow pattern from `db/session.py:_run_inline_migrations` (PRAGMA table_info → ALTER TABLE)
- **Pydantic schemas** — mirror existing `UserCreate/UserUpdate/UserResponse` pattern in `api/routes/users.py`
- **Auth dep** — reuse `get_current_user` and `require_admin` from `api/deps.py`
- **Tailwind classes** — `.btn-primary`, `.btn-secondary`, `.input`, `.card`, `.card-elevated` from `web/src/index.css` (no need to invent new styles)
- **Radix Dialog** — `@radix-ui/react-dialog` already in `package.json`, wrap in our dialog components
- **lucide-react** — `User`, `Camera`, `Trash2`, `Search`, `Upload`, `Eye`, `X` icons all available
- **API client pattern** — `request<T>(path, init)` wrapper in `web/src/api/client.ts`; FormData for uploads
- **Mock auth helper** — `setupAuthenticatedPage()` in `web/tests/e2e/helpers.ts` — extend with admin/user roles
- **TestClient pattern** — `from fastapi.testclient import TestClient; client = TestClient(app)` in existing integration tests

---

## UI/UX Design

### Account Management Page (Admin)

```
┌──────────────────────────────────────────────────────────────┐
│ Account Management                          [Create User]    │
│ Manage user accounts and permissions                        │
├──────────────────────────────────────────────────────────────┤
│ [Search...] [Role: All ▼] [Status: All ▼]                   │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ AVATAR │ USERNAME │ FULL NAME │ EMAIL │ ROLE │ ACTIONS  │ │
│ │  [img] │ admin    │ Adm User  │ a@..  │ admin│ ✏️ 🗑️   │ │
│ │  [img] │ user1    │ User One  │ u@..  │ user │ ✏️ 🗑️   │ │
│ └──────────────────────────────────────────────────────────┘ │
│ Showing 2 of 2 users                                          │
└──────────────────────────────────────────────────────────────┘
```

### Profile Page (Self)

```
┌──────────────────────────────────────────────────────────────┐
│ My Profile                                                    │
│ Manage your personal information                              │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────┐    ┌─────────────────────────────────────┐  │
│  │            │    │ Username  [admin           ] (read) │  │
│  │  [Avatar]  │    │ Full Name [Administrator  ]         │  │
│  │            │    │ Email     [admin@example.com]      │  │
│  │  [Upload]  │    │ Role      admin                     │  │
│  │            │    │                                      │  │
│  └────────────┘    │              [Save Changes]         │  │
│                    └─────────────────────────────────────┘  │
│                                                              │
│  ┌─ Change Password ─────────────────────────────────────┐  │
│  │ Current Password [_____________]                       │  │
│  │ New Password     [_____________]                       │  │
│  │ Confirm Password [_____________]                       │  │
│  │                            [Update Password]          │  │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Sidebar User Info (after avatar)

```
┌──────────────────────────┐
│ [Avatar]  admin          │
│           Administrator  │
│           → View profile │
└──────────────────────────┘
```

---

## Verification

### Backend

```bash
# Run all tests
source .venv/bin/activate && python -m pytest tests/ -v

# Run new tests specifically
python -m pytest tests/unit/test_user_management.py tests/integration/test_user_api.py -v
```

### Frontend

```bash
# Type check + build
cd web && npm run build

# Lint
cd web && npm run lint

# Start services
source .venv/bin/activate && uvicorn src.integrity_checker.api.main:app --port 8000 &
cd web && npm run dev
```

### Playwright

```bash
# Start backend + frontend first (see above)

# Run E2E tests
cd web && npm run test:e2e -- account-management.spec.ts

# Or run all E2E
cd web && npm run test:e2e

# Headed mode for visual debugging
cd web && npm run test:e2e:headed
```

### Manual Smoke Test

1. Login as admin
2. Navigate to /admin/users
3. Create user: username="testuser", full_name="Test User", email="test@example.com", role="user"
4. Edit user: change full_name
5. Upload avatar for the user
6. Deactivate user
7. Try to delete self → error
8. Logout, login as testuser
9. Navigate to /profile
10. Update full_name, upload own avatar
11. Change password
12. Verify avatar shows in sidebar

---

## Migration Safety

The `ALTER TABLE` pattern in `db/session.py:_run_inline_migrations` is the project's existing approach for schema evolution. New fields are all nullable except `is_active` (default 1), so no NOT NULL constraint issues on existing rows. Tests verify the migration is idempotent (running twice doesn't fail).

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing hardcoded admin/user auto-created via `HARDCODED_USERS` may not have email | Set email="admin@example.com" / "user@example.com" defaults in `auth.py:login()` on first login if email is null |
| Avatar path collisions if user re-uploads | Overwrite `data/avatars/{user_id}.{ext}` — same user always overwrites |
| Avatar file lingering after user delete | `avatar_service.delete()` called from `users.py:delete_user` endpoint |
| Email uniqueness if `unique=True` on column but existing nulls | SQLite allows multiple NULLs in unique columns — safe |
| PATCH semantics: project uses PUT for full update | Add PATCH `/users/me` (new), keep PUT `/users/{id}` for admin full update (existing) |
| Frontend tests may need new mock data | Extend `helpers.ts` with `MOCK_USERS` array |
| Test DB doesn't run migrations automatically | Existing `conftest.py` uses in-memory SQLite + `Base.metadata.create_all()` — new fields will be created via SQLAlchemy DDL directly; run tests against same DB |

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: DB + migration | 1h |
| Phase 2: Avatar service | 1h |
| Phase 3: Routes | 2h |
| Phase 4: API client + Auth context | 1h |
| Phase 5: Admin page + dialogs | 3h |
| Phase 6: Profile page + avatar upload | 2h |
| Phase 7: Sidebar + routing | 0.5h |
| Phase 8: Backend tests | 2h |
| Phase 9: Playwright tests | 2h |
| **Total** | ~14.5h |
