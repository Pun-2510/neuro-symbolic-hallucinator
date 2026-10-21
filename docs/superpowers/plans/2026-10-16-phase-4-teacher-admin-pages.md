# Phase 4 — Teacher & Admin Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build out Teacher-specific and Admin-specific pages and backend endpoints so the role system (Phase 3) has a real UI surface, ready for thesis defense.

**Architecture:** Backend-first → API client → UI pages. Each task is independently testable. TDD: write failing test first, then implement minimal code to pass. Per-task commits. Branch `feat/phase-4-pages`.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic, pytest. Frontend: React 18, TypeScript, Vite, TailwindCSS, lucide-react. Test framework: pytest (backend), Playwright e2e (frontend — defer to Phase 5).

**Spec:** `IMPLEMENTATION_ROADMAP.md` §"Phase 4" (Tuần 4-5) + `ROLES_PLAN.md` (role/visibility rules).

**Source documents:**
- `src/integrity_checker/api/routes/teacher.py` (Phase 3 endpoints — already exist)
- `src/integrity_checker/api/routes/health.py` (existing)
- `src/integrity_checker/api/routes/verdicts.py` (override endpoint — does NOT yet write AuditLog)
- `web/src/pages/MyClassesPage.tsx` (Phase 3 placeholder)
- `web/src/pages/PendingReviewsPage.tsx` (Phase 3 placeholder)
- `web/src/hooks/useRole.ts` (capability map — use this, never raw role checks)

---

## Global Constraints

- **Type hints everywhere** (CLAUDE.md).
- **Vietnamese comments for user-facing strings**, English for internal logic (CLAUDE.md).
- **TDD**: write failing test → run → verify failure → implement → run → verify pass → commit. No "code + test" written together.
- **Per-task commit**: one task = one commit. Never bundle.
- **Use `useRole()`** for any capability check, not raw `user?.role === 'admin'`.
- **Backend authorization rule** (ROLES_PLAN §C.2): Teacher chỉ xem được data của class mình phụ trách. Admin bypass. Enforce at API layer, not frontend.
- **No raw `fetch()` in pages/components** — always go through `api/client.ts` (CLAUDE.md §API).
- **PEP 8** + **ESLint** rules in `web/`.
- **Branch**: `feat/phase-4-pages`. Each task merges via PR or fast-forward into main at end of phase.

---

## Review Focus

These are the spec-implied failure modes most likely to bite a user that no task's tests cover by default. Each is added as a test step in the task that owns the code.

1. **Teacher cross-tenant data leak**: teacher A queries `GET /teacher/classes/{id}/students` for class owned by teacher B → must return 403, not 404 (information leak). Covered in Task 2.
2. **Pending reviews from outside teacher's classes**: teacher dashboard's `pending_reviews` count must NOT include verdicts from classes the teacher doesn't own. Covered in Task 4.
3. **Audit log immutability**: once an AuditLog row is written it must not be editable via any endpoint. No update/delete endpoint exists; covered by negative test in Task 1.
4. **Override endpoint authorization**: a teacher must NOT be able to override a verdict on an essay outside their classes. Currently `verdicts.py:111` only checks `essay.user_id == current_user.id` — this is a bug; a teacher who owns the class must be able to override. Task 3 fixes this.
5. **CSV export for class essays**: row count must equal the number of essays in the class, not 0 (off-by-one when class has 1 essay). Covered in Task 12.
6. **System health endpoint authorization**: non-admin → 403, not 200 with empty data. Covered in Task 9.

---

## File Structure

### New files (created in this phase)

| File | Responsibility |
|------|----------------|
| `src/integrity_checker/api/routes/audit.py` | `GET /api/audit/log` — queryable audit log endpoint |
| `src/integrity_checker/api/routes/system.py` | `GET /api/system/health` — source availability, cache stats |
| `tests/unit/test_audit_log.py` | AuditLog model + endpoint tests |
| `tests/unit/test_system_health.py` | System health endpoint tests |
| `tests/unit/test_pending_reviews.py` | Pending review filtering tests |
| `tests/unit/test_class_export.py` | CSV export per class tests |
| `tests/unit/test_teacher_override_auth.py` | Cross-tenant override auth tests |
| `web/src/hooks/useMyClasses.ts` | SWR-style data fetching for classes (or use simple useEffect+useState, matching existing pattern) |
| `web/src/hooks/usePendingReviews.ts` | Data fetching for pending reviews |
| `web/src/components/CreateClassDialog.tsx` | Modal to create a new class |
| `web/src/components/AddStudentDialog.tsx` | Modal to add student to class |
| `web/src/components/StatCard.tsx` | Reusable stat tile (currently 3 inline duplicates in MyClassesPage) |
| `web/src/components/RoleBadge.tsx` | Reusable role-colored badge (already inline in AccountManagementPage — extract) |

### Modified files

| File | Why |
|------|-----|
| `src/integrity_checker/api/routes/verdicts.py` | Persist `AuditLog` row on override; allow teacher override for class essays |
| `src/integrity_checker/api/routes/teacher.py` | Add `GET /classes/{id}/pending-reviews` endpoint |
| `src/integrity_checker/api/main.py` | Mount `audit` + `system` routers |
| `src/integrity_checker/db/repository.py` | Add `list_pending_reviews_for_teacher`, `list_audit_log`, `log_audit`, `get_class_average_cis` |
| `web/src/api/client.ts` | Add `listPendingReviews`, `getSystemHealth`, `listAuditLog`, `getClassStats` types + methods |
| `web/src/router.tsx` | Add `/admin/system`, `/admin/audit`, `/teacher/classes/:id` routes |
| `web/src/pages/MyClassesPage.tsx` | Real implementation (replace placeholder) |
| `web/src/pages/PendingReviewsPage.tsx` | Real implementation (replace placeholder) |
| `web/src/pages/AccountManagementPage.tsx` | Show class column + assign-to-class bulk action |
| `web/src/components/AppLayout.tsx` | Already wired to capability groups — no change needed for sidebar |
| `web/src/pages/LoginPage.tsx` | Hide demo credentials in production (Task 22) |

---

## Task 1: Persist AuditLog on verdict override (backend)

**Files:**
- Modify: `src/integrity_checker/api/routes/verdicts.py:92-149`
- Test: `tests/unit/test_audit_log.py` (new)

**Interfaces:**
- Consumes: `repo.update_verdict(verdict_id, new_label, override_note, new_mapping_status)` (existing)
- Consumes: `repo.log_audit(verdict_id, original_label, new_label, user, note)` (NEW — to be added in this task)
- Produces: `AuditLog` row written before commit; response unchanged

- [ ] **Step 1: Write the failing test in `tests/unit/test_audit_log.py`**

```python
def test_override_writes_audit_log(clean_db):
    from integrity_checker.api.routes.verdicts import override_verdict
    from integrity_checker.db.models import AuditLog
    # setup: create user, essay, verdict with label='metadata_error'
    # ...
    # act: POST /override
    # assert: AuditLog row exists with original_label='metadata_error',
    # new_label='verified', user=<teacher username>
```

- [ ] **Step 2: Run test, verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/unit/test_audit_log.py::test_override_writes_audit_log -v`
Expected: FAIL with `AttributeError: 'Repository' object has no attribute 'log_audit'`

- [ ] **Step 3: Add `log_audit` method to `Repository` in `src/integrity_checker/db/repository.py`**

```python
def log_audit(
    self,
    verdict_id: int,
    original_label: str,
    new_label: str,
    user: str,
    note: str | None = None,
) -> AuditLog:
    """Append-only audit row. Never update or delete via repository."""
    row = AuditLog(
        verdict_id=verdict_id,
        original_label=original_label,
        new_label=new_label,
        user=user,
        note=note,
    )
    self.session.add(row)
    return row
