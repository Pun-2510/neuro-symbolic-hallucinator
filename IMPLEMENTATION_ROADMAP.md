# 📋 Implementation Roadmap — SourceLogic

> **Project**: SourceLogic — Academic Source Verification (Đồ án Tốt nghiệp)
> **Created**: 2026-10-14
> **Deadline**: 3 tháng (khoảng 2027-01-14)
> **Source documents**:
> - `docs/UX_UI_COMPREHENSIVE_AUDIT_REPORT.md` (235 findings: 17 Critical / 49 High / 66 Medium / 103 Low)
> - `ROLES_PLAN.md` (User → Teacher → Admin phân cấp)
>
> **Triết lý**: Foundation trước → Roles sau → Polish cuối. Mỗi phase unblock phase kế tiếp, tránh xung đột.

---

## 🗺️ Tổng quan 5 Phase

| # | Phase | Mục tiêu | Effort | Phụ thuộc |
|---|-------|----------|--------|-----------|
| **1** | Foundation Fixes | Sửa 17 Critical + 12 Quick-win High, app production-ready | 1 tuần (5 ngày) | — |
| **2** | Polish Layer | A11y, contrast, code-splitting, i18n infrastructure | 1 tuần (5 ngày) | Phase 1 |
| **3** | Role System | Backend: thêm `teacher` + Class model. Frontend: `useRole()` + `RoleGate` | 1 tuần (5 ngày) | Phase 1 (đặc biệt C6) |
| **4** | Teacher & Admin Pages | `MyClassesPage`, `PendingReviewsPage`, `SystemHealthPage`, `AuditLogPage` | 2 tuần (10 ngày) | Phase 3 |
| **5** | Final Polish | React Query, split god components, confirmation modal, full-text search | 1 tuần (5 ngày) | Phase 2-4 |

**Tổng effort**: ~30 ngày làm việc (6 tuần). Deadline 3 tháng = ~12 tuần → có buffer ~6 tuần cho testing, fixes phát sinh, polish phụ.

**Nguyên tắc quan trọng:**
- Phase 1 phải xong **trước** Phase 3 vì ROLES_PLAN cần `AuthContext` sạch (không hardcoded admin)
- Phase 1 phải xong **trước** Phase 2 vì code-splitting dễ conflict với refactor lớn
- Phase 4 phụ thuộc Phase 3 vì cần backend `/api/teacher/*` mới có data
- Phase 5 cuối cùng vì touch nhiều file, dễ vỡ nếu làm sớm

---

## 🤖 Quy Tắc Commit Cho Agent (BẮT BUỘC)

**Nguyên tắc**: **Mỗi fix hoặc feature phải commit RIÊNG sau khi code + test đầy đủ. KHÔNG ĐƯỢC gộp nhiều fix vào 1 commit lớn.**

### Quy tắc chi tiết

1. **Một task = một commit**: Hoàn thành xong 1 task trong bảng (vd: "1.1 Xóa `lib/api.ts`") → verify acceptance → commit ngay. KHÔNG đợi hết ngày, hết tuần, hay hết phase.

2. **Tiêu chí "code + test đầy đủ" trước khi commit**:
   - Code đã viết xong theo acceptance criteria
   - Test pass: `pytest` (backend) hoặc `pnpm build` (frontend) không lỗi
   - Nếu có test liên quan đã chạy và pass
   - Self-review: không còn `console.log`, `TODO`, code thừa

3. **Commit message format**:
   ```bash
   # Fix bug
   git commit -m "fix(phase-N): mô tả ngắn gọn (task ID)
   
   - Chi tiết thay đổi 1
   - Chi tiết thay đổi 2
   - Acceptance: <tiêu chí đạt được>
   
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

   # Feature mới
   git commit -m "feat(phase-N): mô tả feature (task ID)
   
   - File mới: web/src/hooks/useRole.ts
   - Exports: useRole, ROLE_CAPABILITIES
   - Test: 5/5 pass
   
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"

   # Refactor
   git commit -m "refactor(phase-N): mô tả refactor (task ID)
   
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
   ```

4. **Tại sao phải commit nhỏ**:
   - **Rollback dễ**: Task 2.3 gây bug → chỉ `git revert` 1 commit, không ảnh hưởng task 1.1-2.2
   - **Code review dễ**: Reviewer thấy diff < 200 dòng, hiểu ngay
   - **Conflict giảm**: Nếu nhiều agent làm song song, conflict nhỏ dễ resolve
   - **Bisect chính xác**: Khi test fail sau này, `git bisect` tìm được commit gây bug
   - **Lịch sử rõ ràng**: Mỗi commit là 1 đơn vị công việc hoàn chỉnh, dễ truy nguyên

