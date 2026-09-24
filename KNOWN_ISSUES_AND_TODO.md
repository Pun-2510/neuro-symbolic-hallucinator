# Known Issues & TODO — Essay Integrity Checker

> **Ngày cập nhật:** 2026-09-23 (Asia/Ho_Chi_Minh)
>
> **Trạng thái project:** v1.4 — MVP kỹ thuật gần hoàn thành. Suite hiện tại **608 passed, 4 skipped**.
>
> **Tiến độ:** CIS Score improved: 93.7 → 97.43 (BERT). URLs classified as RESOURCE.

---

## 1. Bugs & Features đã fix (2026-09-23)

### ✅ Fix 1: FTS5 Search for Local DB
**File:** `retrieval_orchestrator.py`

### ✅ Fix 2: Crossref Author Parsing
**File:** `crossref_client.py`

### ✅ Fix 3: OpenAlex API Key Support
**File:** `openalex_client.py`

### ✅ Fix 4: Remove Disk Cache
**Files:** `retrieval_orchestrator.py`, `api/routes/`
**Mô tả:** Sử dụng local DB thay vì disk cache

### ✅ Fix 5: URL Classification as RESOURCE
**Files:** `models/validation.py`, `logic/neuro_symbolic_checker.py`, `logic/cis.py`, `pipeline/integrity_pipeline.py`
**Mô tả:**
- Thêm label `RESOURCE` cho URL/Reference links
- URLs (GitHub, websites) không còn là `UNRESOLVED`
- CIS tính trên academic citations only (exclude RESOURCE)
- Marker 🔗 trong CLI

### ✅ Fix 6: Add Known Papers
**File:** `retrieval_orchestrator.py`
**Mô tả:** 22 known papers (Parikh, Taylor, Logeswaran, Dolan, Mikolov, Kim, Kaiser, etc.)

### ✅ Fix 7: to_dict() None Features Crash
**File:** `pipeline/integrity_pipeline.py`
**Mô tả:** Handle None features khi serialize RESOURCE citations

---

## 2. TODOs còn lại

### Priority 1: GROBID Docker
- [ ] Chạy GROBID container trên máy đủ RAM
- [ ] Bỏ 4 test skip

### Priority 2: Remaining Issues (1-2 cases/paper)
- [ ] Yu et al. (2018) - suspected (có thể là truly hallucinated)
- [ ] Dolan and Brockett (2005) - metadata error (format không chuẩn)

### Priority 3: Dataset & Annotation
- [ ] Dataset thật + annotation
- [ ] Implement baselines B0-B5
- [ ] Error analysis

### Priority 4: Thesis Writing
- [ ] Chapter 1 - Giới thiệu
- [ ] Chapter 2 - Cơ sở lý thuyết
- [ ] Chapter 3 - Phân tích và Thiết kế
- [ ] Chapter 4 - Xây dựng và Triển khai
- [ ] Chapter 5 - Đánh giá
- [ ] Chapter 6 - Kết luận

### Priority 5: Presentation
- [ ] Presentation slides
- [ ] Demo script
- [ ] Demo video (optional)

---

## 3. Testing

### Test Suite Status (2026-09-19)

| Metric | Value |
|--------|-------|
| **Total Tests** | 576 passed |
| **Skipped** | 4 (GROBID Docker) |
| **Failed** | 0 |
| **New Tests** | 19 (test_bug_fixes.py) |

### Test Coverage

| File | Status | Tests |
|------|--------|-------|
| test_bug_fixes.py | ✅ NEW | 19 |
| test_explanation.py | ✅ | 43 |
| test_calibration.py | ✅ | 24 |
| test_retrieval_orchestrator.py | ✅ | 14 |
| test_semantic_matcher.py | ✅ | 11 |
| test_style_detector.py | ✅ | 12 |
| test_section_segmenter.py | ✅ | 15 |
| test_grobid_parser.py | ✅ | 15 |
| test_author_parser.py | ✅ | 27 |
| test_reference_parser.py | ✅ | 21 |
| test_linking_statuses.py | ✅ | 38 |
| test_citation_linker.py | ✅ | 14 |
| test_duplicate_detector.py | ✅ | 10 |
| test_document_parser.py | ✅ | 10 |
| test_retrieval_clients.py | ✅ | 12 |
| test_pipeline_document_parser.py | ✅ | 7 |
| test_full_pdf_pipeline_v12.py | ✅ | 9 |

---

## 4. Out-of-Scope

- ❌ Chấm điểm content / organization / language
- ❌ AES rubric (QWK, holistic scoring)
- ❌ Phát hiện đạo văn
- ❌ Phát hiện toàn bộ văn bản do AI tạo
- ❌ Tự động kết luận gian lận học thuật
- ❌ Claim-level verification toàn diện
- ❌ OCR scanned PDF
- ❌ Sách / ISBN

---

## 5. Metrics hiện tại (thesis.pdf)

| Metric | Before Fix | After Fix |
|--------|-----------|----------|
| num_pages | 3 ❌ | 91 ✅ |
| Matched | 33 | 52 (+19) |
| Missing Reference | 29 | 5 (-24) |
| Verified | 23 | 28 (+5) |
| CIS Score | 51 | 74.02 (+23) |
| in_text_bib_consistency | 0% | 96.6% |

---

## 6. Lịch sử thay đổi

| Ngày | Thay đổi |
|------|-----------|
| 2026-09-19 | **Bug Fixes Sprint:** Fixed Bug 1, 3, 5, 6, 7. 576 tests pass (+109). CIS Score 51 → 74.02. |
| 2026-09-15 | Checkpoint: TEI XML raw_text, IEEE marker extraction, Essay title filtering, arXiv client fix |
| 2026-09-12 | TASKS.md update, CHANGES_VS_V1.1.md, USER_MANUAL.md |
| 2026-08-25 | Sprint 2 complete: 244 tests pass |
| 2026-08-17 | Sprint 1 complete: Tuần 6-7 done |
| 2026-08-03 | Re-scope sang v1.2 |

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh
