# 📊 Phân Tích UX/UI Phân Cấp Theo Role — Essay Integrity Checker

> Tài liệu đề xuất cải thiện UX/UI theo 3 cấp người dùng: **User (Student)** / **Teacher** / **Admin**
> Ngày tạo: 2026-10-08
> Phiên bản: v1.0 (đề xuất)

---

## 🔍 I. Hiện Trạng Dự Án

### 1. Cấu trúc Role hiện tại

| Thành phần | Trạng thái | Ghi chú |
|------------|------------|---------|
| **Backend roles** | `admin` / `user` | Hard-coded trong `auth.py:130`, `users.py:30` |
| **Frontend role check** | `user?.role === 'admin'` | Chỉ dùng ở 4 file: `AppLayout.tsx`, `ProtectedRoute.tsx`, `AuthContext.tsx`, `AccountManagementPage.tsx` |
| **Teacher role** | ❌ **CHƯA TỒN TẠI** | Không có trong DB, API, hay UI |
| **User/Student role** | ⚠️ Trùng với `user` | Hiện tại `user` đang được dùng như "sinh viên" |

### 2. Phân cấp UI hiện tại — chỉ 2 cấp

```
┌─────────────────────────────────────────────────┐
│  ADMIN (full features)                          │
│  • Account Management                           │
│  • Toàn bộ nav: Dashboard/Upload/Batch/History  │
└─────────────────────────────────────────────────┘
                      vs
┌─────────────────────────────────────────────────┐
│  USER (hiện tại = mọi user thường)              │
│  • Dashboard / Upload / Batch / History         │
│  • KHÔNG có Account Management                  │
└─────────────────────────────────────────────────┘
```

### 3. Những vấn đề UX/UI tôi phát hiện được

| # | Vấn đề | Vị trí | Mức độ |
|---|--------|--------|--------|
| 1 | **Sidebar 17 mục trộn lẫn** — không có nhóm rõ ràng theo role | `AppLayout.tsx:175-253` | 🔴 Cao |
| 2 | **Hard-coded role check** `user?.role === 'admin'` rải rác 4 nơi | Nhiều file | 🔴 Cao |
| 3 | **Teacher role chưa có** trong schema, dù giảng viên yêu cầu cần có | DB + API + UI | 🔴 Cao |
| 4 | **Dashboard hiển thị giống nhau** cho mọi role | `DashboardPage.tsx` | 🟡 Trung bình |
| 5 | **Không có "Class/Cohort"** — teacher không theo dõi được nhóm SV | Thiếu trong DB | 🔴 Cao |
| 6 | **"Batch Upload"** hiện tại không phù hợp context teacher (cần "Submit Class") | `BatchUploadPage.tsx` | 🟡 Trung bình |
| 7 | **OverrideControls** (đổi verdict) lộ cho cả user — đáng lẽ chỉ teacher/admin | `EssayPage.tsx:94` | 🔴 Cao |
| 8 | **Avatar/Profile** làm phức tạp cho user thường | `ProfilePage.tsx`, `AvatarUpload.tsx` | 🟢 Thấp |
| 9 | **LogicTracePage, DocumentInspectorPage, OrphanDetectionPage** — user thường có cần truy cập? | 3 trang nâng cao | 🟡 Trung bình |
| 10 | **Settings Page** — Settings quá chung chung, không rõ cho role nào | `SettingsPage.tsx` | 🟡 Trung bình |
| 11 | **Landing page** dùng `Anthropic cream + indigo` — generic | `LandingPage.tsx` | 🟢 Thấp (thẩm mỹ) |
| 12 | **Help Modal** giống nhau cho mọi role | `HelpModal.tsx` | 🟢 Thấp |
| 13 | **Demo credentials hiển thị trên UI** — security risk khi production | `LoginPage.tsx:261-271` | 🔴 Nghiêm trọng |

---

## 🎯 II. Đề Xuất Kiến Trúc UX/UI Phân Cấp Theo Role

### A. Mô hình 3 cấp độ — đề xuất

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  🟢 USER / STUDENT   ──── Đơn giản, tập trung vào "nộp bài"      │
│  "Tôi cần kiểm tra bài viết của tôi có lỗi trích dẫn không"      │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🟡 TEACHER          ──── Dashboard lớp học, theo dõi SV        │
│  "Tôi muốn xem tiến độ lớp + override verdict khi cần"           │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🔴 ADMIN            ──── Full power + quản lý hệ thống         │
│  "Tôi quản lý user, role, retention API, system health"         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### B. Backend Changes (cần thực hiện)

