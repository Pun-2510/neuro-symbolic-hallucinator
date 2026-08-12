# Authentication & Citation Cache Design

**Ngày:** 2026-08-12
**Mục tiêu:** Thêm login system và citation cache vào Essay Integrity Checker
**Status:** Approved

---

## 1. Mục tiêu

1. **Authentication**: User login bằng username/password (hardcoded credentials)
2. **Authorization**: Phân quyền Admin vs User
3. **User History**: Mỗi essay được gắn với user upload
4. **Citation Cache**: Cache kết quả từ Crossref/OpenAlex/Semantic Scholar/arXiv để tránh gọi lại API

---

## 2. Hardcoded Credentials

### Users

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| user | user123 | user |

### Authorization Matrix

| Action | User | Admin |
|--------|------|-------|
| Login/Logout | ✓ | ✓ |
| Upload essay | ✓ | ✓ |
| View own essays | ✓ | ✓ |
| View all essays | ✗ | ✓ |
| Delete own essay | ✓ | ✓ |
| Delete any essay | ✗ | ✓ |
| Override verdict | ✓ | ✓ |
| Manage users (CRUD) | ✗ | ✓ |
| View cache stats | ✗ | ✓ |
| Clear cache | ✗ | ✓ |
| Export system report | ✗ | ✓ |

---

## 3. Database Schema

### 3.1 Thêm bảng `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',  -- 'admin' or 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Sửa bảng `essays` (thêm user_id)

```sql
ALTER TABLE essays ADD COLUMN user_id INTEGER REFERENCES users(id);
```

### 3.3 Thêm bảng `citation_cache`

```sql
CREATE TABLE citation_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key VARCHAR(64) UNIQUE NOT NULL,  -- SHA256 hash
    source VARCHAR(20) NOT NULL,              -- 'crossref', 'openalex', 'semantic_scholar', 'arxiv'
    raw_response TEXT NOT NULL,              -- Full JSON response
    matched_fields TEXT,                      -- JSON: which fields matched
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_hit_at TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_cache_key ON citation_cache(cache_key);
CREATE INDEX idx_source ON citation_cache(source);
```

### 3.4 Thêm bảng `sessions`

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token ON sessions(token);
CREATE INDEX idx_user_id ON sessions(user_id);
```

---

## 4. Cache Strategy

### 4.1 Cache Key Generation

```python
def generate_cache_key(citation: CitationInfo) -> str:
    """
    Generate unique cache key from citation metadata.
    Uses normalized values for consistency.
    """
    parts = [
        (citation.title or "").lower().strip(),
        "|".join(sorted([a.lower().strip() for a in (citation.authors or [])])),
        (citation.year or "").strip(),
        (citation.doi or "").lower().strip(),
    ]
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()
```

### 4.2 Cache Flow

```
Upload Essay
    │
    ▼
For each citation in essay:
    │
    ▼
Generate cache_key from (title, authors, year, doi)
    │
    ├─── HIT ────→ Return cached raw_response
    │                 Update last_hit_at, hit_count
    │
    └─── MISS ──→ Call Crossref API
                      │
                      ├─── Found ──→ Save to cache, return response
                      │
                      └─── Not Found → Call OpenAlex
                                         │
                                         ├─── Found ──→ Save to cache, return response
                                         │
                                         └─── Not Found → Call Semantic Scholar
                                                            │
                                                            ├─── Found ──→ Save to cache, return response
                                                            │
                                                            └─── Not Found → Call arXiv
                                                                              │
                                                                              ├─── Found ──→ Save to cache, return response
                                                                              │
                                                                              └─── Not Found → Return empty, no cache
```

### 4.3 Cache Storage

Lưu **full raw response** từ mỗi source dưới dạng JSON text trong `raw_response` column.

---

## 5. Authentication Flow

### 5.1 JWT Token Structure

```python
{
    "sub": user_id,           # int
    "username": "admin",      # str
    "role": "admin",          # str
    "exp": timestamp + 24h,   # int
    "iat": timestamp          # int
}
```

### 5.2 Login Flow

```
POST /api/auth/login
Body: { "username": "admin", "password": "admin123" }
    │
    ▼
Validate credentials (hardcoded)
    │
    ▼
Generate JWT token (expires 24h)
    │
    ▼
Store session in DB
    │
    ▼
