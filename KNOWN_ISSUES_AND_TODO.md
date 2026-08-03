# Known Issues & TODO — Essay Integrity Checker

> **Ngày cập nhật:** 2026-08-17 (Asia/Ho_Chi_Minh)
>
> **Trạng thái project:** v1.2 — đã hoàn thành **Tuần 6 (extraction)** và **Tuần 7 (style detection)**. Citation parser, SectionSegmenter, GROBID adapter, AuthorParser, StyleDetector đều có unit tests pass. Pipeline end-to-end trên sample PDF vẫn chạy, các module mới đã được export qua `extraction/` package.
>
> Mục tiêu cũ — "citation-only, GROBID là mở rộng tương lai" — đã được thay bằng mục tiêu v1.2 — **full-text + style detection + bidirectional linking** (xem `final (1).docx`).
>
> 2 test case trong ReferenceListParser vẫn fail (Dutch multi-word single entry + 2-line APA split) — tracked tại task #18 (backlog).

File này liệt kê:

1. **Critical bugs / sai logic** cần fix sớm
2. **TODOs mới** theo từng tuần của kế hoạch 18 tuần (v1.2)
3. **Re-scoped từ v1.1** — những thứ "mở rộng" nay đã trở thành must-have
4. **Caveats kỹ thuật** (thiết kế hiện tại chưa tối ưu, sẽ refactor sau)
5. **Out-of-scope** (ghi rõ để tránh scope creep)
6. **Testing gaps**
7. **Security / privacy notes**

---

## 1. Critical bugs / sai logic — fix NGAY

### 1.1 ❌ `Citation.to_search_query()` lấy last-name sai cho một số biến thể APA

**Vấn đề:** Logic hiện tại xử lý `"Smith, A."` (lấy token trước dấu phẩy) và fallback `"Smith A."` (lấy token cuối), nhưng vẫn chưa robust:

```
"van der Berg, J."   → last-name = "van der Berg"   ❌ (chỉ lấy "van")
"Smith J. K."         → last-name = "Smith"         ❌ (không có dấu phẩy)
"J. K. Smith"         → last-name = "Smith"         ❌ (không có dấu phẩy)
```

**Fix proposal (tuần 4–5):** Tách `matching/author_parser.py` chuẩn hoá last-name + initials + full-name, có test cho 6–8 biến thể phổ biến.

### 1.2 ❌ `datetime.utcnow()` deprecated (Python 3.14)

```
DeprecationWarning: datetime.datetime.utcnow() is deprecated
```

**Vị trí:** `src/integrity_checker/pipeline/integrity_pipeline.py:178`.

**Fix:** Đổi sang `datetime.now(timezone.utc)`.

### 1.3 ⚠️ `pytest` không nhận `asyncio_mode = "auto"` config option

```
PytestConfigWarning: Unknown config option: asyncio_mode
```

**Fix:** Cài `pytest-asyncio` rồi đảm bảo `[tool.pytest.ini_options]` có đúng format.

### 1.4 ⚠️ SwigPyObject/SwigPyPacked deprecation warning từ PyMuPDF

```
DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
```

**Fix:** Bỏ qua — warning từ PyMuPDF upstream, không ảnh hưởng logic.