#### 1. Mở rộng Role enum
```python
# src/integrity_checker/db/models.py
class UserRole(str, Enum):
    USER = "user"          # Sinh viên / User thường
    TEACHER = "teacher"    # Giảng viên (mới)
    ADMIN = "admin"        # Quản trị viên

# Thêm field:
class User(Base):
    # ... existing fields
    institution: Mapped[str | None]     # Trường/khoa
    class_id: Mapped[int | None]        # Lớp (FK → Class)
    can_override_verdicts: Mapped[bool] = False  # Teacher-specific
```

#### 2. Class/Cohort model mới
```python
class Class(Base):
    id: int
    name: str                       # "KHDL2023-A"
    teacher_id: int (FK → User)     # Giảng viên phụ trách
    student_ids: list[int]          # Danh sách SV
    created_at: datetime
```

#### 3. API endpoints mới cho Teacher
```
GET    /api/teacher/classes              # Danh sách lớp của teacher
POST   /api/teacher/classes              # Tạo lớp
GET    /api/teacher/classes/{id}/students
GET    /api/teacher/classes/{id}/essays   # Bài nộp của lớp
GET    /api/teacher/dashboard            # Stats cho teacher
POST   /api/verdicts/{id}/override       # Teacher được phép override
```

---

### C. Frontend Architecture — Role-Based UI System

#### 1. Tạo abstraction layer `useRole()` hook

```tsx
// web/src/hooks/useRole.ts
import { useAuth } from '@/contexts/AuthContext';

export type UserCapability =
  | 'upload_essay'
  | 'batch_upload'
  | 'view_own_history'
  | 'view_class_history'      // Teacher
  | 'override_verdict'         // Teacher + Admin
  | 'manage_users'             // Admin only
  | 'view_logic_trace'         // Teacher + Admin
  | 'view_document_inspector'  // Teacher + Admin
  | 'export_class_report'      // Teacher
  | 'system_settings';         // Admin

const ROLE_CAPABILITIES: Record<string, UserCapability[]> = {
  user: [
    'upload_essay',
    'view_own_history',
  ],
  teacher: [
    'upload_essay',
    'view_own_history',
    'view_class_history',
    'override_verdict',
    'view_logic_trace',
    'view_document_inspector',
    'export_class_report',
  ],
  admin: [
    'upload_essay',
    'view_own_history',
    'view_class_history',
    'override_verdict',
    'view_logic_trace',
    'view_document_inspector',
    'export_class_report',
    'manage_users',
    'system_settings',
  ],
};

export function useRole() {
  const { user } = useAuth();
  const role = user?.role ?? 'user';
  const capabilities = ROLE_CAPABILITIES[role] ?? [];

  return {
    role,
    isUser: role === 'user',
    isTeacher: role === 'teacher',
    isAdmin: role === 'admin',
    has: (cap: UserCapability) => capabilities.includes(cap),
  };
}
```

#### 2. Component `<RoleGate>` để ẩn/hiện UI theo capability

```tsx
// web/src/components/RoleGate.tsx
interface RoleGateProps {
  capability?: UserCapability;
  roles?: Array<'user' | 'teacher' | 'admin'>;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function RoleGate({ capability, roles, fallback = null, children }: RoleGateProps) {
  const { has, role } = useRole();
  if (capability && !has(capability)) return <>{fallback}</>;
  if (roles && !roles.includes(role)) return <>{fallback}</>;
  return <>{children}</>;
}
```

#### 3. Refactor `AppLayout.tsx` — sidebar dựa trên capability

```tsx
// web/src/components/AppLayout.tsx (refactored)
const SIDEBAR_GROUPS = [
  {
    label: 'Workspace',
    items: [
      { path: '/dashboard', label: 'Dashboard', icon: FileSearch,
        capability: 'upload_essay' as UserCapability },
      { path: '/upload', label: 'New Check', icon: Upload,
        capability: 'upload_essay' as UserCapability },
      // User KHÔNG thấy Batch Upload
      { path: '/batch-upload', label: 'Batch Check', icon: Layers,
        capability: 'view_class_history' as UserCapability },
      { path: '/history', label: 'History', icon: History,
        capability: 'view_own_history' as UserCapability },
    ],
  },
  {
    label: 'Teaching',
    roles: ['teacher', 'admin'],  // CHỈ teacher/admin
    items: [
      { path: '/teacher/classes', label: 'My Classes', icon: GraduationCap,
        capability: 'view_class_history' as UserCapability },
      { path: '/teacher/reviews', label: 'Pending Reviews', icon: ClipboardCheck,
        capability: 'override_verdict' as UserCapability },
    ],
  },
  {
    label: 'Administration',
    roles: ['admin'],  // CHỈ admin
    items: [
      { path: '/admin/users', label: 'Accounts', icon: Users,
        capability: 'manage_users' as UserCapability },
      { path: '/admin/system', label: 'System Health', icon: Activity,
        capability: 'system_settings' as UserCapability },
    ],
  },
  {
    label: 'Preferences',
    items: [
      { path: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];
```