Return: { "token": "eyJ...", "user": { "id": 1, "username": "admin", "role": "admin" } }
```

### 5.3 Protected Routes

Mọi route trừ `/api/auth/login` và `/api/health` cần Bearer token.

```python
# Backend dependency
def get_current_user(authorization: str = Header(...)) -> User:
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user = db.query(User).get(payload["sub"])
    if not user or user.session.token != token:
        raise HTTPException(401, "Invalid token")
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return user
```

---

## 6. API Endpoints

### 6.1 Auth Routes

| Method | Endpoint | Body | Response | Auth |
|--------|----------|------|----------|------|
| POST | `/api/auth/login` | `{username, password}` | `{token, user}` | None |
| POST | `/api/auth/logout` | - | `{message}` | User |
| GET | `/api/auth/me` | - | `{id, username, role}` | User |

### 6.2 Essay Routes

| Method | Endpoint | Response | Auth |
|--------|----------|----------|------|
| POST | `/api/essays` | Upload & analyze essay | User |
| GET | `/api/essays` | List own essays | User |
| GET | `/api/essays/all` | List all essays | Admin |
| GET | `/api/essays/{id}` | Get essay details | Owner/Admin |
| DELETE | `/api/essays/{id}` | Delete essay | Owner/Admin |

### 6.3 User Management (Admin only)

| Method | Endpoint | Body | Response | Auth |
|--------|----------|------|----------|------|
| GET | `/api/users` | - | `[{id, username, role, created_at}]` | Admin |
| POST | `/api/users` | `{username, password, role}` | `{id, username, role}` | Admin |
| PUT | `/api/users/{id}` | `{username?, password?, role?}` | `{id, username, role}` | Admin |
| DELETE | `/api/users/{id}` | - | `{message}` | Admin |

### 6.4 Cache Management (Admin only)

| Method | Endpoint | Response | Auth |
|--------|----------|----------|------|
| GET | `/api/cache/stats` | `{total, by_source, avg_hit_rate}` | Admin |
| DELETE | `/api/cache` | - | `{deleted_count}` | Admin |
| DELETE | `/api/cache/{cache_key}` | - | `{message}` | Admin |

### 6.5 Export (Admin only)

| Method | Endpoint | Response | Auth |
|--------|----------|----------|------|
| GET | `/api/export/report` | `{users, essays, cache_stats, verdicts_summary}` | Admin |

---

## 7. Frontend Structure

### 7.1 Routes

```
/login                    → LoginPage (public)
/dashboard                → DashboardPage (user: my essays)
/dashboard/admin          → AdminDashboard (admin: overview)
/history                  → HistoryPage (user: my essays filtered)
/admin/users              → UserManagementPage (admin: CRUD)
/admin/cache              → CacheManagementPage (admin: stats, clear)
```

### 7.2 Auth Context

```typescript
interface AuthContext {
  user: { id: number; username: string; role: 'admin' | 'user' } | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
}
```

### 7.3 Protected Routes

```typescript
// Route guards
<ProtectedRoute>
  <Dashboard />           // User or Admin
</ProtectedRoute>

<AdminRoute>
  <AdminDashboard />      // Admin only
</AdminRoute>
```

### 7.4 API Client Update

```typescript
// Add auth header to all requests
const apiClient = {
  async request(endpoint: string, options?: RequestInit) {
    const token = getAuthToken();
    return fetch(`/api${endpoint}`, {
      ...options,
      headers: {
        ...options?.headers,
        ...(token && { Authorization: `Bearer ${token}` }),
      },
    });
  },
};
```

---

## 8. File Changes

### 8.1 Backend

| File | Changes |
|------|---------|
| `src/integrity_checker/db/models.py` | Add User, Session, CitationCache models |
| `src/integrity_checker/db/session.py` | Add get_db dependency |
| `src/integrity_checker/db/repository.py` | Add user, cache, session methods |
| `src/integrity_checker/api/routes/auth.py` | New: login, logout, me |
| `src/integrity_checker/api/routes/users.py` | New: CRUD users |
| `src/integrity_checker/api/routes/cache.py` | New: cache stats, clear |
| `src/integrity_checker/api/routes/essays.py` | Add user_id, ownership check |
| `src/integrity_checker/api/routes/export.py` | New: system report |
| `src/integrity_checker/api/deps.py` | Add get_current_user, require_admin |
| `src/integrity_checker/api/main.py` | Register new routers |
| `src/integrity_checker/config.py` | Add JWT_SECRET, TOKEN_EXPIRE_HOURS |

### 8.2 Frontend

| File | Changes |
|------|---------|
| `web/src/contexts/AuthContext.tsx` | New: auth state management |
| `web/src/lib/api.ts` | Update: add auth header |
| `web/src/pages/LoginPage.tsx` | New: login form |
| `web/src/pages/DashboardPage.tsx` | Update: show user essays |
| `web/src/pages/AdminDashboard.tsx` | New: admin overview |
| `web/src/pages/UserManagementPage.tsx` | New: CRUD users |
| `web/src/pages/CacheManagementPage.tsx` | New: cache stats |
| `web/src/components/ProtectedRoute.tsx` | New: route guard |
| `web/src/App.tsx` | Update: add routes |

---

## 9. Implementation Order

1. **Database**: Add models, run migrations
2. **Auth Backend**: Login, JWT, deps
3. **User Management**: CRUD endpoints
4. **Frontend Auth**: Login page, AuthContext, protected routes
5. **Essay Updates**: Add user_id, ownership checks
6. **Cache Backend**: CitationCache model, integration in retrieval
7. **Cache Frontend**: Stats page, clear button
8. **Admin Dashboard**: Overview, reports
9. **Export**: System report endpoint

---

## 10. Security Considerations

- Passwords hashed with bcrypt (even for hardcoded)
- JWT tokens expire after 24 hours
- Sessions stored in DB for invalidation capability
- Soft delete for essays (keep data for audit)
- Admin actions logged in AuditLog

---

## 11. Cache Key Normalization

```python
def normalize_for_cache(value: str | None) -> str:
    """Normalize citation field for consistent cache keys."""
    if not value:
        return ""
    # Remove extra whitespace, lowercase
    return " ".join(value.lower().split())
```

Fields normalized:
- Title: lowercase, strip whitespace
- Authors: lowercase each, sort alphabetically, join with |
- Year: strip whitespace
- DOI: lowercase, strip

---

## 12. Error Handling

| Scenario | Response |
|----------|----------|
| Invalid credentials | 401: `{detail: "Invalid username or password"}` |
| Token expired | 401: `{detail: "Token expired"}` |
| Token invalid | 401: `{detail: "Invalid token"}` |
| Admin-only endpoint by user | 403: `{detail: "Admin access required"}` |
| User accesses other's essay | 403: `{detail: "Access denied"}` |
| Essay not found | 404: `{detail: "Essay not found"}` |
