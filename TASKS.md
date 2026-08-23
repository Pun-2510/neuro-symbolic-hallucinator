# TASK LIST - Essay Integrity Checker
## Ngay: 2026-08-23 | Dinh huong: Engineering Contribution

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
**Status:** Chua bat dau  
**Files:** `web/src/components/`, `web/src/pages/`

**Mo ta:** Hien thi badge style + confidence + features ho tro trong UI.

**Requirements:**
- [ ] Them badge hien thi "APA-like" / "IEEE-like" / "MIXED" / "UNKNOWN"
- [ ] Hien thi confidence score dang progress bar
- [ ] Collapsible section cho features (apa_count, numeric_count, ratios)
- [ ] Mau sac theo style:
  - APA-like: Blue
  - IEEE-like: Green
  - MIXED: Yellow
  - UNKNOWN: Gray

---

### Task 2.2: Web UI - Citation Graph View (2 chieu)
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**Files:** `web/src/components/CitationGraph.tsx` (moi)

**Mo ta:** Hien thi bidirectional linking giua in-text citations va reference entries.

**Requirements:**
- [ ] Dang bang 2 cot: In-text | Reference Entry
- [ ] Highlight mau theo `CitationMappingStatus`
- [ ] Filter dropdown cho cac trang thai: ALL / MATCHED / MISSING / UNCITED / MISMATCH / DUPLICATE
- [ ] Click vao row -> hien thi chi tiet + evidence

---

### Task 2.3: Web UI - Override Mapping/Labels
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**Files:** `web/src/components/`, `api/routes/`

**Mo ta:** Cho phep giang vien sua mapping status / validation label va log lai.

**Requirements:**
- [ ] Click icon edit tren moi citation
- [ ] Dropdown de chon label moi
- [ ] Text area de nhap ly do override
- [ ] POST len API: `/api/verdicts/{id}/override`
- [ ] Backend luu vao `audit_logs` table

---

### Task 2.4: Web UI - Evidence Drawer mo rong
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**Files:** `web/src/components/EvidenceDrawer.tsx`

**Mo ta:** Hien thi opening record tu CrossRef/OpenAlex/S2/arXiv + source provenance + thoi diem kiem tra.

**Requirements:**
- [ ] Tabs cho tung nguon: CrossRef | OpenAlex | Semantic Scholar | arXiv
- [ ] Hien thi metadata da tim duoc (title, authors, year, venue)
- [ ] Badge "Cached" neu tu cache
- [ ] Timestamp khi kiem tra
- [ ] Link "Open in [Source]" den trang goc

---

### Task 2.5: Web UI - Export PDF/CSV/JSON
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**Files:** `api/routes/export.py`, `web/src/pages/ExportPage.tsx`

**Mo ta:** Export bao cao voi 2 lop output tach riet.

**Requirements:**
- [ ] Export JSON: chua day du 2 lop (integrity + source)
- [ ] Export CSV: flatten thanh bang, cot rieng cho moi truong
- [ ] Export PDF: formatted report voi summary stats
- [ ] Include disclaimer header trong moi export

---

## PHASE 3: INTEGRATION & TESTING (Tuan 15)

### Task 3.1: Integration Test - GROBID Docker
**Priority:** HIGH  
**Status:** Chua bat dau  
**Files:** `scripts/grobid_docker_setup.sh`, `tests/integration/`

**Mo ta:** End-to-end test voi GROBID Docker container that.

**Requirements:**
- [ ] `./scripts/grobid_docker_setup.sh start` -> verify health
- [ ] Run pipeline tren sample PDFs
- [ ] Verify output structure day du
- [ ] Teardown: `./scripts/grobid_docker_setup.sh stop`

---

### Task 3.2: Integration Test - Full PDF Pipeline v1.2
**Priority:** HIGH  
**Status:** Chua bat dau  
**File:** `tests/integration/test_full_pdf_pipeline_v12.py`

**Test cases can cover:**
- [ ] PDF voi mixed citations (that + ao)
- [ ] PDF chi co DOI references
- [ ] PDF khong co references
- [ ] PDF voi fabrication markers
- [ ] API fail fallback -> UNRESOLVED
- [ ] Cache hit -> verify cached=True

---

### Task 3.3: Unit Tests - Retrieval Orchestrator
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**File:** `tests/unit/test_retrieval_orchestrator.py`

**Test cases:**
- [ ] Happy path: 4 sources tra ve results
- [ ] Partial failure: 2 sources fail -> still proceed
- [ ] All fail: return empty + UNRESOLVED sentinel
- [ ] Cache hit: verify not calling APIs
- [ ] Cache miss: verify calling APIs
- [ ] Rate limiting: verify backoff works

---

### Task 3.4: Unit Tests - Semantic Matcher
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**File:** `tests/unit/test_semantic_matcher.py`

**Test cases:**
- [ ] Exact match -> high score
- [ ] Partial match -> medium score
- [ ] No match -> low score
- [ ] Multi-language title

---

### Task 3.5: Unit Tests - Calibration
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**File:** `tests/unit/test_calibration.py`

**Test cases:**
- [ ] Perfect calibration -> ECE gan 0
- [ ] Miscalibration -> ECE > 0
- [ ] Coverage-accuracy trade-off
- [ ] Abstention band calculation

---

## PHASE 4: DOCUMENTATION (Tuan 16)

### Task 4.1: Update CHANGES_VS_V1.1.md
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**File:** `docs/CHANGES_VS_V1.1.md`

**Mo ta:** Tai lieu hoa tat ca thay doi tu v1.1 sang v1.2.

---

### Task 4.2: Update API Documentation
**Priority:** MEDIUM  
**Status:** Chua bat dau  
**Files:** `src/integrity_checker/api/routes/`, FastAPI auto-generated docs

---

### Task 4.3: Update User Manual
**Priority:** MEDIUM  
**Status:** Chua bat dau  
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

**Last updated:** 2026-08-23
**Maintained by:** Nguyen Bao Minh (523H0054) & Tran Gia Thanh (523H0096)
