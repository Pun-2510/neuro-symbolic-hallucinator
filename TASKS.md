# TASK LIST - Essay Integrity Checker
## Cập nhật: 2026-09-19 | Định hướng: Engineering Contribution

---

## PHASE 1: HOÀN THÀNH TRƯỚC KHI NỘP ĐỀ CƯƠNG (Tuần 12)

### Task 1.1: ExplanationGenerator - Sinh lý do bằng tiếng Việt
**Priority:** HIGH  
**Status:** HOÀN THÀNH (2026-08-23)  
**File:** `src/integrity_checker/logic/explanation.py`

---

### Task 1.2: ExplanationGenerator - Unit Tests
**Priority:** HIGH  
**Status:** HOÀN THÀNH (2026-08-23)  
**File:** `tests/unit/test_explanation.py`
**Test coverage:** 43 test cases

---

## PHASE 2: WEB UI (Tuần 13-14)

### Task 2.1: Web UI - Style Profile View
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)

### Task 2.2: Web UI - Citation Graph View (2 chiều)
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)

### Task 2.3: Web UI - Override Mapping/Labels
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)

### Task 2.4: Web UI - Evidence Drawer mở rộng
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)

### Task 2.5: Web UI - Export PDF/CSV/JSON
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)

### Task 2.6: Frontend UI Improvements (2026-09-19)
**Priority:** MEDIUM
**Status:** HOÀN THÀNH
**Files:** `VerdictTable.tsx`, `MappingStatusBadge.tsx`

**Đã implement:**
- Header labels rõ ràng: "Link Status (↔ Ref)", "Source Verify (✓ Source)"
- Tooltips giải thích cho mỗi mapping status
- Phân biệt 2 layers: Integrity vs Source verification

---

## PHASE 3: INTEGRATION & TESTING (Tuần 15)

### Task 3.1: Integration Test - GROBID Docker
**Priority:** HIGH  
**Status:** MOCK HOÀN THÀNH; REAL DOCKER ĐANG CHỜ MÁY ĐỦ RAM

### Task 3.2: Integration Test - Full PDF Pipeline v1.2
**Priority:** HIGH  
**Status:** HOÀN THÀNH (2026-08-25, 9 tests pass)

### Task 3.3: Unit Tests - Retrieval Orchestrator
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)
**Test coverage:** 14 tests

### Task 3.4: Unit Tests - Semantic Matcher
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-08-23)
**Test coverage:** 11 tests

### Task 3.5: Unit Tests - Calibration
**Priority:** MEDIUM
**Status:** HOÀN THÀNH
**Test coverage:** 24 tests

### Task 3.6: Bug Fixes Tests (2026-09-19)
**Priority:** HIGH
**Status:** HOÀN THÀNH
**File:** `tests/unit/test_bug_fixes.py`
**Test coverage:** 19 tests

**Bao gồm:**
- Bug 1: num_pages calculation
- Bug 3: retry config, timeout values
- Bug 5: known papers whitelist
- Bug 6: CIS penalties alignment
- Bug 7: reference parsing, numeric_index extraction

---

## PHASE 4: DOCUMENTATION (Tuần 16)

### Task 4.1: Update CHANGES_VS_V1.1.md
**Priority:** MEDIUM  
**Status:** HOÀN THÀNH (2026-09-12)

### Task 4.2: Update API Documentation
**Priority:** MEDIUM  
**Status:** ĐANG CẬP NHẬT

### Task 4.3: Update User Manual
**Priority:** MEDIUM  
**Status:** HOÀN THÀNH (2026-09-12)

### Task 4.4: Update Checkpoints
**Priority:** MEDIUM
**Status:** HOÀN THÀNH (2026-09-19)
**File:** `CHECKPOINT_2026-09-19.md`

---

## PHASE 5: THESIS WRITING (Tuần 17-20)

### Task 5.1: Chapter 1 - Giới thiệu
**Priority:** HIGH  
**Status:** Chưa bắt đầu

### Task 5.2: Chapter 2 - Cơ sở lý thuyết
**Priority:** HIGH  
**Status:** Chưa bắt đầu

### Task 5.3: Chapter 3 - Phân tích và Thiết kế
**Priority:** HIGH  
**Status:** Chưa bắt đầu

### Task 5.4: Chapter 4 - Xây dựng và Triển khai
**Priority:** HIGH  
**Status:** Chưa bắt đầu

### Task 5.5: Chapter 5 - Đánh giá
**Priority:** MEDIUM  
**Status:** Chưa bắt đầu

### Task 5.6: Chapter 6 - Kết luận
**Priority:** MEDIUM  
**Status:** Chưa bắt đầu

---

## PHASE 6: PRESENTATION & DEMO (Tuần 21-22)

### Task 6.1: Presentation Slides
**Priority:** HIGH  
**Status:** Chưa bắt đầu

### Task 6.2: Demo Script
**Priority:** HIGH  
**Status:** Chưa bắt đầu

### Task 6.3: Demo Video (Optional)
**Priority:** LOW  
**Status:** Chưa bắt đầu

---

## CRITICAL BUG FIXES (2026-09-19)

### Bug 1: num_pages incorrect
**Status:** ✅ ĐÃ FIX
**File:** `src/integrity_checker/pipeline/integrity_pipeline.py`
**Mô tả:** num_pages = len(sections) → document.num_pages

### Bug 3: Network Resilience
**Status:** ✅ ĐÃ FIX
**Files:** `configs/config.yaml`, `config.py`, `crossref_client.py`, `semantic_scholar_client.py`
**Mô tả:** Tăng retry attempts (3→5), backoff max (10→120s), timeout (10→30s)

### Bug 5: Known Papers False Positives
**Status:** ✅ ĐÃ FIX
**Files:** `retrieval_orchestrator.py`, `neuro_symbolic_checker.py`
**Mô tả:** Thêm whitelist cho seminal papers (Vaswani, Devlin, Sennrich, etc.)

### Bug 6: CIS Calculation
**Status:** ✅ ĐÃ FIX
**File:** `logic/cis.py`
**Mô tả:** Cập nhật MAPPING_PENALTIES để match với rubric

### Bug 7: Reference Parsing
**Status:** ✅ ĐÃ FIX
**Files:** `extraction/reference_parser.py`, `citation_extractor.py`
**Mô tả:** 
- Extract numeric_index cho APA entries với [N] prefix
- Fix find_reference_section() page number calculation

---

## TASKS ĐÃ HOÀN THÀNH

### Sprint 1-2 (Tuần 6-11)
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
- [x] Output schema tách integrity vs source
- [x] CIS calculator
- [x] ExplanationGenerator
- [x] Unit tests - 467 tests pass

### Sprint 3 (Tuần 12-16) - Updated 2026-09-19
- [x] Critical Bug Fixes (Bug 1, 3, 5, 6, 7)
- [x] Frontend UI Improvements
- [x] Bug Fix Tests (19 tests)
- [x] **Total: 576 tests pass** (+109 from previous)

---

## METRICS HIỆN TẠI

| Metric | Value |
|--------|-------|
| **Total Tests** | 576 passed |
| **Skipped** | 4 (GROBID Docker) |
| **Failed** | 0 |
| **CIS Score (thesis.pdf)** | 74.02 |
| **Verified Citations** | 28 |
| **Matched References** | 52 |
| **Missing Reference** | 5 |

---

**Last updated:** 2026-09-19
**Maintained by:** Nguyen Bao Minh (523H0054) & Tran Gia Thanh (523H0096)
