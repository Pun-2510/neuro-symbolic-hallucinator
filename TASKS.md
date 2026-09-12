# TASK LIST - Essay Integrity Checker
## Cập nhật: 2026-09-12 | Định hướng: Engineering Contribution

---

## PHASE 1: HOAN THANH TRUOC KHI NOP DE CUONG (Tuan 12)

### Task 1.1: ExplanationGenerator - Sinh ly do bang tieng Viet
**Priority:** HIGH  
**Status:** HOAN THANH (2026-08-23)  
**File:** `src/integrity_checker/logic/explanation.py`

**Da implement:**
- `short()` - One-liner tieng Viet cho UI (voi mapping status)
- `detailed()` - Multi-line explanation cho report (Nhan / Ly do / Bang chung / Mapping / Nguon)
- `suggestions()` - Goi y hanh dong cho giang vien (ca source + mapping)
- `structured()` - Dict co cau truc cho UI components
- `_default_reasoning()` - Tu dong generate reasoning dua tren verdict
- Vietnamese translations cho tat ca ValidationLabels va MappingStatuses

**Test cases:**
- [x] VERIFIED
- [x] METADATA_ERROR
- [x] SUSPECTED_HALLUCINATION
- [x] UNRESOLVED

---

### Task 1.2: ExplanationGenerator - Unit Tests
**Priority:** HIGH  
**Status:** HOAN THANH (2026-08-23)  
**File:** `tests/unit/test_explanation.py`

**Test coverage:** 43 test cases
- Translation tests (LABEL_VI, MAPPING_VI)
- short() method tests (4 labels + mapping)
- _default_reasoning() tests (4 scenarios)
- detailed() tests (basic, features, source, mapping)
- suggestions() tests (4 labels + 8 mapping statuses)
- structured() tests (fields, values, evidence, formatting)
- Edge cases (empty verdict, None source, long titles)
- Integration tests (full verdict scenarios)

---

## PHASE 2: WEB UI (Tuan 13-14)

### Task 2.1: Web UI - Style Profile View
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**Files:** `web/src/components/StyleProfileCard.tsx`

**Da implement:**
- Badge "APA-Like" / "IEEE-Like" / "Mixed" / "Unknown" with icons
- Confidence score bar (percentage + visual bar)
- Features display (apa_count, ieee_count, mixed_count)
- Color scheme: Blue/Green/Amber/Gray

---

### Task 2.2: Web UI - Citation Graph View (2 chieu)
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**Files:** `web/src/components/CitationGraphView.tsx`

**Da implement:**
- 3 view modes: Integrity / Source / Combined
- Filter chips for all 8 mapping statuses + 4 labels
- Click row -> open detail drawer
- Stats bar showing counts
- Override controls per row

---

### Task 2.3: Web UI - Override Mapping/Labels
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**Files:** `web/src/components/OverrideControls.tsx`, `src/integrity_checker/api/routes/verdicts.py`

**Da implement:**
- Edit icon button on each citation row
- Dropdown to select new label/status
- Reason text area for override note
- API endpoint: POST `/api/essays/{id}/verdicts/{id}/override`
- Visual indicator for overridden rows (amber border)

---

### Task 2.4: Web UI - Evidence Drawer mo rong
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**Files:** `web/src/components/CitationDetailDrawer.tsx`

**Da implement:**
- Two-layer badges (Source + Integrity)
- Evidence section with per-source cards
- Open links to CrossRef/OpenAlex/S2/arXiv
- Matched fields badges
- Checked timestamp
- Triggered rules display
- Override history section

---

### Task 2.5: Web UI - Export PDF/CSV/JSON
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**Files:** `src/integrity_checker/api/routes/report.py`

**Da implement:**
- [x] Export JSON: v1.2 schema with linking_summary + verdicts
- [x] Export CSV: all v1.2 fields included
- [x] Export PDF: formatted report with summary stats

**PDF includes:**
- Report title and essay metadata
- Summary statistics for both layers (source + integrity)
- Citation details table (up to 50 per page)
- Disclaimer

---

## PHASE 3: INTEGRATION & TESTING (Tuan 15)

### Task 3.1: Integration Test - GROBID Docker
**Priority:** HIGH  
**Status:** MOCK HOÀN THÀNH; REAL DOCKER ĐANG CHỜ MÁY ĐỦ RAM
**Files:** `scripts/grobid_docker_setup.sh`, `tests/integration/`

**Mô tả:** End-to-end test với GROBID Docker container thật và mock mode.

**Requirements:**
- [x] Mock HTTP integration: 16 tests pass.
- [x] Script start/stop/status/logs và health check.
- [ ] `./scripts/grobid_docker_setup.sh start` trên Docker host đủ RAM.
- [ ] Chạy real mode trên sample PDFs và verify output.
- [x] Teardown command đã có: `./scripts/grobid_docker_setup.sh stop`.