5. **Các task có thể gộp commit** (NGOẠI LỆ):
   - **Atomic UI changes**: Một modal cần 3 file (component + dialog + form) → 1 commit OK
   - **Test + implementation**: Code + test cho cùng 1 feature → 1 commit OK
   - **i18n key additions**: Thêm 1 loạt keys cho cùng 1 feature → 1 commit OK
   - **Migration files**: Backend migration + model update phải đi cùng nhau

6. **KHÔNG được gộp commit**:
   - ❌ Gộp 5 fixes khác nhau vào "fix(phase-1): various fixes"
   - ❌ Gộp fix bug + thêm feature mới
   - ❌ Gộp refactor + fix bug (refactor riêng, fix riêng)
   - ❌ Commit cả ngày/tuần/phase vào 1 commit lớn

7. **Branch strategy**:
   ```bash
   # Mỗi phase = 1 branch
   git checkout -b fix/phase-1-foundation
   git checkout -b feat/phase-3-roles
   git checkout -b feat/phase-4-pages

   # Commit từng task lên branch đó
   # Khi phase xong → merge vào main với 1 PR (nhiều commits)
   ```

8. **Ví dụ timeline Day 1**:
   ```
   09:00 - Task 1.1: Xóa lib/api.ts
   09:05 - Verify: grep không còn import
   09:10 - Commit: "refactor(phase-1): remove legacy lib/api.ts (1.1)"

   09:15 - Task 1.2: Migrate DashboardPage
   10:15 - Verify: grep không còn raw fetch, build pass
   10:20 - Commit: "refactor(phase-1): migrate DashboardPage to api/client.ts (1.2)"

   10:25 - Task 1.3: Migrate HistoryPage
   11:25 - Verify: tương tự 1.2
   11:30 - Commit: "refactor(phase-1): migrate HistoryPage to api/client.ts (1.3)"

   ...
   ```

9. **Khi gặp bug trong lúc làm task khác**:
   - KHÔNG sửa + gộp vào commit hiện tại
   - Tạo commit riêng: `fix: <mô tả bug>` rồi mới tiếp task đang làm
   - Hoặc stash, làm task hiện tại xong, quay lại fix bug

10. **Trước khi commit, luôn check**:
    ```bash
    git status                    # Xem files changed
    git diff --stat               # Số dòng thay đổi
    # Nếu diff > 500 dòng → CÂN NHẮC tách commit
    # Nếu diff có nhiều concerns khác nhau → TÁCH commit
    ```

---

## Phase 1: Foundation Fixes (Tuần 1)

**Mục tiêu**: Sửa tất cả Critical (C1-C17) có tác động lớn nhất + Quick-win High. Sau phase này, app deploy được và không có bug "embarrassing" trước hội đồng.

**Exit criteria**:
- [x] Chỉ còn 1 API layer (`api/client.ts`), `lib/api.ts` đã xóa
- [x] Không còn `window.location.reload()` ở frontend (chỉ còn ở ErrorBoundary fallback, OK)
- [x] Không còn hardcoded `localhost:8000` ở bất kỳ đâu
- [x] Không còn hardcoded admin user
- [x] `text-slate-400/500` không còn dùng cho body text (còn ở decorative/secondary, OK)
- [x] Tất cả 4 trang dùng `api/client.ts` (không raw fetch)

---

### Day 1: API Consolidation + Security Quick Wins (5 tasks, < 1 ngày)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 1.1 | Xóa `lib/api.ts` | `web/src/lib/api.ts` | 5 min | File deleted; grep không còn import từ `lib/api` | [x] |
| 1.2 | Migrate `DashboardPage` sang `api/client.ts` | `web/src/pages/DashboardPage.tsx:62` | 1h | Raw `fetch('/api/...')` → `api.getEssays()` | [x] |
| 1.3 | Migrate `HistoryPage` sang `api/client.ts` | `web/src/pages/HistoryPage.tsx:47` | 1h | Tương tự 1.2 | [x] |
| 1.4 | Migrate `SettingsPage` (cache + 2 chỗ khác) | `web/src/pages/SettingsPage.tsx:237` | 1.5h | Tất cả raw fetch → api client | [x] |
| 1.5 | Bỏ hardcoded admin user | `web/src/contexts/AuthContext.tsx:9` | 30 min | `isAdmin` = `user?.role === 'admin'` only, không fallback | [x] |

**Pre-check**: tìm function nào trong `lib/api.ts` chưa có trong `api/client.ts` (audit report nói `getAllEssays`, `deleteEssay`, `clearCache`). Nếu thiếu, bổ sung vào `api/client.ts` trước khi migrate.