### 1.5 ⚠️ FastAPI TestClient + httpx deprecation warning

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated
```

**Fix:** Chuyển sang `httpx2` khi stable. Hiện tại bỏ qua.

### 1.6 ❌ `CISComponents.in_text_bib_consistency` và `format_consistency` đang là STUB

**Vị trí:** `src/integrity_checker/logic/cis.py:78, 81`.

**Hiện tại:**
```python
in_text_bib_consistency = 0.8 if n > 0 else 0.0   # placeholder
format_consistency = 0.85 if n > 0 else 0.0       # placeholder
```

**Vấn đề (theo v1.2 §3.9):** Hai thành phần này phải được tính từ module `linking/` (bidirectional linker) và `StyleDetector` (style profile) thật, không phải constant. Tổng trọng số của 2 stub này = **35%** CIS — đang là "ảo".

**Fix:** Triển khai tuần 6–7 cho linker, tuần 12–13 cho CIS.

### 1.7 ⚠️ Output schema không tách integrity vs source

**Vấn đề:** Hiện `CitationVerdict` chỉ chứa 1 nhãn (`ValidationLabel`) cho 1 citation. Theo v1.2 §3.2.2, phải tách thành `CitationMappingStatus` (integrity) + `ValidationLabel` (source) — vì `MISSING_REFERENCE` không phải hallucination và `SUSPECTED_HALLUCINATION` không phải lỗi sử dụng.

**Fix:** Mở rộng `models/validation.py` (tuần 6) và schema trả về của pipeline.

---

## 2. TODOs theo kế hoạch 18 tuần (v1.2 §5.2)

> Mỗi mục có ghi `[BLOCKER]` (chặn end-to-end) / `[MILESTONE]` (mốc nghiệm thu) / `[NICE]` (chỉnh trang).

### 2.1 Tuần 1–2 — Khảo sát (đã chốt scope, đang thực hiện)

- [BLOCKER] **[NOW]** Cập nhật 4 file: `README.md`, `KNOWN_ISSUES_AND_TODO.md`, `DEVELOPER_QUICKSTART.md`, `configs/config.example.yaml` cho khớp v1.2. _(đang làm)_
- [BLOCKER] **[NOW]** Viết `docs/CHANGES_VS_V1.1.md` để GVHD thấy rõ đã đối chiếu những gì.
- [BLOCKER] **[NOW]** Literature matrix v1.2 (style families, taxonomy, định nghĩa "dư thừa", kiến trúc 5 tầng).
- [MILESTONE M1] GVHD chốt phạm vi, 2 lớp taxonomy, dữ liệu và tiêu chí nghiệm thu.

### 2.2 Tuần 3–5 — Dữ liệu

- [BLOCKER] Mở rộng `data/ground_truth/gold_dataset.json` lên **3 mức nhãn**:
  - **Mức 1 (document)**: style profile (APA-like / IEEE-like / MIXED / UNKNOWN) + confidence + evidence.
  - **Mức 2 (span + link)**: mỗi in-text span (raw, page, section, context, bounding box) + `CitationMappingStatus` (7 trạng thái) + `CitationLink` (occurrence_id, reference_id, conf, method).
  - **Mức 3 (source)**: mỗi reference entry có nhãn 1 trong 4 nhãn + record chuẩn + evidence URL + ngày kiểm tra + lý do.
- [BLOCKER] Viết `annotation_guideline_v2.md` tích hợp **5 trạng thái mapping** + **4 nhãn nguồn** + **4 style label** + 6–10 edge case (citation gộp, 2024a/2024b, table-marker giả, họ 2 từ "van der Berg", DOI bị wrap, v.v.).
- [BLOCKER] Pilot 30–50 tiểu luận mẫu thật đã ẩn danh.
- [BLOCKER] 2 SV cùng annotate 100 citation → Cohen's kappa / Krippendorff's alpha target ≥ 0.7.
- [BLOCKER] Train/val/test split **theo tiểu luận** (không phải theo citation) để tránh rò rỉ nguồn lặp.
- [BLOCKER] Khóa test set trước khi tối ưu threshold, trọng số, rule.
- [NICE] Hypothesis property-based test cho parser.

### 2.3 Tuần 6–7 — Full-text audit (Tầng 1 + Tầng 2)

> **Tiến độ 2026-08-17:** Tuần 6 hoàn thành (SectionSegmenter, AuthorParser, GROBID adapter). Tuần 7 (StyleDetector) hoàn thành. ReferenceListParser mở rộng (APA + IEEE + Vancouver + title + numeric_index + year_suffix + order_index) pass 15/17 — 2 test fail tracked backlog #18. `linking/` package chưa scaffold (chuyển tuần 8–9 hoặc mở task riêng).

- [x] **Tạo `extraction/section_segmenter.py`** (2026-08-10): phân vùng body / bibliography / appendix / footnote / figure caption. 15/15 unit tests pass. Hỗ trợ header detection cho EN + VI + ZH (參考文獻 / Tài liệu tham khảo).
- [x] **Tạo `matching/author_parser.py`** (2026-08-12): chuẩn hoá last-name + initials + full-name + Dutch particles (`van der`, `de la`) + Vietnamese (Nguyễn Văn A) + suffixes (Jr/III). 27/27 unit tests pass. Xem 1.1.
- [x] **Tạo `extraction/grobid_parser.py`** (2026-08-15): TEI XML parser (defusedxml chống XXE) + HTTP client injectable + SHA256 cache + JSON serialize/deserialize. 15/15 unit tests pass. Docker adapter thật (week 8 task riêng).
- [x] **Tạo `extraction/style_detector.py`** (2026-08-17): document-level profile (APA-like / IEEE-like / MIXED / UNKNOWN + confidence + features + ratios + explanation). 12/12 unit tests pass.
- [x] **Mở rộng `extraction/reference_parser.py`** (2026-08-13): APA + IEEE + Vancouver parsers, extract `title` + `title_normalized` + `numeric_index` + `year_suffix` + `order_index`. 15/17 unit tests pass — 2 fail (Dutch + 2-line) tracked #18.
- [BLOCKER] **Tạo `linking/` package** (chưa bắt đầu — task tách riêng):
  - `linking/statuses.py` — enum `CitationMappingStatus` (7 trạng thái) + `STYLE_INCONSISTENT`.
  - `linking/citation_linker.py` — bidirectional linker (in-text ↔ reference entry).
  - `linking/duplicate_detector.py` — exact DOI/arXiv → normalized title + author + year + threshold cẩn trọng.
  - `linking/__init__.py`.
- [BLOCKER] **Tạo `extraction/document_parser.py`** (chưa bắt đầu) — orchestrator: PDF → muPDF text + GROBID TEI → fused Document. Có thể tận dụng GROBID output để bypass 2 ReferenceListParser edge cases.
- [BLOCKER] **GROBID Docker adapter thật** — phần trên (grobid_parser.py) chỉ wrap HTTP. Cần viết script `scripts/grobid_docker_setup.sh` (theo v1.2 §5.2).
- [NICE] Mở rộng `extraction/text_preprocessor.py` để sửa wrap dòng cho DOI, URL, số thứ tự, ký tự gạch nối. (Hiện có light normalize trong ReferenceListParser workaround.)
- [MILESTONE M3] PDF → style profile → citation graph → candidate top-K chạy end-to-end trên bộ mẫu đầu tiên. (Phụ thuộc linking/.)

### 2.4 Tuần 8–9 — Retrieval (Tầng 3)

- [BLOCKER] **Điền HTTP call thật** cho 4 connector (đã có interface đúng):
  - `retrieval/crossref_client.py`: `GET /works/{doi}` + `GET /works?query.bibliographic=...`.
  - `retrieval/openalex_client.py`: `GET /works?search=...&filter=...`.
  - `retrieval/semantic_scholar_client.py`: `GET /paper/search?query=...&fields=...`.
  - `retrieval/arxiv_client.py`: `arxiv.Search(query=..., max_results=5)` qua SDK.
- Hiện tại cả 4 đều stub → pipeline rơi vào nhánh `UNRESOLVED`. Đây là lúc verdict bắt đầu phân hóa thật sự.
- [BLOCKER] Tenacity retry + exponential backoff với riêng từng nguồn.
- [BLOCKER] Cache key bao gồm `source_name` để tránh trộn nhầm Crossref vs OpenAlex.
- [BLOCKER] Health check + `UNRESOLVED` khi `sources_failed` chiếm đa số.

### 2.5 Tuần 10–11 — Matching (Tầng 4)

- [BLOCKER] Author normalization (last-name canonical, diacritics, "van der" multi-token).
- [BLOCKER] Venue normalization (viết tắt vs. đầy đủ).
- [BLOCKER] Source consensus (đếm số nguồn độc lập trả về cùng DOI/title-author-year).
- [BLOCKER] Fuzzy threshold tuning trên validation set.
- [BLOCKER] Build B0–B5 baselines (xem 2.7).

### 2.6 Tuần 12–13 — Logic (Tầng 4 + Tầng 5)

- [BLOCKER] Mở rộng `logic/rules.py` thêm rule cho `AMBIGUOUS_MAPPING`, `STYLE_INCONSISTENT`, **DOMAIN-EXCEPTION** (URL lỗi nhưng scholarly record tồn tại → giữ nhãn tồn tại + `BROKEN_LINK`).
- [BLOCKER] Abstention band tối ưu (ECE-driven).
- [BLOCKER] Calibration (Brier, ECE, coverage-accuracy).
- [BLOCKER] **Sửa `logic/cis.py`**:
  - Weights `35/25/25/10/5` (đã cập nhật trong config).
  - Hai thành phần `in_text_bib_consistency` + `format_consistency` phải **real** (tính từ linker + StyleDetector).
  - Tách output schema: `CitationMappingStatus` (integrity) + `ValidationLabel` (source) — xem 1.7.
- [BLOCKER] `ExplanationGenerator` sinh lý do bằng tiếng Việt có cấu trúc (rule + field + score).
- [MILESTONE M4] Có mapping statuses, 4 nhãn nguồn, evidence, abstention + validation report.

### 2.7 Tuần 16–17 — Baselines + Metrics (đã chốt trong v1.2)

| Baseline | Mô tả |
|---|---|
| **B0** | Pattern-only audit — Regex style + exact author-year/index + 1 chiều. |
| **B1** | Link/DOI only — chỉ HTTP/DOI resolution. |
| **B2** | Single-source top-1 — chỉ lấy kết quả đầu tiên từ Crossref / 1 nguồn chính. |
| **B3** | Fuzzy matching — weighted title-author-year, không embedding + không symbolic. |
| **B4** | Embedding only — cosine similarity tiêu đề, chọn top-1. |
| **B5** | ML classifier — Logistic Regression / XGBoost trên tập feature. |
| **Proposed** | Full-text style inference + bidirectional linking + multi-source + neural/statistical similarity + symbolic rules + abstention. |

**Metrics cần đo (per v1.2 §3.10.2):**

| Module | Metric |
|---|---|
| Style detection | Document-level Accuracy, Macro-F1 |
| In-text extraction | Span-level P/R/F1 |
| Citation-reference linking | Link Accuracy/F1; per-status P/R/F1 |
| Reference extraction | Boundary F1; field-level P/R/F1 |
| Candidate retrieval | Recall@1, Recall@5, MRR |
| Nguồn phân loại | Per-class P/R/F1, Macro-F1, confusion matrix |
| Confidence/abstention | Brier, ECE, coverage-accuracy |
| CIS | Spearman / weighted kappa / MAE với rubric GVHD |
| Hệ thống | Latency/PDF, API error rate, cache hit rate |
| Usability | Thời gian task, SUS, bảng hỏi 5–7 tiêu chí |

### 2.8 Tuần 14 — IAA

- 2 SV cùng annotate 100 citation (đã lên lịch ở tuần 3–5, đo ở đây).
- Cohen's kappa / Krippendorff's alpha target ≥ 0.7.
- `data/ground_truth/iaa_template.csv` hiện tại chỉ là stub.

### 2.9 Tuần 14–15 — Web UI

- [BLOCKER] Style profile view (badge + conf + features hỗ trợ).
- [BLOCKER] Citation graph view (2 chiều) + filter theo `MISSING/UNCITED/MISMATCH/DUPLICATE/AMBIGUOUS`.
- [BLOCKER] Override mapping/labels UI (giảng viên sửa → log vào `audit_logs`).
- [BLOCKER] Evidence drawer mở rộng: opening record từ Crossref/OpenAlex/S2/arXiv + source provenance + thời điểm kiểm tra.
- [BLOCKER] Export PDF/CSV/JSON — JSON phải chứa 2 lớp output tách rời (integrity vs source).
- [NICE] `npx shadcn@latest add button card table dialog` để sinh components (placeholder hiện tại).
- [NICE] `react-dropzone` đang thiếu trong `package.json` — cần `npm install` trước khi dev.
- [MILESTONE M5] Web MVP chạy bằng Docker; demo không phụ thuộc thao tác thủ công ẩn.

### 2.10 Tuần 17 — Error analysis + usability

- [BLOCKER] Error analysis theo từng mô-đun (extraction / linking / retrieval / classification).
- [BLOCKER] Test với 3–5 giảng viên (nếu tiếp cận được) — thời gian task, SUS, góp ý.
- [MILESTONE M6] Đóng băng kết quả, hoàn thành baseline/ablation/error analysis.

---

## 3. Re-scoped từ v1.1 (nay đã vào MVP)

| Thứ cũ v1.1 | Nay trong v1.2 |
|---|---|
| GROBID là "mở rộng tương lai" | **Must-have cho MVP** (§3.4) — cần Docker adapter + GROBID client. |
| Đọc PDF chỉ để trích citation | **Đọc toàn văn, phân vùng body/bibliography** (§3.4). |
| Chỉ verify reference entry | **Có 2 lớp output** (integrity + source) (§3.2.2). |
| Style detection ẩn / không bắt buộc | **Document-level style profile + confidence** (§3.5). |
| Mapping một chiều hoặc không có | **Bidirectional linking + 7 trạng thái** (§3.5). |
| "Dư thừa" = mặc định cứng | **Định nghĩa lại**: `UNCITED ∪ DUPLICATE`; KHÔNG coi trích nhiều lần là dư thừa. |
| CIS weights 45/25/15/10/5 | **35/25/25/10/5** (§3.9). |
| 2 CIS component là stub | **Phải tính thật** từ linker + style detector (§3.9). |
| Gold set 1 mức (source label) | **3 mức**: style / span-link / source (§3.2). |
| Baselines mơ hồ | **B0–B5 chốt cụ thể** (§3.10.1). |
| Roadmap 1A/1B (citation-only) | **Roadmap 18 tuần chốt mốc M1–M7** (§5.2). |

---

## 4. Caveats kỹ thuật — refactor sau

### 4.1 PDF parsing
- ⚠️ `BasePDFParser.is_supported()` chỉ check extension `.pdf` — chưa check magic bytes `%PDF-`.
- ⚠️ `fallback_to_ocr: false` — nếu PDF là scan (không có text layer), pipeline fail im lặng. Spec v1.2 ghi rõ:** scan PDF = unsupported trong MVP**, OCR là mở rộng.
- ⚠️ Encrypted PDF chưa handle — sẽ raise exception từ PyMuPDF.
- ⚠️ Khi có GROBID (tuần 6–7), cần cache kết quả GROBID theo `sha256(file)` để tránh gọi lại.

### 4.2 Retrieval
- ⚠️ Retry logic chưa có — khi API timeout/5xx sẽ fail. Cần `tenacity` retry exponential backoff.
- ⚠️ Cache key hiện chỉ dùng SHA256 của raw text. Chưa truyền `source_name` → Crossref và OpenAlex cùng return có thể đụng key.
- ⚠️ Rate limiter dùng spacing cố định, chưa sliding-window → sẽ vỡ rate limit nếu gọi đột biến.

### 4.3 Logic
- ⚠️ **`NeuroSymbolicChecker` thiếu classifier ML** (đã đánh dấu TODO tuần 12–13).
- ⚠️ Story abstraction `best_candidate()` chỉ dùng `max(confidence)` — không tính consensus. Cần thêm `consensus_count()` vào ranking.
- ⚠️ Calibration (`calibration.py`) hiện stub — cần Brier + ECE thật.

### 4.4 Pipeline
- ⚠️ `asyncio.run` trong sync wrapper — nếu gọi `pipeline.run()` từ trong FastAPI endpoint (đã có event loop), sẽ raise. Cần detect + dùng `loop.run_until_complete` hoặc `loop.run_in_executor`.
- ⚠️ Cần thêm module `linking/` orchestrator (chưa có) để pipeline gọi sau `extraction/` trước `retrieval/`.

### 4.5 DB
- ⚠️ Không có Alembic migrations — dùng `Base.metadata.create_all()` lúc startup. OK cho MVP, schema đổi sẽ khó migrate.
- ⚠️ SQLite only — production cần PostgreSQL. Settings đã có `database.url` configurable.
- ⚠️ `audit_logs` table có nhưng chưa có API để log override mapping/labels.

### 4.6 Web
- ⚠️ shadcn components chưa được generate thật (`src/components/ui/placeholder.ts`).
- ⚠️ `useEssayAnalysis` hook không có polling — chỉ fetch 1 lần.
- ⚠️ `VITE_API_BASE_URL` mặc định = `/api` (qua Vite proxy) — OK cho dev, cần override cho prod.
- ⚠️ CSS colors hiện đang hardcode theo 4 nhãn `ValidationLabel` — cần thêm bảng màu cho 7 trạng thái `CitationMappingStatus`.

---

## 5. Out-of-scope (v1.2, ghi rõ để tránh scope creep)

- ❌ Chấm điểm content / organization / language / vocabulary / mechanics.
- ❌ AES rubric (QWK, holistic scoring).
- ❌ Phát hiện đạo văn.
- ❌ Phát hiện toàn bộ văn bản do AI tạo.
- ❌ **Tự động kết luận gian lận học thuật** — hệ thống là decision-support.
- ❌ **Claim-level verification toàn diện** — chỉ kiểm tra author/year/number/index, KHÔNG kiểm tra câu văn có được nguồn hỗ trợ về ngữ nghĩa.
- ❌ **Phán xét việc trích cùng một nguồn nhiều lần là "dư thừa"** — chỉ `UNCITED` + `DUPLICATE` mới là dư thừa.
- ❌ OCR scanned PDF (mở rộng tương lai).
- ❌ Sách / ISBN (mở rộng tương lai).
- ❌ Highlight trực tiếp lên PDF (mở rộng — mở đúng trang + bảng page/context là đủ cho MVP).
- ❌ Google Scholar / SerpAPI (bị loại).
- ❌ **Auto-grade toàn bài tiểu luận** (dù GVHD có nói lỏng lẻo trong v1.1, v1.2 đã chốt rõ: 3 lớp kiểm tra, không chấm tổng).

---

## 6. Testing gaps

### 6.1 Tests chưa có — update 2026-08-17

| File test | Status | Note |
|---|---|---|
| `tests/unit/test_style_detector.py` | ✅ DONE (2026-08-17) | 12/12 pass — APA / IEEE / MIXED / UNKNOWN / diacritics / multi-index |
| `tests/unit/test_section_segmenter.py` | ✅ DONE (2026-08-10) | 15/15 pass — body / bib / appendix / footnote / multi-style header EN+VI+ZH |
| `tests/unit/test_grobid_parser.py` | ✅ DONE (2026-08-15) | 15/15 pass — header / authors / abstract / sections / citations / bibliography / serialize round-trip / XXE entity attack |
| `tests/unit/test_author_parser.py` | ✅ DONE (2026-08-12) | 27/27 pass — APA / multi-author / Dutch / Vietnamese / suffix / full name |
| `tests/unit/test_reference_parser.py` | ⚠️ PARTIAL (2026-08-13) | 15/17 pass — 2 fail tracked #18 |
| `tests/unit/test_citation_linker.py` | ❌ NOT STARTED | Phụ thuộc linking/ package (chưa scaffold) |
| `tests/unit/test_duplicate_detector.py` | ❌ NOT STARTED | Phụ thuộc linking/ package |
| `tests/unit/test_extraction_preprocessor.py` | ❌ NOT STARTED | |
| `tests/unit/test_semantic_matcher.py` | ❌ NOT STARTED | Tuần 10–11 |
| `tests/unit/test_retrieval_orchestrator.py` | ❌ NOT STARTED | Tuần 8–9 |
| `tests/unit/test_consensus.py` | ❌ NOT STARTED | Tuần 10–11 |
| `tests/unit/test_calibration.py` | ❌ NOT STARTED | Tuần 12–13 |
| `tests/unit/test_explanation.py` | ❌ NOT STARTED | Tuần 12–13 |
| `tests/unit/test_db_repository.py` | ❌ NOT STARTED | |
| `tests/integration/test_full_pdf_pipeline_v12.py` | ❌ NOT STARTED | Sau linking/ + retrieval/ |
| `tests/integration/test_api_upload.py` | ❌ NOT STARTED | |
| `tests/integration/test_baselines_b0_b5.py` | ❌ NOT STARTED | Tuần 16–17 |

**Tổng test count (2026-08-17):** 84 unit tests pass / 2 deferred. Xem §9 lịch sử.

### 6.2 Coverage tụt so với v1.1
- `pipeline/integrity_pipeline.py`: chỉ test happy path. Cần test:
  - 0 citations extracted
  - 1 citation duy nhất
  - Toàn bộ API fail
  - `MISSING_REFERENCE` & `UNCITED_REFERENCE` realistic
- `db/repository.py`: chưa có test thật.

### 6.3 Property-based tests
- Có thể thêm `hypothesis` library để test parser với input random.

### 6.4 IAA measurement
- File `data/ground_truth/iaa_template.csv` hiện stub — cần chạy thật ở tuần 14.

---

## 7. Security / privacy notes

### 7.1 Quyền riêng tư
- ⚠️ **Tiểu luận SV là dữ liệu nhạy cảm**. Mặc dù đề cương ghi "đã được ẩn danh", vẫn cần:
  - Không commit essay thật vào git.
  - Không gửi essay qua API bên thứ ba nếu không cần thiết (v1.2 §3.4 đã chốt: **không gửi toàn văn ra scholarly APIs**, chỉ gửi truy vấn thư mục tối thiểu sau khi đã phân vùng + ẩn danh).
  - Cache TTL 24h — sau 24h sẽ bị xoá.
- ⚠️ **Gold dataset cũng có thể chứa thông tin nhạy cảm** — cần review trước khi công khai.
- ⚠️ **Hash tên tệp** (filename hash) trước khi lưu DB.
- ⚠️ **Tách kho tệp gốc khỏi dataset nghiên cứu**; dataset chia sẻ chỉ chứa marker + reference + mã liên kết + ngữ cảnh tối thiểu đã được phép.

### 7.2 API keys
- ⚠️ `S2_API_KEY` chỉ optional, không commit.
- ⚠️ `CONTACT_EMAIL` đang mặc định `student@tdtu.edu.vn` — đổi sang email thật của nhóm trước khi demo.

### 7.3 Disclaimer bắt buộc
- ⚠️ Mọi page web PHẢI có `<DecisionSupportDisclaimer />`.
- ⚠️ Mọi report export PHẢI có disclaimer đầu trang (đã có trong `_json_response` và `_csv_response`).
- ⚠️ FastAPI `/api/health` PHẢI trả disclaimer (đã có).
- ⚠️ **Phải ghi rõ trong UI**: "Không tự động kết luận gian lận" + "SUSPECTED_HALLUCINATION chỉ là suspect, GVHD là người quyết định cuối".

### 7.4 Security findings (từ automated review 2026-07-26) — KHÔNG fix trong skeleton phase

> Background security review phát hiện 8 issues ở mức MEDIUM/HIGH. **Chưa fix** theo yêu cầu của user (skeleton — security chưa trong scope MVP). Cần xử lý **trước khi deploy production**, ước lượng 1–2 tuần.

| Severity | File | Issue | Fix proposal |
|---|---|---|---|
| CRITICAL | `api/routes/essays.py` | Missing authz — không có authentication, ai cũng upload được | Thêm JWT bearer auth, tag `EssayRecord` với `user_id`, check ownership |
| HIGH | `api/main.py` | CORS misconfig — `allow_origins=["*"]` + `allow_credentials=True` | Restrict allowlist hoặc drop credentials |
| HIGH | `api/routes/essays.py` | Resource exhaustion — không cap file size, không validate PDF magic bytes | Streaming size cap (50MB), check `%PDF-` header |
| HIGH | `api/routes/report.py` | CSV injection — `citation_raw` chứa `=+-@` → Excel thực thi formula | Prepend `'` cho cell bắt đầu bằng `=+-@\t\r` |
| HIGH | `api/routes/report.py` | Header injection — `filename` user-controlled vào `Content-Disposition` | Sanitize filename ASCII-only + RFC 5987 `filename*=UTF-8''...` |
| HIGH | `api/deps.py` | Cache poisoning — `get_pipeline()` tạo mới mỗi request | Singleton module-level, share `httpx.AsyncClient` |
| MEDIUM | `api/routes/essays.py` | No validation: chỉ check extension, không check magic bytes | Verify `%PDF-` magic header trước khi write |
| MEDIUM | `api/routes/essays.py` | No semaphore — concurrent uploads có thể OOM | `asyncio.Semaphore` + `ThreadPoolExecutor` bounded |