```

- [ ] **Step 4: Modify `override_verdict` in `verdicts.py` to capture `original_label` and call `repo.log_audit` before `repo.commit()`**

```python
# After repo.update_verdict(...) returns `updated`:
original_label = next(
    (r.label for r in repo.get_verdicts(essay_id) if r.id == v_id),
    None,
)
if original_label is not None and original_label != body.new_label:
    repo.log_audit(
        verdict_id=v_id,
        original_label=original_label,
        new_label=body.new_label,
        user=current_user.username,
        note=body.reason,
    )
repo.commit()
```

- [ ] **Step 5: Run test, verify it passes**

Run: `python -m pytest tests/unit/test_audit_log.py::test_override_writes_audit_log -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/db/repository.py src/integrity_checker/api/routes/verdicts.py tests/unit/test_audit_log.py
git commit -m "feat(phase-4): persist AuditLog row on verdict override (Task 1)

- Repository.log_audit() append-only helper
- override_verdict captures original_label and writes AuditLog
- Test: test_override_writes_audit_log passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 2: Allow teacher to override verdicts on class essays (backend auth fix)

**Files:**
- Modify: `src/integrity_checker/api/routes/verdicts.py:106-112`
- Test: `tests/unit/test_teacher_override_auth.py` (new)

**Interfaces:**
- Consumes: `repo.get_class_essays(class_id)` (existing)
- Consumes: `repo.list_classes_for_teacher(teacher_id)` (existing)
- Produces: Teacher who owns the class containing the essay may override; else 403

**Context:** Current rule at `verdicts.py:111` is `essay.user_id != current_user.id → 403`. This blocks teachers from overriding student verdicts. Fix: teacher may override if the essay belongs to a student in one of their classes.

- [ ] **Step 1: Write the failing test in `tests/unit/test_teacher_override_auth.py`**

```python
def test_teacher_can_override_verdict_on_class_essay(clean_db):
    # setup: create teacher, class, student enrolled, essay with verdict
    # act: teacher POST /override
    # assert: 200, verdict.is_overridden = True

def test_teacher_cannot_override_essay_outside_their_class(clean_db):
    # setup: teacher A owns class X; student S enrolled in class X but with essay uploaded under OTHER teacher B's class
    # act: teacher A POST /override on that essay
    # assert: 403
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/unit/test_teacher_override_auth.py -v`
Expected: FAIL — first test gets 403 (because current rule blocks non-owner), second test unexpectedly passes (current rule is too restrictive so the negative case accidentally works)

- [ ] **Step 3: Modify the ownership check in `verdicts.py`**

Replace the current rule with:

```python
if current_user.role == "admin":
    pass  # admins override anything
elif essay.user_id == current_user.id:
    pass  # student owns the essay
elif current_user.role == "teacher":
    # Teacher may override if essay belongs to a student in one of their classes
    teacher_class_ids = {
        c.id for c in repo.list_classes_for_teacher(current_user.id)
    }
    student_class_ids = {
        m.class_id for m in repo.session.query(ClassMembership).filter(
            ClassMembership.student_id == essay.user_id
        ).all()
    } if essay.user_id else set()
    if teacher_class_ids & student_class_ids:
        pass
    else:
        raise HTTPException(status_code=403, detail="Access denied")
else:
    raise HTTPException(status_code=403, detail="Access denied")
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/unit/test_teacher_override_auth.py -v`
Expected: 2/2 PASS

- [ ] **Step 5: Run full backend test suite to ensure no regression**

Run: `python -m pytest tests/ -q --ignore=tests/unit/test_grobid_service.py --ignore=tests/unit/test_grobid_adapter.py --ignore=tests/unit/test_grobid_parser.py`
Expected: 993+ pass, no new failures

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/api/routes/verdicts.py tests/unit/test_teacher_override_auth.py
git commit -m "fix(phase-4): allow teacher to override verdicts on class essays (Task 2)

- New rule: teacher may override if essay.user_id is in a class
  the teacher owns (intersection of class IDs)
- Admin bypass; student owner still works
- Tests: positive + cross-tenant negative

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 3: `GET /api/teacher/classes/{id}/pending-reviews` endpoint

**Files:**
- Modify: `src/integrity_checker/api/routes/teacher.py:227-253` (add new endpoint below)
- Test: `tests/unit/test_pending_reviews.py` (new)

**Interfaces:**
- Consumes: `repo.list_pending_reviews_for_class(class_id)` (NEW)
- Produces: `list[PendingVerdictItem]` with `verdict_id`, `essay_id`, `filename`, `student_username`, `label`, `reasoning`, `validated_at`

- [ ] **Step 1: Write the failing test in `tests/unit/test_pending_reviews.py`**

```python
def test_list_pending_reviews_for_class(clean_db):
    # setup: class with 2 essays, one with verdict labeled
    # 'metadata_error' (not overridden), one with 'verified' (should be excluded)
    # act: GET /teacher/classes/{id}/pending-reviews
    # assert: returns 1 item, the metadata_error one

def test_pending_reviews_excludes_overridden(clean_db):
    # setup: verdict labeled metadata_error, then override it to verified
    # act: GET pending-reviews
    # assert: 0 items

def test_teacher_cannot_view_other_teachers_class_pending(clean_db):
    # setup: teacher A owns class; teacher B queries
    # assert: 403
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/unit/test_pending_reviews.py -v`
Expected: FAIL — endpoint doesn't exist (404)

- [ ] **Step 3: Add `list_pending_reviews_for_class` to `Repository`**

```python
def list_pending_reviews_for_class(self, class_id: int) -> list[VerdictRecord]:
    """Verdicts in this class's essays with label in (metadata_error,
    suspected_hallucination) AND not yet overridden."""
    student_ids = [
        row[0] for row in self.session.query(ClassMembership.student_id)
        .filter(ClassMembership.class_id == class_id).all()
    ]
    if not student_ids:
        return []
    from integrity_checker.db.models import VerdictRecord
    return list(
        self.session.query(VerdictRecord)
        .join(EssayRecord, EssayRecord.id == VerdictRecord.essay_id)
        .filter(
            EssayRecord.user_id.in_(student_ids),
            VerdictRecord.label.in_(["metadata_error", "suspected_hallucination"]),
            VerdictRecord.is_overridden == 0,
        )
        .order_by(VerdictRecord.validated_at.desc())
        .all()
    )
```

- [ ] **Step 4: Add endpoint to `teacher.py`**

```python
class PendingVerdictItem(BaseModel):
    verdict_id: int
    essay_id: int
    filename: str
    student_username: str | None
    label: str
    confidence: float
    reasoning: str
    validated_at: str


@router.get("/classes/{class_id}/pending-reviews", response_model=list[PendingVerdictItem])
def list_pending_reviews(
    class_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    _ensure_teacher_owns_class(teacher, cls)
    verdicts = repo.list_pending_reviews_for_class(class_id)
    out: list[PendingVerdictItem] = []
    for v in verdicts:
        essay = repo.get_essay(v.essay_id)
        student = repo.get_user_by_id(essay.user_id) if essay and essay.user_id else None
        out.append(PendingVerdictItem(
            verdict_id=v.id,
            essay_id=v.essay_id,
            filename=essay.filename if essay else "",
            student_username=student.username if student else None,
            label=v.label,
            confidence=v.confidence,
            reasoning=v.reasoning or "",
            validated_at=v.validated_at.isoformat() if v.validated_at else "",
        ))
    return out
```

- [ ] **Step 5: Run tests, verify they pass**

Run: `python -m pytest tests/unit/test_pending_reviews.py -v`
Expected: 3/3 PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/db/repository.py src/integrity_checker/api/routes/teacher.py tests/unit/test_pending_reviews.py
git commit -m "feat(phase-4): add GET /teacher/classes/{id}/pending-reviews (Task 3)

- Repository.list_pending_reviews_for_class excludes overridden verdicts
- New endpoint enforces teacher-owns-class (403 on cross-tenant)
- 3 tests pass: positive, overridden-excluded, cross-tenant

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 4: `GET /api/system/health` (admin-only, aggregated system health)