**Verification**:
```bash
# Tìm raw fetch còn sót
grep -rn "fetch(" web/src/pages/ web/src/components/
# Tìm import từ lib/api
grep -rn "from.*lib/api" web/src/
```

---

### Day 2: Bug Fixes + UX Quick Wins (4 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 2.1 | Fix CORS hardcode trong `AvatarUpload` | `web/src/components/AvatarUpload.tsx` | 30 min | URL = `/api/users/me/avatar` (relative) | [x] |
| 2.2 | Bỏ `window.location.reload()` ở `SettingsPage` | `web/src/pages/SettingsPage.tsx:83` | 2h | Đổi sang SPA state update + i18n.changeLanguage() | [x] |
| 2.3 | Bỏ `window.location.reload()` ở `main.tsx` (i18n init) | `web/src/main.tsx:29` | 1h | Dùng React state cho language change | [x] |
| 2.4 | Fix Dashboard "Verified Rate" calc | `web/src/pages/DashboardPage.tsx:168-172` | 2h | Tính từ verdicts data, hoặc xóa card nếu backend không expose | [x] |

**Lưu ý cho 2.2-2.3**: Phase 2 mới wire i18n đầy đủ, nhưng bỏ `reload()` ngay bây giờ để tránh UX tệ.

---

### Day 3: Code-Splitting (1 task lớn, nhưng bounded)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 3.1 | `React.lazy` cho 16 routes | `web/src/router.tsx` | 3h | Tất cả page imports dùng `lazy(() => import(...))` | [x] |
| 3.2 | Wrap routes trong `<Suspense>` với skeleton fallback | `web/src/router.tsx` | 1h | Mỗi lazy route có `fallback={<PageSkeleton />}` | [x] |
| 3.3 | Add `manualChunks` trong `vite.config.ts` | `web/vite.config.ts` | 1h | `vendor: ['react', 'react-dom']`, `ui: ['lucide-react', '@radix-ui/*']` | [x] |

**Acceptance**: Initial bundle giảm từ 592KB → < 250KB. Test bằng `pnpm build` rồi check `dist/assets/index-*.js` size.

---

### Day 4-5: Critical A11y + Polish (6 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 4.1 | Add skip-to-content link | `web/src/components/AppLayout.tsx:73` | 1h | Visually-hidden link đầu layout, focus → visible | [x] |
| 4.2 | Add `<main id="main-content" tabIndex={-1}>` | `web/src/components/AppLayout.tsx` | 30 min | Main element có id, tabindex | [x] |
| 4.3 | `role="dialog"`, `aria-modal="true"` cho `CitationDetailDrawer` | `web/src/components/CitationDetailDrawer.tsx:147-180` | 2h | Có `aria-labelledby` trỏ tới title | [x] |
| 4.4 | Implement focus trap cho drawer | `web/src/components/CitationDetailDrawer.tsx` | 2h | Dùng `focus-trap-react` | [x] |
| 4.5 | `aria-label` cho 2 search inputs | `web/src/components/CitationGraphView.tsx:715`, `web/src/components/VerdictTable.tsx:110` | 30 min | `aria-label="Search citations"`, `aria-hidden="true"` cho icon | [x] |
| 4.6 | Replace `alert()` và `confirm()` với `Toast` + `ConfirmationModal` | 3+ pages (cần tìm) | 3h | Tất cả native dialogs đã thay | [x] |

**Tìm native dialogs**:
```bash
grep -rn "alert(\|confirm(" web/src/pages/ web/src/components/
```

---

### Day 5: Verification cuối Phase 1

```bash
# 1. Build pass
cd web && pnpm build

# 2. Không còn raw fetch trong pages
grep -rn "fetch(" web/src/pages/ web/src/components/ | grep -v "node_modules"

# 3. Không còn lib/api
test -f web/src/lib/api.ts && echo "FAIL" || echo "OK"

# 4. Không còn hardcoded localhost
grep -rn "localhost:8000" web/src/

# 5. Bundle size check
ls -la web/dist/assets/ | head -20
```

**Commit pattern**:
```bash
git checkout -b fix/phase-1-foundation
git commit -m "fix(phase1): consolidate API, remove hardcoded admin, add a11y (v1.13)"
```

---

## Phase 2: Polish Layer (Tuần 2)

**Mục tiêu**: A11y compliance, code quality, prepare foundation cho i18n wiring đầy đủ (defer đến Phase 5).