**Caveats:**
- Hệ thống MVP chỉ dùng **trong nội bộ nhóm TDTU** — authentication thật (qua SSO TDTU) sẽ tích hợp ở tuần 14–15 khi deploy.
- `findings` này đã được ghi nhận, không bỏ qua. Sẽ address trước khi production.

---

## 8. Dependencies — pinned versions cần update

| Package | Pinned | Lưu ý |
|---|---|---|
| `pydantic` | `>=2.6,<3` | OK |
| `pydantic-settings` | `>=2.2,<3` | OK |
| `PyMuPDF` | `>=1.24,<2` | Đã test OK trên Python 3.14 |
| `pdfplumber` | `>=0.10,<1` | OK |
| `fastapi` | `>=0.110,<1` | OK |
| `SQLAlchemy` | `>=2.0,<3` | OK |
| `sentence-transformers` | `>=2.6,<4` | Chưa test — cần Python ≥3.10 |
| `arxiv` | `>=2.0,<3` | OK |
| `rapidfuzz` | `>=3.6,<4` | OK |
| `httpx` | `>=0.27,<1` | Có deprecation warning với starlette.testclient |
| `grobid-client` | TBD | **Cần thêm** — Docker compose cho GROBID service |
| `tenacity` | TBD | **Cần thêm** — retry + exponential backoff |