---

### D. UI/UX Design — Specific cho từng role

#### 🟢 USER (Student) — Minimal & Focused

**Triết lý:** *"Một nút bấm, một kết quả."*

| Trang | Hiển thị |
|-------|----------|
| **Dashboard** | Chỉ thấy: "Tải bài lên" (CTA lớn) + 1 dòng "Bài gần nhất: X" + History list của riêng họ |
| **Upload** | Drag-drop đơn giản, không có batch option |
| **Report** | CIS score (lớn) + bảng verdict rút gọn (chỉ 3 cột: Citation / Status / Source) |
| **History** | Bài của tôi, không thấy bài người khác |
| **Settings** | Theme + Đổi mật khẩu + Đăng xuất (3 mục) |

**Ẩn đi đối với User:**
- ❌ Account Management
- ❌ Logic Trace, Document Inspector, Orphan Detection (chi tiết nâng cao)
- ❌ Override Verdict controls
- ❌ Multi-user dashboard
- ❌ System metrics

```
┌────────────────────────────────────────────────────┐
│  SourceLogic                            🌙 user ▼ │
├────────────────────────────────────────────────────┤
│  [Sidebar]        │  Dashboard                     │
│  ────────         │                                │
│  📊 Dashboard     │  Welcome back, An!             │
│  ⬆️  New Check    │                                │
│  📜 History       │  ┌──────────────────────────┐  │
│  ────────         │  │   📤  Tải bài lên        │  │
│  ⚙️  Settings     │  │   để kiểm tra trích dẫn  │  │
│                   │  └──────────────────────────┘  │
│                   │                                │
│                   │  Recent checks                  │
│                   │  • thesis_v3.pdf  ⭐ 97%       │
│                   │  • essay_2.pdf    ⚠️  62%      │
└────────────────────────────────────────────────────┘
```

#### 🟡 TEACHER — Pedagogical View

**Triết lý:** *"Lớp học của tôi, bài nộp của sinh viên tôi."*

**Bổ sung thêm (so với User):**

| Trang | Mô tả |
|-------|--------|
| **My Classes** | Danh sách lớp, mỗi lớp hiển thị: tên, số SV, bài đã nộp, CIS trung bình |
| **Class Detail** | Grid bài nộp của từng SV với CIS score, status |
| **Pending Reviews** | Hàng đợi verdict cần teacher xem lại (mismatched/hallucinated) |
| **Override Verdict** | Cho phép sửa verdict khi sinh viên giải thích |
| **Batch Upload** | Đổi tên → "Submit Class Assignment" |
| **Logic Trace** | Được truy cập để xem tại sao bị flagged |
| **Export** | CSV riêng theo lớp, tổng kết điểm |
| **Sidebar mới** | Nhóm "Teaching" hiển thị |

```
┌────────────────────────────────────────────────────┐
│  SourceLogic                          🌙 teacher ▼│
├────────────────────────────────────────────────────┤
│  [Sidebar]        │  Teaching Dashboard           │
│  ────────         │                                │
│  📊 Dashboard     │  Class: KHDL2023-A (32 SV)    │
│  ⬆️  New Check    │                                │
│  📚 My Classes ★  │  ┌─ Submitted: 28/32 ──────┐  │
│  ✓  Reviews (5)   │  │  Avg CIS:    78.4%       │  │
│  📜 History       │  │  Pending:    5 reviews   │  │
│  ────────         │  └──────────────────────────┘  │
│  🔍 Logic Trace   │                                │
│  ────────         │  Students needing review:      │
│  ⚙️  Settings     │  • An Nguyen  ⚠️  3 issues     │
│                   │  • Binh Tran  ⚠️  1 mismatch   │
│                   │  [View all 5]                  │
└────────────────────────────────────────────────────┘
```

#### 🔴 ADMIN — Full Power

**Triết lý:** *"Tôi cần thấy hết, sửa hết, xuất hết."*

**Bổ sung thêm (so với Teacher):**