**Exit criteria**:
- [x] Contrast issues (text-slate-400/500) fixed ở tất cả body text (còn decorative, OK)
- [x] Touch targets ≥ 44x44px trên mobile
- [x] Filter chips có `aria-pressed` và `role="group"`
- [x] God components (`CitationGraphView`, `EssayPage`) bắt đầu được split
- [x] Custom hooks layer khởi tạo (useDebounce, useLocalStorage, useEssayPolling)

---

### Day 6-7: Contrast & Touch Targets (8 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 6.1 | Replace `text-slate-400/500` cho body text | Toàn bộ `web/src/pages/**`, `web/src/components/**` | 4h | Body text dùng `text-slate-600`+ (light mode) | [x] |
| 6.2 | Touch target min 44x44px | Tất cả icon buttons | 2h | `min-h-11 min-w-11` cho icon-only buttons | [x] |
| 6.3 | `aria-pressed` cho filter chips | `AccountManagementPage`, `IssuesPage` | 1h | Mỗi filter chip có `aria-pressed={isActive}` | [x] |
| 6.4 | `role="group" aria-label` cho filter groups | Tương tự 6.3 | 1h | Filter group có label mô tả | [x] |

---

### Day 8: Fix Polling Race Conditions (3 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 8.1 | `AbortController` cho `IssuesPage` | `web/src/pages/IssuesPage.tsx` | 2h | Fetch cancelled on unmount | [x] |
| 8.2 | `AbortController` cho `LogicTracePage` | `web/src/pages/LogicTracePage.tsx` | 1.5h | Tương tự 8.1 | [x] |
| 8.3 | `AbortController` cho `DocumentInspectorPage` | `web/src/pages/DocumentInspectorPage.tsx` | 1.5h | Tương tự 8.1 | [x] |

**Pattern**:
```ts
useEffect(() => {
  const controller = new AbortController();
  fetchData(controller.signal);
  return () => controller.abort();
}, [essayId]);
```

---

### Day 9-10: Split God Components (bắt đầu, không xong hết)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 9.1 | Extract `useDebounce` hook | `web/src/hooks/useDebounce.ts` (mới) | 1h | Hook reusable, có test | [x] |
| 9.2 | Extract `useLocalStorage` hook | `web/src/hooks/useLocalStorage.ts` (mới) | 1h | Type-safe generic | [x] |
| 9.3 | Split `CitationGraphView` (866 LOC) thành 3 sub-components | `web/src/components/CitationGraphView.tsx` | 6h | `GraphNode`, `GraphEdge`, `GraphControls` extracted | [x] (1 sub: `CitationGraphControls`) |
| 9.4 | Split `EssayPage` (764 LOC) thành 3 sub-components | `web/src/pages/EssayPage.tsx` | 6h | `EssayHeader`, `VerdictList`, `ActionToolbar` extracted | [x] (1 sub: `EssayHeader`) |

**Lưu ý**: Phase 5 mới finish split hoàn toàn, Phase 2 chỉ extract 2-3 sub-components quan trọng nhất.

---

## Phase 3: Role System Foundation (Tuần 3)

**Mục tiêu**: Backend hỗ trợ 3 roles (`user` / `teacher` / `admin`), Frontend có `useRole()` + `<RoleGate>` để gate UI. Có thể chưa cần Teacher pages, nhưng role plumbing phải xong.

**Prerequisites**: Phase 1 đã fix C6 (hardcoded admin) — **BẮT BUỘC** vì nếu không, thêm `teacher` role sẽ có 2 lớp bypass auth.

**Exit criteria**:
- [x] Backend enum có `teacher` + migration script
- [x] Class model + endpoints `/api/teacher/classes/*` hoạt động
- [x] JWT payload có `role` đúng
- [x] Frontend `useRole()` hook + `<RoleGate>` component
- [x] `AppLayout` sidebar dùng capability groups
- [x] Backend enforce: teacher chỉ xem class của mình

---

### Day 11-12: Backend Role Expansion (5 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 11.1 | Mở rộng `UserRole` enum thêm `teacher` | `src/integrity_checker/db/models.py` | 1h | Enum = `user` / `teacher` / `admin` | [x] |
| 11.2 | Tạo Alembic migration | `alembic/versions/xxx_add_teacher_role.py` (mới) | 2h | Migration chạy thành công, rollback OK | [x] (inline ALTER block, not Alembic) |
| 11.3 | Tạo `Class` model | `src/integrity_checker/db/models.py` | 2h | Class: id, name, teacher_id, student_ids, created_at | [x] |
| 11.4 | Thêm field `institution`, `class_id` cho User | `src/integrity_checker/db/models.py` | 1h | User model updated | [x] (institution + can_override_verdicts, no class_id — many-to-many via ClassMembership) |
| 11.5 | Update seed script (nếu có) | `scripts/seed.py` | 1h | Seed 1 teacher account + 1 sample class | [x] (hardcoded teacher user + auto-seed in main.py) |