---

## 9. Lịch sử thay đổi

| Ngày | Thay đổi |
|---|---|
| 2026-07-26 | Skeleton v1.1 — tạo 115 files. 29/29 unit tests pass, 8/8 integration tests pass. CLI demo chạy end-to-end. CIS = 45.5/100 (vì API stub → toàn UNRESOLVED). |
| 2026-07-26 | Fix bug `to_search_query()` cho APA format. Fix `out_of_scope` config shape (YAML list). |
| 2026-08-03 | **Re-scope sang v1.2** (sau khi chốt với GVHD). README / KNOWN_ISSUES / Quickstart / config được đồng bộ sang v1.2: full-text + GROBID, style detection, bidirectional linking, 7 trạng thái mapping, 4 nhãn nguồn, CIS weights 35/25/25/10/5, 18-tuần roadmap. Chưa có code thay đổi ở phase này. |
| 2026-08-10 | **Tuần 6 — `extraction/section_segmenter.py`**: phân vùng body/bibliography/appendix/footnote, multi-style header EN+VI+ZH. 15/15 unit tests pass. |
| 2026-08-12 | **Tuần 6 — `matching/author_parser.py`**: chuẩn hoá last-name + initials + full-name + Dutch particles + Vietnamese + suffixes. 27/27 unit tests pass. Fix §1.1. |
| 2026-08-13 | **Tuần 6 — `extraction/reference_parser.py` mở rộng**: APA + IEEE + Vancouver parsers, title + title_normalized + numeric_index + year_suffix + order_index. 15/17 unit tests pass — 2 fail (Dutch + 2-line) tracked #18. |
| 2026-08-15 | **Tuần 6 — `extraction/grobid_parser.py`**: TEI XML parser (defusedxml XXE-safe) + HTTP client injectable + SHA256 cache + JSON serialize/deserialize. 15/15 unit tests pass. |
| 2026-08-17 | **Tuần 7 — `extraction/style_detector.py`**: document-level profile (APA-like / IEEE-like / MIXED / UNKNOWN) + confidence + features + ratios + explanation. 12/12 unit tests pass. |
| 2026-08-17 | **Tổng kết tuần 6–7**: 84 unit tests pass / 2 deferred. 5 commit, 4 module mới + 1 mở rộng. Cập nhật tài liệu (.md files) + push GitHub. |