| Trang | Mô tả |
|-------|--------|
| **All Essays** | Xem bài nộp của TOÀN BỘ user (không giới hạn lớp) |
| **User Management** | CRUD user, phân quyền, reset password |
| **System Health** | API key status, retrieval source health, cache hit rate |
| **Audit Log** | Override history, login attempts, system events |
| **Settings** | Tất cả settings + API key rotation + whitelist management |

```
┌────────────────────────────────────────────────────┐
│  SourceLogic                          🌙 admin ▼  │
├────────────────────────────────────────────────────┤
│  [Sidebar]        │  Admin Dashboard              │
│  ────────         │                                │
│  📊 Dashboard     │  System: 3 retrieval sources  │
│  ⬆️  New Check    │  ⏺ Crossref:  ✅ healthy     │
│  📚 Classes       │  ⏺ OpenAlex:  ⚠️ rate limit  │
│  ✓  Reviews (12)  │  ⏺ CORE API:  ✅ healthy     │
│  📜 History       │                                │
│  🔍 Logic Trace   │  Users: 47                    │
│  ────────         │  Active: 38 (12 teachers)     │
│  👥 Accounts ★    │  Essays today: 23             │
│  🛠 System        │                                │
│  📋 Audit Log     │  Cache: 1.2GB (2,134 entries) │
│  ────────         │                                │
│  ⚙️  Settings     │                                │
└────────────────────────────────────────────────────┘
```

---

## 🎨 III. Đề Xuất Design Direction (ngoài role-based)

### 1. Hệ thống màu phân biệt role (light + dark)

```css
/* web/src/design-system/role-tokens.css */
:root {
  /* Role badges */
  --role-user: #3b82f6;      /* Blue - Student */
  --role-teacher: #16a34a;   /* Green - Teacher */
  --role-admin: #a855f7;     /* Purple - Admin */

  /* Verdict palette (giữ nguyên) */
  --verdict-verified: #16a34a;
  --verdict-metadata-error: #ca8a04;
  --verdict-suspected: #dc2626;
  --verdict-unresolved: #6b7280;
  --verdict-resource: #a855f7;
}

[data-theme="dark"] {
  --role-user: #60a5fa;
  --role-teacher: #4ade80;
  --role-admin: #c084fc;
}
```

### 2. Report Page — theo role, hiển thị KHÁC NHAU