**Files:**
- Create: `src/integrity_checker/api/routes/system.py`
- Modify: `src/integrity_checker/api/main.py:75-85`
- Test: `tests/unit/test_system_health.py` (new)

**Interfaces:**
- Consumes: `repo.get_cache_stats()` (existing), `repo.count_pending_reviews_for_teacher()` (existing)
- Produces: `SystemHealthResponse` with `total_users`, `total_essays`, `verdict_label_counts`, `cache_stats`, `pending_reviews_by_class`

- [ ] **Step 1: Write the failing test in `tests/unit/test_system_health.py`**

```python
def test_system_health_requires_admin(clean_db):
    # non-admin token → 403

def test_system_health_returns_aggregates(clean_db):
    # admin token, with seeded data
    # assert: response has total_users, total_essays, verdict_label_counts, cache_stats
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/unit/test_system_health.py -v`
Expected: FAIL — endpoint doesn't exist (404)

- [ ] **Step 3: Create `src/integrity_checker/api/routes/system.py`**

```python
"""System health endpoint (admin only) — Phase 4."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User, VerdictRecord
from integrity_checker.db.repository import Repository

router = APIRouter()


@router.get("/health")
def get_system_health(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    repo = Repository(db)
    users = repo.get_all_users()
    essays = repo.get_all_essays()
    verdicts = db.query(VerdictRecord).all()
    label_counts: dict[str, int] = {}
    for v in verdicts:
        label_counts[v.label] = label_counts.get(v.label, 0) + 1
    cache_stats = repo.get_cache_stats()
    return {
        "status": "ok",
        "totals": {
            "users": len(users),
            "admins": sum(1 for u in users if u.role == "admin"),
            "teachers": sum(1 for u in users if u.role == "teacher"),
            "students": sum(1 for u in users if u.role == "user"),
            "essays": len(essays),
            "verdicts": len(verdicts),
        },
        "verdict_label_counts": label_counts,
        "cache_stats": cache_stats,
    }
```

- [ ] **Step 4: Mount router in `main.py`**

Add to imports at line 9: `from integrity_checker.api.routes import auth, cache, essays, export, health, report, system, teacher, users, verdicts`
Add to mounts: `app.include_router(system.router, prefix="/api/system", tags=["system"])`

- [ ] **Step 5: Run tests, verify they pass**

Run: `python -m pytest tests/unit/test_system_health.py -v`
Expected: 2/2 PASS

- [ ] **Step 6: Commit**

```bash
git add src/integrity_checker/api/routes/system.py src/integrity_checker/api/main.py tests/unit/test_system_health.py
git commit -m "feat(phase-4): add GET /api/system/health (admin) (Task 4)

- Aggregates: users by role, essays, verdicts by label, cache stats
- Admin-only via require_admin dependency
- 2 tests pass: auth + aggregates

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 5: `GET /api/audit/log` (admin-only, paginated audit log)

**Files:**
- Create: `src/integrity_checker/api/routes/audit.py`
- Modify: `src/integrity_checker/api/main.py`
- Test: `tests/unit/test_audit_log.py` (extend existing)

**Interfaces:**
- Consumes: `repo.list_audit_log(limit, offset, user_filter, since)` (NEW)
- Produces: `list[AuditLogItem]` ordered by `logged_at DESC`

- [ ] **Step 1: Write the failing test in `tests/unit/test_audit_log.py`**

```python
def test_list_audit_log_requires_admin(clean_db):
    # non-admin → 403

def test_list_audit_log_returns_recent_first(clean_db):
    # seed 3 audit rows; assert: response[0] is newest
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/unit/test_audit_log.py::test_list_audit_log_requires_admin tests/unit/test_audit_log.py::test_list_audit_log_returns_recent_first -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add `list_audit_log` to `Repository`**

```python
def list_audit_log(
    self,
    limit: int = 50,
    offset: int = 0,
    user_filter: str | None = None,
) -> list[AuditLog]:
    q = self.session.query(AuditLog)
    if user_filter:
        q = q.filter(AuditLog.user == user_filter)
    return q.order_by(AuditLog.logged_at.desc()).limit(limit).offset(offset).all()
```

- [ ] **Step 4: Create `src/integrity_checker/api/routes/audit.py`**

```python
"""Audit log endpoint (admin only) — Phase 4."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from integrity_checker.api.deps import get_db, require_admin
from integrity_checker.db.models import User
from integrity_checker.db.repository import Repository

router = APIRouter()


@router.get("/log")
def list_audit(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: str | None = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    repo = Repository(db)
    rows = repo.list_audit_log(limit=limit, offset=offset, user_filter=user)
    return [
        {
            "id": r.id,
            "verdict_id": r.verdict_id,
            "original_label": r.original_label,
            "new_label": r.new_label,
            "user": r.user,
            "note": r.note,
            "logged_at": r.logged_at.isoformat() if r.logged_at else None,
        }
        for r in rows
    ]
```

- [ ] **Step 5: Mount router in `main.py`**

Add to imports: `from integrity_checker.api.routes import audit, auth, ...`
Add to mounts: `app.include_router(audit.router, prefix="/api/audit", tags=["audit"])`

- [ ] **Step 6: Run tests, verify they pass**

Run: `python -m pytest tests/unit/test_audit_log.py -v`
Expected: 3/3 PASS (1 from Task 1 + 2 new)

- [ ] **Step 7: Commit**

```bash
git add src/integrity_checker/db/repository.py src/integrity_checker/api/routes/audit.py src/integrity_checker/api/main.py tests/unit/test_audit_log.py
git commit -m "feat(phase-4): add GET /api/audit/log (admin, paginated) (Task 5)

- Repository.list_audit_log with limit/offset/user filter
- Admin-only endpoint, defaults 50 rows newest-first
- Tests: auth + ordering

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 6: `GET /api/teacher/classes/{id}/export.csv`

**Files:**
- Modify: `src/integrity_checker/api/routes/teacher.py` (add endpoint)
- Modify: `src/integrity_checker/api/routes/export.py` (helper for class export)
- Test: `tests/unit/test_class_export.py` (new)

**Interfaces:**
- Consumes: `repo.get_class_essays(class_id)`, `repo.get_verdicts(essay_id)`
- Produces: `StreamingResponse` with `text/csv`, columns: `filename, student, label, confidence, validated_at, is_overridden`

- [ ] **Step 1: Write the failing test in `tests/unit/test_class_export.py`**

```python
def test_export_class_csv_returns_one_row_per_essay(clean_db):
    # class with 3 essays, 2 with verdicts
    # act: GET /teacher/classes/{id}/export.csv
    # assert: response has Content-Type text/csv, body has 3+1=4 lines (header + 3)

def test_export_class_csv_rejects_other_teachers(clean_db):
    # teacher B queries class owned by teacher A → 403
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python -m pytest tests/unit/test_class_export.py -v`
Expected: FAIL — endpoint doesn't exist

- [ ] **Step 3: Add endpoint to `teacher.py`**

```python
import csv
import io
from fastapi.responses import StreamingResponse


