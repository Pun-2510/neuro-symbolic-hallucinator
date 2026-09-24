# TASK LIST - Essay Integrity Checker
## Cập nhật: 2026-09-23 | Định hướng: Engineering Contribution

---

## PHASE 1: HOÀN THÀNH TRƯỚC KHI NỘP ĐỀ CƯƠNG (Tuần 12)

### Task 1.1: ExplanationGenerator - Sinh lý do bằng tiếng Việt
**Priority:** HIGH
**Status:** HOÀN THÀNH (2026-08-23)
**File:** `src/integrity_checker/logic/explanation.py`

### Task 1.2: ExplanationGenerator - Unit Tests
**Priority:** HIGH
**Status:** HOÀN THÀNH (2026-08-23)
**File:** `tests/unit/test_explanation.py`
**Test coverage:** 43 test cases

---

## PHASE 2: WEB UI (Tuần 13-14)

### Task 2.1-2.5: Web UI Components
**Status:** HOÀN THÀNH (2026-08-23)
- Style Profile View
- Citation Graph View (2 chiều)
- Override Mapping/Labels
- Evidence Drawer mở rộng
- Export PDF/CSV/JSON

### Task 2.6: Frontend UI Improvements
**Status:** HOÀN THÀNH (2026-09-19)
**Files:** `VerdictTable.tsx`, `MappingStatusBadge.tsx`

---

## PHASE 3: INTEGRATION & TESTING

### Task 3.1: GROBID Docker
**Status:** MOCK - Real Docker cần máy đủ RAM

### Task 3.2-3.5: Unit Tests
**Status:** HOÀN THÀNH
- Retrieval Orchestrator (14 tests)
- Semantic Matcher (11 tests)
- Calibration (24 tests)
- Bug Fixes (19 tests)

---

## PHASE 4: DOCUMENTATION (2026-09-23)

### Task 4.1-4.4: Documentation Updates
**Status:** HOÀN THÀNH
- [x] README.md (v1.4)
- [x] CLAUDE.md (v1.4)
- [x] TASKS.md (2026-09-23)
- [x] USER_MANUAL.md (cập nhật RESOURCE label)
- [x] CHECKPOINT_2026-09-23_v2.md

---

## CRITICAL BUG FIXES & FEATURES (2026-09-23)

### Fix 1: FTS5 Search for Local DB
**Status:** ✅ FIXED
**File:** `retrieval_orchestrator.py`

### Fix 2: Crossref Author Parsing
**Status:** ✅ FIXED
**File:** `crossref_client.py`

### Fix 3: OpenAlex API Key Support
**Status:** ✅ FIXED
**File:** `openalex_client.py`

### Fix 4: Remove Disk Cache
**Status:** ✅ FIXED
**Files:** `retrieval_orchestrator.py`, `api/routes/`
**Mô tả:** Sử dụng local DB thay vì disk cache

### Fix 5: URL Classification as RESOURCE (NEW)
**Status:** ✅ FIXED
**Files:** `models/validation.py`, `logic/neuro_symbolic_checker.py`, `logic/cis.py`, `pipeline/integrity_pipeline.py`
**Mô tả:**
- Thêm label `RESOURCE` cho URL/Reference links
- URLs (GitHub, websites) không còn là `UNRESOLVED`
- CIS tính trên academic citations only
- Marker 🔗 trong CLI

### Fix 6: Add Known Papers
**Status:** ✅ FIXED
**File:** `retrieval_orchestrator.py`
**Mô tả:** 22 known papers (Parikh, Taylor, Logeswaran, Dolan, Mikolov, Kim, Kaiser, etc.)

### Fix 7: to_dict() None Features Crash
**Status:** ✅ FIXED
**File:** `pipeline/integrity_pipeline.py`
**Mô tả:** Handle None features khi serialize RESOURCE citations

---

## METRICS HIỆN TẠI (v1.4 - 2026-09-23)

| Metric | Value |
|--------|-------|
| **Version** | v1.4 |
| **Total Tests** | 608 passed |
| **Skipped** | 4 (GROBID Docker) |
| **Failed** | 0 |
| **Known Papers** | 22 |
| **Validation Labels** | 5 (VERIFIED, METADATA_ERROR, SUSPECTED, UNRESOLVED, RESOURCE) |

### Test Results - Verified Papers

| Paper | CIS | Verified | Suspected | Resource | Unresolved |
|-------|-----|----------|-----------|----------|------------|
| BERT.pdf | **97.43** | 93.1% | 1 | 5 | 0 |
| Attention.pdf | **92.99** | 98.6% | 1 | 0 | 0 |
| VietDepression.pdf | **~100** | 100% | 0 | 0 | 0 |
| Scenario A | **96.3** | 95% | 0 | 1 | 0 |
| Scenario B | **81.1** | 73% | 1 | 4 | 0 |

---

## TASKS CÒN LẠI

### High Priority
- [ ] GROBID Docker (cần máy đủ RAM)
- [ ] Dataset annotation - ground truth
- [ ] Baselines B0-B5

### Medium Priority
- [ ] Performance optimization - batch API calls
- [ ] Crossref API key integration

### Low Priority
- [ ] Write thesis Chapter 1-6
- [ ] Presentation slides
- [ ] Demo video

---

**Last updated:** 2026-09-23
**Version:** v1.4
**Maintained by:** Nguyen Bao Minh (523H0054) & Tran Gia Thanh (523H0096)