**Migration safety**:
- Default `role = 'user'` cho existing users (không break backward compat)
- `institution` và `class_id` nullable

---

### Day 13: Backend API + Auth Updates (4 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 13.1 | Cập nhật `auth.py` để encode `role` đúng | `src/integrity_checker/api/routes/auth.py` | 2h | JWT payload có `role` | [x] |
| 13.2 | Tạo `/api/teacher/*` endpoints | `src/integrity_checker/api/routes/teacher.py` (mới) | 4h | `GET /teacher/classes`, `GET /teacher/classes/{id}/students`, `GET /teacher/classes/{id}/essays`, `GET /teacher/dashboard` | [x] (7 endpoints, bao gồm cả POST/DELETE) |
| 13.3 | Thêm `require_teacher` dependency | `src/integrity_checker/api/deps.py` | 1h | FastAPI dependency check `role == 'teacher' or 'admin'` | [x] |
| 13.4 | Thêm `require_admin` nếu chưa có | `src/integrity_checker/api/deps.py` | 30 min | Check `role == 'admin'` | [x] (đã có sẵn từ trước) |

**Authorization rule**: Teacher chỉ xem được essays của class mình phụ trách. Enforce ở API layer (không tin tưởng frontend).

---

### Day 14-15: Frontend Role System (6 tasks)

| # | Task | File | Effort | Acceptance | Status |
|---|------|------|--------|------------|--------|
| 14.1 | Tạo `useRole()` hook | `web/src/hooks/useRole.ts` (mới) | 2h | Hook với `role`, `isUser`, `isTeacher`, `isAdmin`, `has(cap)` | [x] |
| 14.2 | Tạo `ROLE_CAPABILITIES` map | `web/src/hooks/useRole.ts` | 1h | Map role → capabilities (theo ROLES_PLAN) | [x] |
| 14.3 | Tạo `<RoleGate>` component | `web/src/components/RoleGate.tsx` (mới) | 1h | Support cả `capability` và `roles` props | [x] |
| 14.4 | Refactor `AppLayout` sidebar với capability groups | `web/src/components/AppLayout.tsx:175-253` | 4h | 4 groups: Workspace / Teaching / Administration / Preferences | [x] |
| 14.5 | Refactor `ProtectedRoute` thành `RoleProtectedRoute` | `web/src/components/ProtectedRoute.tsx` | 1h | Support `requiredRole` prop | [x] (backward-compat: `adminOnly` + new `requiredRoles` + `requiredCapabilities`) |
| 14.6 | Wrap `LogicTracePage`, `DocumentInspectorPage`, `OrphanDetectionPage` với `<RoleGate>` | 3 pages | 1h | User thường không thấy menu + redirect nếu access direct | [x] (dùng `ProtectedRoute requiredCapabilities`) |

**Visibility matrix** (theo ROLES_PLAN):

| Page | User | Teacher | Admin |
|------|------|---------|-------|
| Dashboard | ✓ | ✓ | ✓ |
| Upload | ✓ | ✓ | ✓ |
| Batch Upload | ✗ | ✓ | ✓ |
| History | own only | own + class | all |
| Logic Trace | ✗ | ✓ | ✓ |
| Document Inspector | ✗ | ✓ | ✓ |
| Orphan Detection | ✗ | ✓ | ✓ |
| My Classes | ✗ | ✓ | ✓ |
| Pending Reviews | ✗ | ✓ | ✓ |
| Account Management | ✗ | ✗ | ✓ |
| System Health | ✗ | ✗ | ✓ |
| Audit Log | ✗ | ✗ | ✓ |
| Settings | ✓ | ✓ | ✓ |

---

## Phase 4: Teacher & Admin Pages (Tuần 4-5)

**Mục tiêu**: Build out Teacher-specific và Admin-specific pages theo ROLES_PLAN.

**Exit criteria**:
- [ ] Teacher có dashboard riêng, xem được lớp + bài nộp
- [ ] Admin có System Health + Audit Log
- [ ] Pending Reviews workflow hoạt động
- [ ] Batch Upload rename thành Class Assignment cho teacher

---