**User thấy:**
```
┌─ Report ──────────────────────────────────┐
│                                            │
│  thesis_v3.pdf            [⬇ Download]     │
│                                            │
│  ┌────────────────────────────────────┐   │
│  │   ⭐  Citation Integrity Score     │   │
│  │        97.4 / 100                  │   │
│  │   29 verified · 1 needs review     │   │
│  └────────────────────────────────────┘   │
│                                            │
│  Citations (30)                            │
│  ┌────────────────────────────────────┐   │
│  │ [1] Vaswani et al.     ✅ Verified  │   │
│  │ [2] Devlin et al.      ✅ Verified  │   │
│  │ [3] Brown et al.       ⚠️  Check    │   │
│  └────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

**Teacher/Admin thấy thêm:**
```
│  ┌─ Advanced (Teacher) ─────────────────┐  │
│  │ Style profile:    APA_LIKE (87%)     │  │
│  │ Mapping issues:   2 ambiguous        │  │
│  │ Sources: 3 of 4 healthy              │  │
│  │ [View Logic Trace] [Edit Override]   │  │
│  └──────────────────────────────────────┘  │
```

### 3. Empty states khác nhau theo role

| Role | Empty state copy |
|------|------------------|
| User | "Chưa có bài nào? Tải lên ngay để bắt đầu" |
| Teacher | "Chưa có lớp nào. Tạo lớp để bắt đầu theo dõi" |
| Admin | "Hệ thống sẵn sàng. 0 users, 0 essays trong 24h qua" |

---

## 📋 IV. Roadmap Triển Khai (đề xuất)

### Phase 1: Backend Foundation (1-2 ngày)
- [ ] Thêm `teacher` role vào enum + DB migration
- [ ] Tạo `Class` model
- [ ] Thêm API endpoints cho teacher (`/api/teacher/*`)
- [ ] Cập nhật JWT payload để chứa `class_ids`, `capabilities`

### Phase 2: Frontend Role System (2-3 ngày)
- [ ] Tạo `useRole()` hook
- [ ] Tạo `<RoleGate>` component
- [ ] Refactor `AppLayout.tsx` với capability-based sidebar
- [ ] Refactor `ProtectedRoute.tsx` thành `RoleProtectedRoute`
- [ ] Ẩn các route nâng cao (LogicTrace, DocumentInspector, OrphanDetection) đối với user

### Phase 3: Teacher-specific Pages (3-4 ngày)
- [ ] `MyClassesPage.tsx`
- [ ] `ClassDetailPage.tsx`
- [ ] `PendingReviewsPage.tsx`
- [ ] Refactor `BatchUploadPage.tsx` → `ClassAssignmentPage.tsx`
- [ ] Cập nhật `OverrideControls.tsx` cho teacher
- [ ] Thêm CSV export theo lớp

### Phase 4: Admin-specific Enhancements (2-3 ngày)
- [ ] `SystemHealthPage.tsx` (API source status, cache)
- [ ] `AuditLogPage.tsx`
- [ ] Refactor `AccountManagementPage.tsx` thêm column "Class" + bulk action

### Phase 5: Polish & Visual Identity (1-2 ngày)
- [ ] Role-colored badges
- [ ] Empty states riêng cho từng role
- [ ] HelpModal phân nhánh theo role
- [ ] Ẩn demo credentials khi production (`VITE_DEMO_MODE === 'true'`)
- [ ] Thêm `RoleSwitcher` (chỉ dev) để test

---

## ⚠️ V. Vấn Đề Cần Lưu Ý

### 1. Backward compatibility
Hiện `user` role đang bao gồm tất cả user thường. Cần migration strategy:
- **Option A:** Đổi `user` → `student`, thêm `teacher`
- **Option B:** Giữ `user` cho student, thêm `teacher` mới
- **Đề xuất:** Option B để không break existing users

### 2. Security
- Override verdict của teacher cần audit log (đã có pattern trong codebase — `OverrideRecord`)
- Teacher chỉ xem được lớp mình phụ trách — backend phải enforce
- Không hiển thị demo credentials ở production (xem `LoginPage.tsx:261-271`)

### 3. Mobile considerations
- Sidebar 17 items trên mobile rất cồng kềnh
- Đề xuất: User thấy 4 items, Teacher 7 items, Admin 10 items (collapse nhóm Administration)

### 4. Dark mode
Mọi role-based component phải test ở cả light + dark mode (đặc biệt sidebar với role badges).

---

## 🏆 VI. Tóm Tắt Giá Trị Mang Lại

| Cho đối tượng | Lợi ích |
|---------------|---------|
| **Sinh viên** | UI gọn, ít bị overwhelm, tập trung nộp bài → tăng adoption |
| **Giảng viên** | Workflow theo dõi lớp học, override verdict khi cần → tiết kiệm thời gian |
| **Admin** | Quản lý tập trung, không phải support từng role → giảm cognitive load |
| **Dự án** | Phân cấp rõ ràng → dễ demo cho hội đồng, dễ onboard user mới |

---

## 💬 VII. Câu Hỏi Cần Xác Nhận Trước Khi Code

1. **Database migration** — Bạn muốn giữ `user` cho student hay rename thành `student`?
2. **Class model** — Lớp học chỉ cần `name + teacher + students` hay cần thêm `term`, `course_code`?
3. **Teacher override workflow** — Khi teacher override verdict, có cần student nhận notification không? (qua toast/email?)
4. **First admin bootstrap** — Tài khoản admin đầu tiên tạo thế nào? (Qua env var, CLI command, hay auto-create khi DB trống?)
5. **Demo data** — Có cần seed data (classes, sample essays) để demo không?

---

## 📎 Phụ Lục: Files Liên Quan

| File | Vai trò | Action |
|------|---------|--------|
| `src/integrity_checker/api/routes/auth.py` | Login + JWT | Cập nhật để nhận role mới |
| `src/integrity_checker/api/routes/users.py` | User CRUD | Mở rộng role enum |
| `src/integrity_checker/db/models.py` | ORM models | Thêm `Class` model |
| `src/integrity_checker/api/deps.py` | Auth dependencies | Thêm `require_teacher` |
| `web/src/contexts/AuthContext.tsx` | Auth state | Cập nhật user type |
| `web/src/components/AppLayout.tsx` | Sidebar | Refactor với capability groups |
| `web/src/components/ProtectedRoute.tsx` | Route guard | Mở rộng role check |
| `web/src/pages/DashboardPage.tsx` | Dashboard | Phân nhánh theo role |
| `web/src/pages/AccountManagementPage.tsx` | Admin user mgmt | Thêm column "Class" |
| `web/src/pages/LoginPage.tsx` | Login | Ẩn demo creds khi prod |