---

## 10. Action items ngay tuần này

**Sinh viên (thứ tự ưu tiên) — 2026-08-17:**

1. Đọc `README.md` (v1.2) + `docs/CHANGES_VS_V1.1.md` + file này.
2. `make setup` → `make sample` → `make demo` → `make test` — xác nhận skeleton vẫn chạy.
3. ✅ Tuần 6 hoàn thành: SectionSegmenter + AuthorParser + ReferenceListParser (mở rộng) + GROBID adapter.
4. ✅ Tuần 7 hoàn thành: StyleDetector.
5. ⏳ Tuần 8 — scaffold `linking/` package (statuses + citation_linker + duplicate_detector) — **chưa bắt đầu**.
6. ⏳ Backlog #18 — ReferenceListParser Dutch + 2-line APA split (mình đã thử nhiều heuristic regex, đều fail — có thể cần approach mới dựa trên GROBID output hoặc citation graph).

**GVHD (cần xin ý kiến) — vẫn pending:**

- Tên đề tài tiếng Việt/Anh và cách dùng thuật ngữ "ảo giác".
- MVP ngoài APA-like / IEEE-like có cần hỗ trợ style families nào không (Chicago, Harvard, Vancouver — mình đã implement Vancouver parser, có thể mở rộng sang Chicago nếu cần).
- Có chấp nhận `MIXED` / `UNKNOWN` như cơ chế an toàn không.
- Nhóm được tiếp cận bao nhiêu tiểu luận và quy trình ẩn danh / lưu trữ.
- Định nghĩa "dư thừa" = `UNCITED ∪ DUPLICATE` đã OK chưa.
- CIS có cần so sánh với điểm thật hay chỉ là thống kê hỗ trợ.
- Tiêu chí tối thiểu về accuracy, tốc độ, số mẫu, usability.

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh
**Đề cương:** v1.2 đã chốt 2026-08-03