### Day 16-18: Teacher Pages (5 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 16.1 | Tạo `MyClassesPage` | `web/src/pages/MyClassesPage.tsx` (mới) | 6h | List classes với stats (số SV, bài nộp, avg CIS) |
| 16.2 | Tạo `ClassDetailPage` | `web/src/pages/ClassDetailPage.tsx` (mới) | 6h | Grid bài nộp của từng SV, click → EssayPage |
| 16.3 | Tạo `PendingReviewsPage` | `web/src/pages/PendingReviewsPage.tsx` (mới) | 4h | Queue verdicts cần teacher xem lại |
| 16.4 | Refactor `BatchUploadPage` → `ClassAssignmentPage` | `web/src/pages/BatchUploadPage.tsx` | 4h | UI cho teacher submit cả lớp |
| 16.5 | Cập nhật `OverrideControls` cho teacher context | `web/src/components/OverrideControls.tsx` | 3h | Có audit log khi teacher override |

---

### Day 19-20: Admin Pages (4 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 19.1 | Tạo `SystemHealthPage` | `web/src/pages/SystemHealthPage.tsx` (mới) | 6h | API source status, cache hit rate, error rate |
| 19.2 | Tạo `AuditLogPage` | `web/src/pages/AuditLogPage.tsx` (mới) | 5h | Override history, login attempts, system events |
| 19.3 | Cập nhật `AccountManagementPage` với column "Class" | `web/src/pages/AccountManagementPage.tsx` | 3h | Bulk action: assign user to class |
| 19.4 | Thêm `can_override_verdicts` field cho teacher | `src/integrity_checker/db/models.py` | 1h | Có thể config per-teacher |

---

### Day 21-22: Backend Endpoints cho Pages mới (4 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 21.1 | Backend `/api/system/health` | `src/integrity_checker/api/routes/health.py` | 3h | Source availability, quota, cache stats |
| 21.2 | Backend `/api/audit/log` | `src/integrity_checker/api/routes/audit.py` (mới) | 4h | Query audit log, filter by user/action/date |
| 21.3 | Backend `/api/teacher/dashboard` stats | `src/integrity_checker/api/routes/teacher.py` | 3h | Aggregated metrics cho 1 teacher |
| 21.4 | CSV export theo class | `src/integrity_checker/api/routes/export.py` | 2h | `GET /teacher/classes/{id}/export.csv` |

---

### Day 23: Polished Visual Identity (3 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 23.1 | Add role-colored badges | `web/src/design-system/role-tokens.css` (mới) | 2h | User=blue, Teacher=green, Admin=purple |
| 23.2 | Empty states riêng cho từng role | 3 pages | 2h | User: "Tải bài lên", Teacher: "Tạo lớp", Admin: "0 users" |
| 23.3 | Ẩn demo credentials khi production | `web/src/pages/LoginPage.tsx:261-271` | 1h | `import.meta.env.VITE_DEMO_MODE === 'true'` |

---

## Phase 5: Final Polish (Tuần 6)

**Mục tiêu**: React Query adoption, finish god component splits, ConfirmationModal, full-text search. Sau phase này, app ready cho thesis defense.

**Exit criteria**:
- [ ] Tất cả 5 polling pages dùng React Query
- [ ] Không còn `any` type trong TypeScript
- [ ] ConfirmationModal dùng cho tất cả destructive actions
- [ ] Full-text search hoạt động ở Dashboard + History + Verdict
- [ ] Test coverage: Vitest cho hooks + Playwright e2e cho top 10 flows

---

### Day 24-25: React Query Migration (5 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 24.1 | Install `@tanstack/react-query` | `web/package.json` | 30 min | Dep added, build pass |
| 24.2 | Setup `QueryClientProvider` | `web/src/main.tsx` | 1h | Provider wrap toàn app |
| 24.3 | Refactor `DashboardPage` polling → `useQuery` | `web/src/pages/DashboardPage.tsx` | 3h | `refetchInterval: 10_000, staleTime: 5_000` |
| 24.4 | Refactor `HistoryPage`, `EssayPage`, `ProcessingPage` → `useQuery` | 3 pages | 6h | Tương tự 24.3 |
| 24.5 | `useMutation` cho override với optimistic update | `EssayPage`, `OverrideControls` | 3h | UI update ngay, rollback on error |

**Lợi ích**: Bỏ được 5 file `fetch + setInterval + setState + try/catch` riêng lẻ.

---

### Day 26-27: ConfirmationModal & UX Consistency (4 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 26.1 | Tạo `ConfirmationModal` dùng Radix Dialog | `web/src/components/ConfirmationModal.tsx` (mới) | 2h | API: `open`, `title`, `message`, `onConfirm` |
| 26.2 | Replace tất cả `confirm()` calls | 3+ pages | 2h | Native confirm → ConfirmationModal |
| 26.3 | `StatCard` reusable (3 implementations → 1) | `web/src/components/StatCard.tsx` | 2h | Cùng 1 component, variants qua props |
| 26.4 | Date format chuẩn hóa → "Oct 14, 2026" | 3+ pages | 1h | Helper function `formatDate()` |

