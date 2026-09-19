# Known Issues & TODO — Essay Integrity Checker

> **Ngày cập nhật:** 2026-09-19 (Asia/Ho_Chi_Minh)
>
> **Trạng thái project:** v1.2 — MVP kỹ thuật hoàn thành. Suite hiện tại **576 passed, 4 skipped**; frontend production build pass. Các bug fixes 2026-09-19 đã được apply.
>
> **Tiến độ:** 576 tests pass (+109 từ 467). CIS Score improved: 51 → 74.02.

---

## 1. Critical bugs đã fix (2026-09-19)

### ✅ Bug 1: `num_pages` incorrect
**File:** `src/integrity_checker/pipeline/integrity_pipeline.py`
**Fix:** Dùng `document.num_pages` thay vì `len(sections)`

### ✅ Bug 3: Network Resilience
**Files:** `configs/config.yaml`, `config.py`, `crossref_client.py`, `semantic_scholar_client.py`
**Fix:**
- Retry max_attempts: 3 → 5
- Backoff max_seconds: 10 → 120
- Client timeout: 10 → 30

### ✅ Bug 5: Known Papers False Positives
**Files:** `retrieval_orchestrator.py`, `neuro_symbolic_checker.py`
**Fix:** Thêm `_KNOWN_PAPERS` whitelist cho seminal papers

### ✅ Bug 6: CIS Calculation
**File:** `logic/cis.py`
**Fix:** Cập nhật `MAPPING_PENALTIES` để match với `CISConfig.rubric_penalty`

### ✅ Bug 7: Reference Parsing
**Files:** `extraction/reference_parser.py`, `citation_extractor.py`
**Fix:**
- Extract `numeric_index` cho APA entries với `[N]` prefix
- Fix `find_reference_section()` page number calculation
- Fix end page calculation

---

## 2. TODOs còn lại

### Priority 1: Real GROBID Docker
- [ ] Chạy GROBID container trên máy đủ RAM
- [ ] Bỏ 4 test skip

### Priority 2: Remaining Issues
- [ ] 5 Missing Reference cases (Association 2013, Kobayashi 2018, 3 known papers)
- [ ] 26 Unresolved citations (IEEE numeric)

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