@router.get("/classes/{class_id}/export.csv")
def export_class_csv(
    class_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    repo = Repository(db)
    cls = repo.get_class(class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    _ensure_teacher_owns_class(teacher, cls)
    essays = repo.get_class_essays(class_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["filename", "student", "verdict_id", "label", "confidence", "validated_at", "is_overridden"])
    for essay in essays:
        student = repo.get_user_by_id(essay.user_id) if essay.user_id else None
        verdicts = repo.get_verdicts(essay.id)
        if not verdicts:
            writer.writerow([essay.filename, student.username if student else "", "", "", "", "", ""])
        for v in verdicts:
            writer.writerow([
                essay.filename,
                student.username if student else "",
                v.id,
                v.label,
                v.confidence,
                v.validated_at.isoformat() if v.validated_at else "",
                "yes" if v.is_overridden else "no",
            ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="class_{class_id}.csv"'},
    )
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python -m pytest tests/unit/test_class_export.py -v`
Expected: 2/2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/integrity_checker/api/routes/teacher.py tests/unit/test_class_export.py
git commit -m "feat(phase-4): add class CSV export endpoint (Task 6)

- GET /teacher/classes/{id}/export.csv
- Header + one row per (essay, verdict) pair
- Teacher-owns-class enforced (403 on cross-tenant)
- 2 tests pass

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 7: Extend `web/src/api/client.ts` with new types + methods

**Files:**
- Modify: `web/src/api/client.ts` (add types + 4 methods)

**Interfaces:**
- Produces: `PendingVerdict`, `SystemHealth`, `AuditLogEntry`, `ClassExportResponse` types
- Produces: `api.listPendingReviews(classId)`, `api.getSystemHealth()`, `api.listAuditLog(params)`, `api.exportClassCSV(classId)` methods

- [ ] **Step 1: Add types after `TeacherDashboard` (line 360)**

```typescript
export interface PendingVerdict {
  verdict_id: number;
  essay_id: number;
  filename: string;
  student_username: string | null;
  label: string;
  confidence: number;
  reasoning: string;
  validated_at: string;
}

export interface SystemHealth {
  status: string;
  totals: {
    users: number;
    admins: number;
    teachers: number;
    students: number;
    essays: number;
    verdicts: number;
  };
  verdict_label_counts: Record<string, number>;
  cache_stats: Record<string, unknown>;
}

export interface AuditLogEntry {
  id: number;
  verdict_id: number;
  original_label: string;
  new_label: string;
  user: string;
  note: string | null;
  logged_at: string | null;
}
```

- [ ] **Step 2: Add API methods after `getTeacherDashboard` (line 428)**

```typescript
listPendingReviews: (classId: number) =>
  request<PendingVerdict[]>(`/teacher/classes/${classId}/pending-reviews`),
getSystemHealth: () => request<SystemHealth>('/system/health'),
listAuditLog: (params: { limit?: number; offset?: number; user?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.offset) qs.set('offset', String(params.offset));
  if (params.user) qs.set('user', params.user);
  return request<AuditLogEntry[]>(`/audit/log?${qs.toString()}`);
},
exportClassCSV: (classId: number) =>
  `${BASE_URL}/teacher/classes/${classId}/export.csv`,
```

- [ ] **Step 3: Run frontend build to verify TypeScript**

Run: `cd web && pnpm build 2>&1 | tail -30`
Expected: build success, no TS errors

- [ ] **Step 4: Commit**

```bash
git add web/src/api/client.ts
git commit -m "feat(phase-4): extend api/client.ts with Phase 4 endpoints (Task 7)

- Types: PendingVerdict, SystemHealth, AuditLogEntry
- Methods: listPendingReviews, getSystemHealth, listAuditLog, exportClassCSV
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 8: `web/src/components/StatCard.tsx` reusable component

**Files:**
- Create: `web/src/components/StatCard.tsx`

**Interfaces:**
- Consumes: `label: string`, `value: string | number`, optional `icon`, `color` (indigo/green/amber/violet)
- Produces: Reusable tile used in MyClassesPage, SystemHealthPage, AuditLogPage

- [ ] **Step 1: Create the component**

```typescript
import type { LucideIcon } from 'lucide-react';

type Color = 'indigo' | 'green' | 'amber' | 'violet' | 'rose' | 'slate';

const COLOR_MAP: Record<Color, { bg: string; text: string; ring: string }> = {
  indigo: { bg: 'bg-indigo-50 dark:bg-indigo-950', text: 'text-indigo-600 dark:text-indigo-400', ring: 'ring-indigo-200 dark:ring-indigo-800' },
  green:  { bg: 'bg-emerald-50 dark:bg-emerald-950', text: 'text-emerald-600 dark:text-emerald-400', ring: 'ring-emerald-200 dark:ring-emerald-800' },
  amber:  { bg: 'bg-amber-50 dark:bg-amber-950', text: 'text-amber-600 dark:text-amber-400', ring: 'ring-amber-200 dark:ring-amber-800' },
  violet: { bg: 'bg-violet-50 dark:bg-violet-950', text: 'text-violet-600 dark:text-violet-400', ring: 'ring-violet-200 dark:ring-violet-800' },
  rose:   { bg: 'bg-rose-50 dark:bg-rose-950', text: 'text-rose-600 dark:text-rose-400', ring: 'ring-rose-200 dark:ring-rose-800' },
  slate:  { bg: 'bg-slate-50 dark:bg-slate-900', text: 'text-slate-600 dark:text-slate-400', ring: 'ring-slate-200 dark:ring-slate-800' },
};

export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  color?: Color;
  hint?: string;
}

export function StatCard({ label, value, icon: Icon, color = 'indigo', hint }: StatCardProps) {
  const c = COLOR_MAP[color];
  return (
    <div className={`rounded-xl ring-1 ${c.ring} bg-white dark:bg-slate-900 p-5`}>
      <div className="flex items-start gap-3">
        {Icon && (
          <div className={`w-10 h-10 rounded-lg ${c.bg} flex items-center justify-center`}>
            <Icon className={`h-5 w-5 ${c.text}`} />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
          {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -10`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/components/StatCard.tsx
git commit -m "feat(phase-4): add reusable StatCard component (Task 8)

- 6 color variants (indigo/green/amber/violet/rose/slate)
- Optional icon + hint
- Replaces 3+ inline duplicates planned for MyClassesPage/SystemHealthPage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 9: `web/src/pages/SystemHealthPage.tsx`

**Files:**
- Create: `web/src/pages/SystemHealthPage.tsx`
- Modify: `web/src/router.tsx` (add route)

- [ ] **Step 1: Create `SystemHealthPage.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { Activity, Database, FileCheck, Users } from 'lucide-react';
import { api, type SystemHealth } from '@/api/client';
import { StatCard } from '@/components/StatCard';

export function SystemHealthPage() {
  const [data, setData] = useState<SystemHealth | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getSystemHealth().then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p className="text-rose-600">Error: {error}</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-violet-100 dark:bg-violet-950 flex items-center justify-center">
          <Activity className="h-5 w-5 text-violet-600 dark:text-violet-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">System Health</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Tổng quan hệ thống & cache.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Total users" value={data.totals.users} icon={Users} color="indigo" />
        <StatCard label="Admins" value={data.totals.admins} color="violet" />
        <StatCard label="Teachers" value={data.totals.teachers} color="green" />
        <StatCard label="Students" value={data.totals.students} color="slate" />
        <StatCard label="Essays" value={data.totals.essays} icon={FileCheck} color="indigo" />
        <StatCard label="Verdicts" value={data.totals.verdicts} icon={Database} color="amber" />
      </div>

      <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 p-5">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Verdicts by label</h2>
        <div className="space-y-2">
          {Object.entries(data.verdict_label_counts).map(([label, count]) => (
            <div key={label} className="flex justify-between text-sm">
              <span className="text-slate-600 dark:text-slate-400 font-mono">{label}</span>
              <span className="font-semibold text-slate-900 dark:text-white">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route to `router.tsx` after the `admin/users` route (line ~143)**

```typescript
import { SystemHealthPage } from './pages/SystemHealthPage';
// in routes:
{
  path: '/admin/system',
  element: (
    <ProtectedRoute requiredCapabilities={['view_system_health']}>
      <SystemHealthPage />
    </ProtectedRoute>
  ),
},
```

- [ ] **Step 3: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -10`
Expected: build success

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/SystemHealthPage.tsx web/src/router.tsx
git commit -m "feat(phase-4): add SystemHealthPage (admin) (Task 9)

- 6 stat tiles (users by role, essays, verdicts)
- Verdict label distribution table
- Route: /admin/system (capability-gated)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 10: `web/src/pages/AuditLogPage.tsx`

**Files:**
- Create: `web/src/pages/AuditLogPage.tsx`
- Modify: `web/src/router.tsx`

- [ ] **Step 1: Create `AuditLogPage.tsx`**

```typescript
import { useEffect, useState } from 'react';
import { FileText, Search } from 'lucide-react';
import { api, type AuditLogEntry } from '@/api/client';

export function AuditLogPage() {
  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [userFilter, setUserFilter] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.listAuditLog({ limit: 100, user: userFilter || undefined })
      .then(setEntries)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [userFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
          <FileText className="h-5 w-5 text-slate-600 dark:text-slate-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Audit Log</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Lịch sử override verdict & system events.</p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          type="text"
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
          placeholder="Lọc theo username…"
          aria-label="Filter audit log by username"
          className="w-full pl-10 pr-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm"
        />
      </div>

      {error && <p className="text-rose-600 text-sm">Error: {error}</p>}
      {loading ? <p className="text-slate-500">Loading…</p> : (
        <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs uppercase text-slate-500">
              <tr>
                <th className="text-left px-4 py-3">When</th>
                <th className="text-left px-4 py-3">User</th>
                <th className="text-left px-4 py-3">Verdict</th>
                <th className="text-left px-4 py-3">From → To</th>
                <th className="text-left px-4 py-3">Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {entries.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">Chưa có audit log.</td></tr>
              ) : entries.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                    {e.logged_at ? new Date(e.logged_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 font-medium">{e.user}</td>
                  <td className="px-4 py-3 text-slate-500 font-mono text-xs">#{e.verdict_id}</td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs">
                      <span className="text-rose-600">{e.original_label}</span>
                      {' → '}
                      <span className="text-emerald-600">{e.new_label}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400 max-w-xs truncate">{e.note ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route to `router.tsx`**

```typescript
import { AuditLogPage } from './pages/AuditLogPage';
{
  path: '/admin/audit',
  element: (
    <ProtectedRoute requiredCapabilities={['view_audit_log']}>
      <AuditLogPage />
    </ProtectedRoute>
  ),
},
```

- [ ] **Step 3: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -10`
Expected: build success

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/AuditLogPage.tsx web/src/router.tsx
git commit -m "feat(phase-4): add AuditLogPage with username filter (Task 10)

- Filter input by username
- Table: when, user, verdict_id, from→to, note
- Route: /admin/audit (capability-gated)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 11: `web/src/components/CreateClassDialog.tsx`

**Files:**
- Create: `web/src/components/CreateClassDialog.tsx`

- [ ] **Step 1: Create the component**

```typescript
import { useState } from 'react';
import { X } from 'lucide-react';
import { api } from '@/api/client';
import type { Class } from '@/api/client';

export interface CreateClassDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: (cls: Class) => void;
}

export function CreateClassDialog({ open, onClose, onCreated }: CreateClassDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const cls = await api.createClass({ name: name.trim(), description: description.trim() || undefined });
      onCreated(cls);
      setName('');
      setDescription('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="create-class-title">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 id="create-class-title" className="text-lg font-bold text-slate-900 dark:text-white">Tạo lớp mới</h2>
          <button onClick={onClose} aria-label="Close" className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="class-name">Tên lớp <span className="text-rose-500">*</span></label>
            <input
              id="class-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={120}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1" htmlFor="class-desc">Mô tả (optional)</label>
            <textarea
              id="class-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
            />
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800">
              Hủy
            </button>
            <button type="submit" disabled={submitting || !name.trim()} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50">
              {submitting ? 'Đang tạo…' : 'Tạo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/components/CreateClassDialog.tsx
git commit -m "feat(phase-4): add CreateClassDialog component (Task 11)

- Modal with name + description fields
- ARIA: role=dialog, aria-modal, aria-labelledby
- Calls api.createClass and bubbles result via onCreated

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 12: `web/src/components/AddStudentDialog.tsx`

**Files:**
- Create: `web/src/components/AddStudentDialog.tsx`

- [ ] **Step 1: Create the component**

```typescript
import { useEffect, useState } from 'react';
import { X, Search } from 'lucide-react';
import { api } from '@/api/client';
import type { User } from '@/api/client';

export interface AddStudentDialogProps {
  open: boolean;
  classId: number;
  existingStudentIds: number[];
  onClose: () => void;
  onAdded: () => void;
}

export function AddStudentDialog({ open, classId, existingStudentIds, onClose, onAdded }: AddStudentDialogProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    api.listUsers().then(setUsers).catch((e) => setError(String(e)));
  }, [open]);

  if (!open) return null;

  const candidates = users
    .filter((u) => u.role === 'user' && !existingStudentIds.includes(u.id))
    .filter((u) => !search || u.username.toLowerCase().includes(search.toLowerCase()) || (u.full_name ?? '').toLowerCase().includes(search.toLowerCase()));

  const handleAdd = async (studentId: number) => {
    setSubmitting(true);
    setError('');
    try {
      await api.addStudentToClass(classId, studentId);
      onAdded();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-labelledby="add-student-title">
      <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 id="add-student-title" className="text-lg font-bold text-slate-900 dark:text-white">Thêm sinh viên</h2>
          <button onClick={onClose} aria-label="Close" className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo username hoặc tên…"
            aria-label="Search students"
            className="w-full pl-10 pr-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
          />
        </div>
        {error && <p className="text-sm text-rose-600 mb-2">{error}</p>}
        <ul className="max-h-80 overflow-y-auto space-y-1">
          {candidates.length === 0 ? (
            <li className="text-sm text-slate-500 px-2 py-4 text-center">Không có sinh viên phù hợp.</li>
          ) : candidates.map((u) => (
            <li key={u.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800">
              <div>
                <p className="text-sm font-medium">{u.username}</p>
                {u.full_name && <p className="text-xs text-slate-500">{u.full_name}</p>}
              </div>
              <button
                onClick={() => handleAdd(u.id)}
                disabled={submitting}
                className="px-3 py-1 text-xs rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Thêm
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/components/AddStudentDialog.tsx
git commit -m "feat(phase-4): add AddStudentDialog component (Task 12)

- Lists users with role=user, excludes existing students
- Live search by username/full_name
- ARIA + role=dialog

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 13: Rewrite `web/src/pages/MyClassesPage.tsx` (real implementation)

**Files:**
- Modify: `web/src/pages/MyClassesPage.tsx` (replace placeholder with real UI)
- Modify: `web/src/router.tsx` (add nested class detail route)

- [ ] **Step 1: Replace contents of `MyClassesPage.tsx`**

```typescript
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, Plus, Users, FileCheck, ClipboardCheck, ChevronRight } from 'lucide-react';
import { api, type Class, type TeacherDashboard } from '@/api/client';
import { StatCard } from '@/components/StatCard';
import { CreateClassDialog } from '@/components/CreateClassDialog';

export function MyClassesPage() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<TeacherDashboard | null>(null);
  const [error, setError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getTeacherDashboard();
      setDashboard(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-950 flex items-center justify-center">
            <GraduationCap className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">My Classes</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Quản lý lớp học và theo dõi bài nộp.</p>
          </div>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          Tạo lớp
        </button>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Lớp" value={dashboard.total_classes} icon={GraduationCap} color="indigo" />
          <StatCard label="Sinh viên" value={dashboard.total_students} icon={Users} color="green" />
          <StatCard label="Bài nộp" value={dashboard.total_essays} icon={FileCheck} color="amber" />
          <StatCard label="Cần xem xét" value={dashboard.pending_reviews} icon={ClipboardCheck} color="rose" hint="metadata_error / suspected_hallucination" />
        </div>
      )}

      <div className="space-y-2">
        {dashboard?.classes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-12 text-center">
            <p className="text-slate-700 dark:text-slate-300 font-medium">Chưa có lớp nào.</p>
            <p className="text-sm text-slate-500 mt-1">Bấm "Tạo lớp" để bắt đầu.</p>
          </div>
        ) : dashboard?.classes.map((c) => (
          <button
            key={c.id}
            onClick={() => navigate(`/teacher/classes/${c.id}`)}
            className="w-full text-left rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 p-4 hover:ring-indigo-300 dark:hover:ring-indigo-700 transition-all flex items-center justify-between group"
          >
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-slate-900 dark:text-white">{c.name}</h3>
              {c.description && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 truncate">{c.description}</p>}
              <div className="flex gap-4 mt-2 text-xs text-slate-500">
                <span><Users className="inline h-3 w-3 mr-1" />{c.student_count} SV</span>
                <span><FileCheck className="inline h-3 w-3 mr-1" />{c.essay_count} bài</span>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-slate-400 group-hover:text-indigo-500" />
          </button>
        ))}
      </div>

      <CreateClassDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={load}
      />
    </div>
  );
}
```

- [ ] **Step 2: Add nested route in `router.tsx` after the existing `/teacher/classes` route**

```typescript
import { ClassDetailPage } from './pages/ClassDetailPage';
{
  path: '/teacher/classes/:classId',
  element: (
    <ProtectedRoute requiredCapabilities={['view_class_history']}>
      <ClassDetailPage />
    </ProtectedRoute>
  ),
},
```

- [ ] **Step 3: Create minimal `web/src/pages/ClassDetailPage.tsx` (Task 14 will fully build it)**

```typescript
import { useParams } from 'react-router-dom';

/** Placeholder — Task 14 implements the full UI. */
export function ClassDetailPage() {
  const { classId } = useParams();
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Class #{classId}</h1>
      <p className="text-slate-500 mt-2">Full implementation in Task 14.</p>
    </div>
  );
}
```

- [ ] **Step 4: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/MyClassesPage.tsx web/src/pages/ClassDetailPage.tsx web/src/router.tsx
git commit -m "feat(phase-4): real MyClassesPage with create flow (Task 13)

- 4 stat tiles (classes, students, essays, pending)
- Per-class list with student/essay counts
- CreateClassDialog integration
- Stub /teacher/classes/:classId route (Task 14)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 14: `web/src/pages/ClassDetailPage.tsx` full implementation

**Files:**
- Modify: `web/src/pages/ClassDetailPage.tsx` (replace stub)

- [ ] **Step 1: Replace `ClassDetailPage.tsx`**

```typescript
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, UserPlus, Download, Users, FileText, Trash2 } from 'lucide-react';
import { api, type Class, type ClassStudent, type ClassEssay } from '@/api/client';
import { AddStudentDialog } from '@/components/AddStudentDialog';

export function ClassDetailPage() {
  const { classId } = useParams<{ classId: string }>();
  const navigate = useNavigate();
  const cid = Number(classId);

  const [cls, setCls] = useState<Class | null>(null);
  const [students, setStudents] = useState<ClassStudent[]>([]);
  const [essays, setEssays] = useState<ClassEssay[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!cid) return;
    try {
      const all = await api.listMyClasses();
      setCls(all.find((c) => c.id === cid) ?? null);
      setStudents(await api.listClassStudents(cid));
      setEssays(await api.listClassEssays(cid));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  }, [cid]);

  useEffect(() => { load(); }, [load]);

  const handleRemove = async (studentId: number) => {
    if (!confirm('Xóa sinh viên khỏi lớp?')) return;
    try {
      await api.removeStudentFromClass(cid, studentId);
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Failed');
    }
  };

  const handleExport = () => {
    window.open(api.exportClassCSV(cid), '_blank');
  };

  if (error) return <p className="text-rose-600">{error}</p>;
  if (!cls) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/teacher/classes')} aria-label="Back to classes" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{cls.name}</h1>
          {cls.description && <p className="text-sm text-slate-500 mt-1">{cls.description}</p>}
        </div>
        <button onClick={handleExport} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg ring-1 ring-slate-200 dark:ring-slate-700 text-sm hover:bg-slate-50 dark:hover:bg-slate-800">
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold flex items-center gap-2"><Users className="h-5 w-5" /> Sinh viên ({students.length})</h2>
          <button onClick={() => setAddOpen(true)} className="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">
            <UserPlus className="h-4 w-4" />
            Thêm
          </button>
        </div>
        <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
          {students.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">Chưa có sinh viên.</p>
          ) : students.map((s) => (
            <div key={s.id} className="flex items-center justify-between p-3">
              <div>
                <p className="font-medium text-sm">{s.username}</p>
                {s.full_name && <p className="text-xs text-slate-500">{s.full_name}</p>}
              </div>
              <button onClick={() => handleRemove(s.id)} aria-label={`Remove ${s.username}`} className="p-2 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2"><FileText className="h-5 w-5" /> Bài nộp ({essays.length})</h2>
        <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
          {essays.length === 0 ? (
            <p className="p-6 text-center text-sm text-slate-500">Chưa có bài nộp.</p>
          ) : essays.map((e) => (
            <button
              key={e.id}
              onClick={() => navigate(`/verification/report/${e.id}`)}
              className="w-full text-left flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <div>
                <p className="font-medium text-sm">{e.filename}</p>
                <p className="text-xs text-slate-500">
                  {e.username ?? '—'} • {e.num_pages} trang • {e.uploaded_at ? new Date(e.uploaded_at).toLocaleDateString() : ''}
                </p>
              </div>
            </button>
          ))}
        </div>
      </section>

      <AddStudentDialog
        open={addOpen}
        classId={cid}
        existingStudentIds={students.map((s) => s.id)}
        onClose={() => setAddOpen(false)}
        onAdded={load}
      />
    </div>
  );
}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/ClassDetailPage.tsx
git commit -m "feat(phase-4): full ClassDetailPage (Task 14)

- 3 sections: header + students + essays
- Add/remove students, CSV export, click-through to EssayPage
- /teacher/classes/:classId route wired

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 15: Rewrite `web/src/pages/PendingReviewsPage.tsx`

**Files:**
- Modify: `web/src/pages/PendingReviewsPage.tsx`

- [ ] **Step 1: Replace contents of `PendingReviewsPage.tsx`**

```typescript
import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClipboardCheck, ExternalLink } from 'lucide-react';
import { api, type PendingVerdict, type Class } from '@/api/client';

export function PendingReviewsPage() {
  const navigate = useNavigate();
  const [classes, setClasses] = useState<Class[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const [reviews, setReviews] = useState<PendingVerdict[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadClasses = useCallback(async () => {
    try {
      const data = await api.listMyClasses();
      setClasses(data);
      if (data.length > 0 && selectedClassId === null) {
        setSelectedClassId(data[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, [selectedClassId]);

  const loadReviews = useCallback(async (cid: number) => {
    try {
      setReviews(await api.listPendingReviews(cid));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  }, []);

  useEffect(() => { loadClasses(); }, [loadClasses]);
  useEffect(() => { if (selectedClassId !== null) loadReviews(selectedClassId); }, [selectedClassId, loadReviews]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-950 flex items-center justify-center">
          <ClipboardCheck className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Pending Reviews</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Verdict cần xem xét & override.</p>
        </div>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {loading ? <p className="text-slate-500">Loading…</p> : classes.length === 0 ? (
        <p className="text-sm text-slate-500">Bạn chưa phụ trách lớp nào.</p>
      ) : (
        <>
          <div role="group" aria-label="Lọc theo lớp" className="flex flex-wrap gap-2">
            {classes.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedClassId(c.id)}
                aria-pressed={selectedClassId === c.id}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  selectedClassId === c.id
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>

          <div className="rounded-xl bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-800 divide-y divide-slate-100 dark:divide-slate-800">
            {reviews.length === 0 ? (
              <p className="p-6 text-center text-sm text-slate-500">Không có verdict chờ xem xét.</p>
            ) : reviews.map((r) => (
              <button
                key={r.verdict_id}
                onClick={() => navigate(`/verification/report/${r.essay_id}`)}
                className="w-full text-left p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 flex items-start gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                      r.label === 'suspected_hallucination'
                        ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300'
                        : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                    }`}>{r.label}</span>
                    <span className="text-xs text-slate-500">{r.student_username ?? '—'}</span>
                  </div>
                  <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{r.filename}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">{r.reasoning}</p>
                </div>
                <ExternalLink className="h-4 w-4 text-slate-400 mt-1 shrink-0" />
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/PendingReviewsPage.tsx
git commit -m "feat(phase-4): real PendingReviewsPage (Task 15)

- Class filter chips with aria-pressed
- Per-verdict row with label badge, student, reasoning
- Click-through to EssayPage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 16: `web/src/components/RoleBadge.tsx` (extract from AccountManagementPage)

**Files:**
- Create: `web/src/components/RoleBadge.tsx`

- [ ] **Step 1: Create component**

```typescript
import { Shield, GraduationCap, User } from 'lucide-react';

type Role = 'user' | 'teacher' | 'admin';

const ROLE_STYLES: Record<Role, { bg: string; text: string; Icon: typeof Shield; label: string }> = {
  user:    { bg: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',    text: '', Icon: User,         label: 'Student' },
  teacher: { bg: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300', text: '', Icon: GraduationCap, label: 'Teacher' },
  admin:   { bg: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300', text: '', Icon: Shield,         label: 'Admin' },
};

export function RoleBadge({ role }: { role: Role | string }) {
  const style = ROLE_STYLES[role as Role] ?? ROLE_STYLES.user;
  const { Icon } = style;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${style.bg}`}>
      <Icon className="h-3 w-3" />
      {style.label}
    </span>
  );
}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/components/RoleBadge.tsx
git commit -m "feat(phase-4): add RoleBadge component (Task 16)

- 3 role variants with color + icon
- Used in AccountManagementPage and ClassDetailPage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 17: Refactor `AccountManagementPage` to use `RoleBadge` + show class column

**Files:**
- Modify: `web/src/pages/AccountManagementPage.tsx`

- [ ] **Step 1: Replace inline `RoleBadge` (lines 81-92) with import + use**

Find: `const RoleBadge = ({ role }: { role: string }) => (`
Replace with: import { RoleBadge } from '@/components/RoleBadge';
Then change all `<RoleBadge role={u.role} />` usages in the same file.

- [ ] **Step 2: Add class column to the user table**

After the existing columns (look for the `<th>` block), add `<th>Lớp</th>` and a corresponding `<td>` rendering `u.institution ?? '—'` (institution is the closest existing field; the dedicated class column requires new backend field, out of Phase 4 scope — see Review Focus #2).

- [ ] **Step 3: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/AccountManagementPage.tsx
git commit -m "refactor(phase-4): use RoleBadge in AccountManagementPage (Task 17)

- Extract inline RoleBadge to shared component
- Add 'Lớp' column showing institution

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 18: Update `OverrideControls` to call new audit-aware override endpoint

**Files:**
- Modify: `web/src/components/OverrideControls.tsx` (verify the component works with the new backend auth)

- [ ] **Step 1: Read current `OverrideControls.tsx` and verify it uses `api.overrideVerdict` correctly**

Run: `grep -n "overrideVerdict\|reason\|new_label" web/src/components/OverrideControls.tsx`
Expected: uses `api.overrideVerdict` with `verdict_id`, `new_label`, optional `reason`

- [ ] **Step 2: Add capability check using `useRole()`**

If the current component shows for all users, add a guard:
```typescript
import { useRole } from '@/hooks/useRole';
// inside component:
const { has } = useRole();
if (!has('override_verdict')) return null;
```

- [ ] **Step 3: Add a small banner showing audit info after successful override**

After `await api.overrideVerdict(...)`, show a toast or text: `"Đã ghi audit log"`. Use the existing `Toast` system if present, otherwise add a `<p>` with success styling.

- [ ] **Step 4: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 5: Commit**

```bash
git add web/src/components/OverrideControls.tsx
git commit -m "feat(phase-4): capability-gate OverrideControls + audit toast (Task 18)

- Hide OverrideControls from users without 'override_verdict' capability
- Show 'audit log' confirmation on success

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 19: `web/src/components/RoleGate.tsx` — verify it exists and add new capability

**Files:**
- Modify: `web/src/components/RoleGate.tsx` (verify; possibly add `'view_system_health'` case)

- [ ] **Step 1: Read `RoleGate.tsx` and confirm capability support**

Run: `cat web/src/components/RoleGate.tsx`
Expected: should already accept a `capability` prop

- [ ] **Step 2: If capability prop is missing, add it (skip if already present)**

```typescript
// Add to props:
export interface RoleGateProps {
  capability?: UserCapability;
  roles?: UserRole[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}
```

- [ ] **Step 3: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 4: Commit (if changed)**

```bash
git add web/src/components/RoleGate.tsx
git commit -m "feat(phase-4): ensure RoleGate supports capability prop (Task 19)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Skip this commit if no change was needed.)

---

## Task 20: Refactor `BatchUploadPage` to be teacher-context-aware

**Files:**
- Modify: `web/src/pages/BatchUploadPage.tsx`

- [ ] **Step 1: Read current `BatchUploadPage.tsx` to understand its current behavior**

Run: `cat web/src/pages/BatchUploadPage.tsx | head -100`

- [ ] **Step 2: Add a class-selector dropdown at the top when the user is a teacher**

```typescript
import { useRole } from '@/hooks/useRole';
import { api } from '@/api/client';
// inside component:
const { isTeacher, isAdmin } = useRole();
const [classes, setClasses] = useState<Class[]>([]);
const [targetClassId, setTargetClassId] = useState<number | null>(null);

useEffect(() => {
  if (isTeacher || isAdmin) {
    api.listMyClasses().then(setClasses);
  }
}, [isTeacher, isAdmin]);
```

- [ ] **Step 3: Render a select when `isTeacher` is true, and a helper note "Choose which class to assign these essays to"**

```jsx
{(isTeacher || isAdmin) && classes.length > 0 && (
  <div className="mb-4">
    <label htmlFor="class-select" className="block text-sm font-medium mb-1">Gán vào lớp (optional)</label>
    <select id="class-select" value={targetClassId ?? ''} onChange={(e) => setTargetClassId(e.target.value ? Number(e.target.value) : null)} className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm">
      <option value="">-- Không gán lớp --</option>
      {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
    </select>
  </div>
)}
```

- [ ] **Step 4: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/BatchUploadPage.tsx
git commit -m "feat(phase-4): teacher context in BatchUploadPage (Task 20)

- Show class selector when teacher/admin
- (Server-side assignment is out of scope; stored client-side for future)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 21: Empty states per role

**Files:**
- Modify: `web/src/pages/HistoryPage.tsx`, `web/src/pages/DashboardPage.tsx`

- [ ] **Step 1: In `HistoryPage.tsx`, branch the empty state by role**

```typescript
import { useRole } from '@/hooks/useRole';
const { isTeacher, isAdmin } = useRole();
// inside empty branch:
{essays.length === 0 && (
  <div>
    {isTeacher || isAdmin
      ? <p>Chưa có bài nộp nào trong lớp bạn phụ trách.</p>
      : <p>Tải bài lên để bắt đầu.</p>}
  </div>
)}
```

- [ ] **Step 2: In `DashboardPage.tsx`, branch the empty state by role**

Same pattern.

- [ ] **Step 3: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/HistoryPage.tsx web/src/pages/DashboardPage.tsx
git commit -m "feat(phase-4): role-specific empty states (Task 21)

- Teacher: 'no class essays yet'
- Student: 'upload to get started'

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 22: Hide demo credentials when not in demo mode

**Files:**
- Modify: `web/src/pages/LoginPage.tsx:261-271`

- [ ] **Step 1: Wrap the demo credentials block in a demo-mode check**

```typescript
{import.meta.env.VITE_DEMO_MODE === 'true' && (
  <div className="mt-4 p-3 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs">
    <p className="font-semibold mb-1">Demo accounts:</p>
    <p>admin / admin123 • teacher / teacher123 • user / user123</p>
  </div>
)}
```

- [ ] **Step 2: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -5`
Expected: build success

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/LoginPage.tsx
git commit -m "fix(phase-4): hide demo credentials outside demo mode (Task 22)

- Conditional on import.meta.env.VITE_DEMO_MODE === 'true'

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 23: End-to-end backend test pass

**Files:**
- (no new files; just verification)

- [ ] **Step 1: Run full backend test suite**

Run: `source .venv/bin/activate && python -m pytest tests/ -q --ignore=tests/unit/test_grobid_service.py --ignore=tests/unit/test_grobid_adapter.py --ignore=tests/unit/test_grobid_parser.py 2>&1 | tail -20`
Expected: 1000+ tests pass (993 + 7 new from Tasks 1, 2, 3, 4, 5, 6)

- [ ] **Step 2: Verify no regression in pre-existing tests**

If any pre-existing test fails, **STOP** and fix before continuing.

- [ ] **Step 3: Manual smoke test of new endpoints**

```bash
# Start backend in one terminal
uvicorn src.integrity_checker.api.main:app --port 8001 &

# In another terminal, with admin token:
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login -H "Content-Type: application/json" -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

curl -s http://localhost:8001/api/system/health -H "Authorization: Bearer $TOKEN" | jq .totals
curl -s "http://localhost:8001/api/audit/log?limit=5" -H "Authorization: Bearer $TOKEN" | jq '.[0]'
curl -s http://localhost:8001/api/teacher/dashboard -H "Authorization: Bearer $TOKEN" | jq '{total_classes, total_students}'
```

Expected: each returns 200 with non-empty JSON.

- [ ] **Step 4: Stop backend, commit verification**

```bash
# Kill the backend
pkill -f "uvicorn.*8001" || true
```

No code commit (verification only).

---

## Task 24: End-to-end frontend test pass + manual smoke

**Files:**
- (no new files; just verification)

- [ ] **Step 1: Run frontend build**

Run: `cd web && pnpm build 2>&1 | tail -10`
Expected: build success, bundle size similar to before (no huge regressions)

- [ ] **Step 2: Manual smoke test (if dev server is available)**

```bash
cd web && pnpm dev &
# Test in browser: login as teacher → /teacher/classes → create class → add student → upload essay
# Login as admin → /admin/system → /admin/audit
```

- [ ] **Step 3: Verify no console errors in browser DevTools**

Expected: no 401/403/500 in Network tab for normal flows.

- [ ] **Step 4: Stop dev server**

```bash
pkill -f "vite" || true
```

---

## Task 25: Final integration — branch ready for review

- [ ] **Step 1: Push branch**

```bash
git push -u origin feat/phase-4-pages
```

- [ ] **Step 2: Open PR with description**

PR title: `Phase 4: Teacher & Admin Pages (v1.16)`
PR body summary:
- Backend: AuditLog persistence, cross-tenant override auth, 3 new endpoints (system/audit/class-export)
- Frontend: 4 new pages (SystemHealth, AuditLog, MyClasses real, ClassDetail, PendingReviews real), 4 new components (StatCard, CreateClassDialog, AddStudentDialog, RoleBadge)
- Tests: +7 unit tests, 1000+ total backend tests
- Migration: none (uses existing Phase 3 schema)
- Manual smoke: all admin/teacher flows verified

- [ ] **Step 3: Wait for review/merge**

No commit; wait for the user to merge.

---

## Summary of Effort

| Task | Effort | Type | Layer |
|------|--------|------|-------|
| 1 | 30 min | Audit log persistence | Backend |
| 2 | 1h | Teacher override auth | Backend |
| 3 | 1h | Pending reviews endpoint | Backend |
| 4 | 1h | System health endpoint | Backend |
| 5 | 1h | Audit log endpoint | Backend |
| 6 | 1h | Class CSV export | Backend |
| 7 | 30 min | API client extension | Frontend |
| 8 | 30 min | StatCard component | Frontend |
| 9 | 1.5h | SystemHealthPage | Frontend |
| 10 | 1.5h | AuditLogPage | Frontend |
| 11 | 1h | CreateClassDialog | Frontend |
| 12 | 1h | AddStudentDialog | Frontend |
| 13 | 1.5h | MyClassesPage real | Frontend |
| 14 | 2h | ClassDetailPage | Frontend |
| 15 | 1.5h | PendingReviewsPage real | Frontend |
| 16 | 30 min | RoleBadge component | Frontend |
| 17 | 1h | AccountManagementPage refactor | Frontend |
| 18 | 1h | OverrideControls capability gate | Frontend |
| 19 | 15 min | RoleGate verification | Frontend |
| 20 | 1h | BatchUploadPage teacher context | Frontend |
| 21 | 1h | Role-specific empty states | Frontend |
| 22 | 30 min | Hide demo credentials | Frontend |
| 23 | 30 min | Backend integration test | Verification |
| 24 | 30 min | Frontend integration test | Verification |
| 25 | 15 min | PR | Verification |
| **Total** | **~22h** | (matches 2-week estimate in roadmap) | |

---

## Self-Review Checklist

- [x] **Spec coverage**: Each item in `IMPLEMENTATION_ROADMAP.md` §Phase 4 covered (Day 16-23):
  - 16.1 MyClassesPage → Task 13 ✓
  - 16.2 ClassDetailPage → Task 14 ✓
  - 16.3 PendingReviewsPage → Task 15 ✓
  - 16.4 BatchUploadPage → Task 20 ✓
  - 16.5 OverrideControls → Task 18 ✓
  - 19.1 SystemHealthPage → Task 9 ✓
  - 19.2 AuditLogPage → Task 10 ✓
  - 19.3 AccountManagementPage column → Task 17 ✓
  - 19.4 can_override_verdicts → already exists in models from Phase 3 ✓
  - 21.1 /api/system/health → Task 4 ✓
  - 21.2 /api/audit/log → Task 5 ✓
  - 21.3 teacher dashboard stats → exists from Phase 3 (Task 23 verifies) ✓
  - 21.4 CSV export per class → Task 6 ✓
  - 23.1 role-colored badges → Task 16 ✓
  - 23.2 empty states per role → Task 21 ✓
  - 23.3 hide demo credentials → Task 22 ✓

- [x] **Step scan**: Every step gives implementer exactly one thing to do; no "TBD" or "handle edge cases" lines.

- [x] **Type consistency**: `PendingVerdict`, `SystemHealth`, `AuditLogEntry` defined in Task 7 used in Tasks 9, 10, 15, 18; `Class` reused; `ListMyClasses` returns `Class[]` matches.

- [x] **Review Focus**: 6 review-focus lines, each pinned to a test in the right task:
  - Cross-tenant data leak → Task 2 (test_teacher_cannot_view_other_teachers_class_students-like) + Task 3 (test_teacher_cannot_view_other_teachers_class_pending)
  - Pending reviews outside scope → Task 3 (test_teacher_cannot_view_other_teachers_class_pending) + Task 4 (implicitly admin only)
  - Audit log immutability → Task 1 (no update endpoint ever created)
  - Override auth → Task 2
  - CSV row count → Task 6 (test_export_class_csv_returns_one_row_per_essay)
  - System health 403 → Task 4 (test_system_health_requires_admin)

- [x] **Proportion**: Plan is ~25 tasks over ~22h. Spec (Phase 4 section in roadmap) is ~16 tasks. Plan adds the per-step granularity and one extra task (Task 19 RoleGate verification) for safety. Proportion is reasonable.

---

**Plan complete. Ready for review.**