---

### Day 28: Full-text Search (2 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 28.1 | Full-text search ở `HistoryPage` | `web/src/pages/HistoryPage.tsx` | 3h | Search across filename + author + date |
| 28.2 | Full-text search ở `VerdictTable` | `web/src/components/VerdictTable.tsx` | 2h | Search citation text + author + venue |

---

### Day 29-30: Test Coverage (3 tasks)

| # | Task | File | Effort | Acceptance |
|---|------|------|--------|------------|
| 29.1 | Setup Vitest | `web/vitest.config.ts` (mới) | 2h | Test cho hooks (`useRole`, `useDebounce`) |
| 29.2 | Unit tests cho `useRole()` | `web/src/hooks/useRole.test.ts` (mới) | 2h | 5+ test cases |
| 29.3 | Playwright e2e cho 10 critical flows | `web/e2e/*.spec.ts` | 6h | Login, upload, view report, override, admin user CRUD, teacher class view |

**10 critical flows**:
1. Login as user
2. Login as teacher
3. Login as admin
4. Upload PDF
5. View report
6. Override verdict (teacher)
7. Create class (teacher)
8. View class essays (teacher)
9. Create user (admin)
10. View system health (admin)

---

## 📅 Timeline Summary (3 tháng = 12 tuần)

| Tuần | Phase | Công việc chính |
|------|-------|-----------------|
| **1** | Phase 1 | API consolidation, security fixes, code-splitting, critical a11y |
| **2** | Phase 2 | Contrast, touch targets, polling races, split god components (start) |
| **3** | Phase 3 | Backend: teacher role + Class model. Frontend: useRole + RoleGate + AppLayout |
| **4-5** | Phase 4 | Teacher pages, Admin pages, backend endpoints, visual identity |
| **6** | Phase 5 | React Query, ConfirmationModal, full-text search, tests |
| **7-8** | Buffer | Fix bugs từ testing, code review, polish phụ |
| **9-10** | Buffer | Test e2e toàn diện, fix edge cases, performance optimization |
| **11** | Buffer | Demo prep: seed data, screenshots, video |
| **12** | Defense | Bảo vệ, fix issues từ feedback hội đồng |

**Buffer 6 tuần** là cần thiết vì:
- Code review thường phát hiện 20-30% issues mới
- E2E tests luôn có flaky tests cần fix
- Hội đồng thường yêu cầu thêm features nhỏ
- Documentation (CLAUDE.md, README) cần update

---

## 🔗 Dependency Graph (Visual)

```
Phase 1 (Foundation)
├── C6: Fix hardcoded admin ─────────────┐
├── C2: Consolidate API                   │
├── C5: Fix CORS hardcode                 │
└── C14: Code-splitting                   │
                                         │
                                         ▼
Phase 3 (Role System) ◄──────────────────┘
├── Backend: UserRole enum + migration
├── Backend: Class model
├── Backend: /api/teacher/* endpoints
├── Frontend: useRole() hook
├── Frontend: <RoleGate> component
└── Frontend: AppLayout refactor
            │
            ▼
Phase 4 (Teacher & Admin Pages)
├── Teacher: MyClassesPage, ClassDetailPage, PendingReviewsPage
├── Admin: SystemHealthPage, AuditLogPage
└── Visual: role badges, empty states

Phase 2 (Polish Layer) ── có thể chạy song song với Phase 3 ──
├── A11y: contrast, touch targets, ARIA
├── Quality: split god components
└── Polling race fixes

Phase 5 (Final Polish) ◄── cuối cùng, touch nhiều ──
├── React Query (refactor 5 pages)
├── ConfirmationModal
├── Full-text search
└── Test coverage
```

**Critical path**: Phase 1 → Phase 3 → Phase 4. Phase 2 và Phase 5 có thể overlap.

---

## ⚠️ Rủi ro & Mitigation

| Rủi ro | Xác suất | Tác động | Mitigation |
|--------|----------|----------|------------|
| Migration script corrupt existing users | Trung bình | Cao | Test migration trên DB copy trước; backup trước khi chạy |
| ROLES_PLAN breaking changes cho existing UI | Cao | Trung bình | Giữ `user` role cho student (Option B trong ROLES_PLAN); không rename |
| Code-splitting làm vỡ routing | Trung bình | Cao | Test từng route sau khi lazy-load; có fallback loading state |
| React Query conflict với existing polling | Thấp | Trung bình | Phase 5 cuối cùng, sau khi tất cả pages đã stable |
| 3 tháng không đủ do underestimation | Trung bình | Cao | Có 6 tuần buffer; cắt Phase 5 nếu cần |

---