**Ghi chú:** 4 real-mode tests hiện được skip; checkpoint 2026-09-05 ghi nhận GROBID image bị OOM trên máy macOS hiện tại.

---

### Task 3.2: Integration Test - Full PDF Pipeline v1.2
**Priority:** HIGH  
**Status:** HOÀN THÀNH (2026-08-25, 9 tests pass)
**File:** `tests/integration/test_full_pdf_pipeline_v12.py`

**Test cases can cover:**
- [x] PDF với mixed citations (thật + ảo)
- [x] PDF chỉ có DOI references
- [x] PDF không có references / empty report
- [x] PDF với fabrication markers
- [x] API fail fallback → UNRESOLVED
- [x] Cache hit → verify `cached=True`

---

### Task 3.3: Unit Tests - Retrieval Orchestrator
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**File:** `tests/unit/test_retrieval_orchestrator.py`

**Test coverage:** 14 tests
- Happy path: 4 sources succeed
- Partial failure: 2+ sources fail
- Cache hit/miss behavior
- Rate limiting
- Serialization/deserialization
- Deduplication by DOI
- Sequential mode

---

### Task 3.4: Unit Tests - Semantic Matcher
**Priority:** MEDIUM
**Status:** HOAN THANH (2026-08-23)
**File:** `tests/unit/test_semantic_matcher.py`

**Test coverage:** 11 tests
- Exact match -> high score
- Partial match -> medium score
- No match -> low score
- Multi-language title
- Empty/None text edge cases
- Model loading and exception handling
- Similarity clamping to 0.0-1.0

---

### Task 3.5: Unit Tests - Calibration
**Priority:** MEDIUM
**Status:** HOAN THANH (truoc)
**File:** `tests/unit/test_calibration.py`

**Test coverage:** 21 tests
- Perfect calibration -> ECE gan 0
- Miscalibration -> ECE > 0
- Coverage-accuracy trade-off
- Abstention band calculation

---

## PHASE 4: DOCUMENTATION (Tuan 16)

### Task 4.1: Update CHANGES_VS_V1.1.md
**Priority:** MEDIUM  
**Status:** HOÀN THÀNH (2026-09-12)
**File:** `docs/CHANGES_VS_V1.1.md`

**Mo ta:** Tai lieu hoa tat ca thay doi tu v1.1 sang v1.2.

---

### Task 4.2: Update API Documentation
**Priority:** MEDIUM  
**Status:** ĐANG CẬP NHẬT
**Files:** `src/integrity_checker/api/routes/`, FastAPI auto-generated docs

---

### Task 4.3: Update User Manual
**Priority:** MEDIUM  
**Status:** HOÀN THÀNH (2026-09-12)
**Files:** `docs/USER_MANUAL.md` (moi)

---

## PHASE 5: THESIS WRITING (Tuan 17-20)

### Task 5.1: Chapter 1 - Gioi thieu
**Priority:** HIGH  
**Status:** Chua bat dau

---

### Task 5.2: Chapter 2 - Co so ly thuyet
**Priority:** HIGH  
**Status:** Chua bat dau

---

### Task 5.3: Chapter 3 - Phan tich va Thiet ke
**Priority:** HIGH  
**Status:** Chua bat dau

---

### Task 5.4: Chapter 4 - Xay dung va Tuyen khai
**Priority:** HIGH  
**Status:** Chua bat dau

---

### Task 5.5: Chapter 5 - Danh gia
**Priority:** MEDIUM  
**Status:** Chua bat dau

---

### Task 5.6: Chapter 6 - Ket luan
**Priority:** MEDIUM  
**Status:** Chua bat dau

---

## PHASE 6: PRESENTATION & DEMO (Tuan 21-22)

### Task 6.1: Presentation Slides
**Priority:** HIGH  
**Status:** Chua bat dau

---

### Task 6.2: Demo Script
**Priority:** HIGH  
**Status:** Chua bat dau

---

### Task 6.3: Demo Video (Optional)
**Priority:** LOW  
**Status:** Chua bat dau

---

## TASKS DA HOAN THANH

### Sprint 1-2 (Tuan 6-11)
- [x] SectionSegmenter
- [x] AuthorParser
- [x] ReferenceListParser
- [x] GROBID adapter
- [x] StyleDetector
- [x] CitationLinker
- [x] DuplicateDetector
- [x] DocumentParser
- [x] CrossRef client
- [x] OpenAlex client
- [x] Semantic Scholar client
- [x] arXiv client
- [x] AuthorMatcher
- [x] VenueNormalizer
- [x] SourceConsensus
- [x] FuzzyTuner
- [x] Rules extension
- [x] Calibration
- [x] Output schema tach integrity vs source
- [x] CIS calculator
- [x] ExplanationGenerator (Task 1.1)
- [x] Unit tests ExplanationGenerator (Task 1.2) - 43 tests
- [x] 426 tests pass

---

**Last updated:** 2026-09-12
**Maintained by:** Nguyen Bao Minh (523H0054) & Tran Gia Thanh (523H0096)