## 📊 Metrics Tracking

Sau mỗi phase, đo:

| Metric | Tool | Target |
|--------|------|--------|
| Bundle size | `pnpm build` + check `dist/assets/` | < 250KB initial |
| Test count | `pytest` + `vitest` | Backend 993 → 1000, Frontend 0 → 50+ |
| Type safety | `tsc --noEmit` | No `any` except justified |
| A11y score | Lighthouse | > 90 |
| Lighthouse perf | Lighthouse | > 85 |
| Contrast violations | axe-core | 0 critical |
| Routes lazy-loaded | grep | 16/16 |

---

## 🎓 Khi nào cut features?

Nếu sát deadline, cắt theo thứ tự:

1. **Phase 5 tests** (Vitest + Playwright) — có thể skip, dùng manual test
2. **Phase 4 AuditLogPage** — nice-to-have, có thể ship sau defense
3. **Phase 4 SystemHealthPage** — chỉ admin cần, defer
4. **Phase 2 god component split** — chỉ split nếu còn 2+ tuần
5. **Phase 3/4 visual identity** (role badges, empty states riêng) — cosmetic, defer

**KHÔNG bao giờ cắt**:
- Phase 1 (production blockers)
- Phase 3 backend (foundation cho role)
- Authentication & authorization

---

## ✅ Definition of Done (toàn project)

- [ ] Tất cả 17 Critical findings từ audit report resolved
- [ ] Tất cả 49 High findings resolved hoặc có plan documented
- [ ] 3 roles (user/teacher/admin) hoạt động đúng với phân quyền
- [ ] Backend test pass (993+ → 1000+)
- [ ] Frontend test pass (50+)
- [ ] A11y: Lighthouse score > 90
- [ ] Perf: Lighthouse > 85
- [ ] Bundle < 250KB initial
- [ ] Deploy lên staging, smoke test pass
- [ ] Demo data sẵn (1 admin, 1 teacher, 1 class, 5 students, 10 essays)
- [ ] Demo video 3-5 phút quay trước
- [ ] Slides bảo vệ cập nhật theo UX audit + role system
- [ ] Documentation: CLAUDE.md, README, ARCHITECTURE.md

---

## 📎 Appendix: Effort per File (nếu cần estimate chi tiết)

| File | Phase | Effort | Loại |
|------|-------|--------|------|
| `web/src/api/client.ts` | 1 | 2h | Mở rộng (thêm getAllEssays, deleteEssay, clearCache) |
| `web/src/lib/api.ts` | 1 | 5 min | Xóa |
| `web/src/contexts/AuthContext.tsx` | 1, 3 | 3h | Fix hardcode + extend User type |
| `web/src/components/AppLayout.tsx` | 1, 2, 3 | 12h | A11y + refactor sidebar theo role |
| `web/src/components/CitationGraphView.tsx` | 2, 5 | 10h | A11y + split |
| `web/src/components/CitationDetailDrawer.tsx` | 1, 2 | 4h | Dialog ARIA + focus trap |
| `web/src/pages/EssayPage.tsx` | 5 | 8h | React Query + split |
| `web/src/pages/DashboardPage.tsx` | 1, 2, 5 | 8h | API migration + verified rate + React Query |
| `web/src/pages/HistoryPage.tsx` | 1, 5 | 5h | API migration + full-text search + React Query |
| `web/src/pages/SettingsPage.tsx` | 1 | 4h | API migration + remove reload |
| `web/src/hooks/useRole.ts` | 3 | 3h | Mới |
| `web/src/components/RoleGate.tsx` | 3 | 1h | Mới |
| `src/integrity_checker/db/models.py` | 3 | 4h | Role enum + Class model + migration |
| `src/integrity_checker/api/routes/teacher.py` | 3, 4 | 10h | Mới |
| `src/integrity_checker/api/routes/audit.py` | 4 | 4h | Mới |
| `src/integrity_checker/api/deps.py` | 3 | 2h | require_teacher, require_admin |

---

**Document version**: 1.2
**Last updated**: 2026-10-17
**Next review**: Phase 5 (Polish & Defense Prep)

**Phase 1+2+3+4 status (2026-10-17)**: ✅ ALL DONE
- Phase 1: 11 commits (foundation, a11y, code-splitting, API consolidation)
- Phase 2: 21 commits (polish, contrast, hooks, god component split)
- Phase 3: 15 commits (teacher role, Class model, capability system)
- Phase 4: 19 commits (teacher + admin pages, audit log, system health, e2e tests)
- 1041 backend tests pass, 3/3 E2E teacher-flow pass, build OK
- 1 critical bug + 1 high bug + 3 low bugs caught & fixed in audit
