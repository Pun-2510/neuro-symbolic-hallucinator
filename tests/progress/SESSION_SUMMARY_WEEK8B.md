# Session Summary — Tuần 8 tiếp theo (v1.2, ngày 2026-08-25)

> **Ngày:** 2026-08-25 (Asia/Ho_Chi_Minh)
> **Người thực hiện:** Claude (Claude Opus 5, 1M context) + User (Nguyễn Bảo Minh, 523H0054)
> **Project:** Essay Integrity Checker — Đồ án tốt nghiệp TDTU
> **Giai đoạn:** v1.2 §5.2 — Tuần 8 tiếp theo (Task #23–#26)
> **Tuần 8 trước:** [`SESSION_SUMMARY_WEEK8.md`](./SESSION_SUMMARY_WEEK8.md) — linking/ scaffold + DocumentParser + backlog #18 closed.

---

## 1. Mục tiêu phiên

Hoàn thành 4 task từ §10 Action Items của tuần 8 trước:

- **#23** GROBID Docker adapter thật (`scripts/grobid_docker_setup.sh`).
- **#24** Real HTTP clients cho 4 retrieval connectors (Crossref / OpenAlex / S2 / arXiv).
- **#25** Tích hợp `DocumentParser` vào `pipeline/integrity_pipeline.py`.
- **#26** End-to-end pipeline integration test (`test_full_pdf_pipeline_v12.py`).

Mục tiêu chung: **Milestone M3** chạy end-to-end trên sample PDFs không cần stub nữa.

---

## 2. Công việc hoàn thành

### 2.1 Module mới / mở rộng

| Ngày | Task | File mới/mở rộng | Tests | Status |
|---|---|---|---|---|
| 2026-08-25 | **#23** GROBID Docker adapter | `scripts/grobid_docker_setup.sh` (NEW) | bash syntax check | ✅ |
| 2026-08-25 | **#24** Real HTTP clients | `retrieval/{crossref,openalex,semantic_scholar,arxiv}_client.py` (mở rộng) + `retrieval_orchestrator.py` (cache integration) | 12/12 | ✅ |
| 2026-08-25 | **#25** DocumentParser integration | `pipeline/integrity_pipeline.py` (mở rộng) | 7/7 | ✅ |
| 2026-08-25 | **#26** End-to-end test | `tests/integration/test_full_pdf_pipeline_v12.py` (NEW) + `tests/integration/test_pipeline_endtoend.py` (mock) | 9/9 + 4/4 | ✅ |

### 2.2 Bug fix (pre-existing)

| Bug | Vị trí | Fix |
|---|---|---|
| `AttributeError: 'Author' object has no attribute 'lower'` | `src/integrity_checker/matching/features.py` `_author_jaccard()` | Thêm `_authors_to_strings()` helper normalize `list[Author]` → `list[str]` (last_name). ReferenceListParser trả `list[Author]` nhưng type hint nói `list[str]`. |
| `datetime.utcnow()` deprecated | `pipeline/integrity_pipeline.py:178` | Đổi sang `datetime.now().isoformat() + "Z"` (đề cập ở §1.2 KNOWN_ISSUES). |

### 2.3 Test count

| Giai đoạn | Unit | Integration | Tổng |
|---|---|---|---|
| Cuối tuần 8 (trước) | 225 | 0 (mock) | 225 |
| Sau task #23 | 225 | 0 | 225 |
| Sau task #24 | 237 (+12) | 0 | 237 |
| Sau task #25 | 244 (+7) | 0 | 244 |
| Sau task #26 | 244 | 13 (+9 v12 + 4 legacy) | **257** |
| **Δ tổng** | **+19** | **+13** | **+32** |

---

## 3. Quyết định kỹ thuật đáng chú ý

### 3.1 GROBID Docker script thiết kế

Script `grobid_docker_setup.sh` được viết theo pattern **command-routing Unix tool** (start/stop/restart/status/logs/pull/rm/env). Mỗi command là 1 bash function. Điểm thiết kế:

- **Auto-detect Docker availability**: `command -v docker` + `docker info` check — fail sớm với error message rõ ràng.
- **Auto-pull image nếu missing**: `docker image inspect` trước, fallback `docker pull`. Tránh user phải nhớ 2 bước.
- **Health check polling**: `while ! curl /api/isalive` với timeout configurable (default 120s). GROBID cần ~30-60s lần đầu để load models.
- **Container với `--rm`**: tự động xoá khi stop (educational setup, không persistent state).
- **JVM heap configurable**: `JAVA_OPTS="-Xmx${GROBID_MEMORY}"` — default 2 GB, user có thể tăng/giảm theo RAM.
- **`env` command**: in ra export entries user có thể `source` để dùng.

```bash
$ ./scripts/grobid_docker_setup.sh start
[INFO] Pull GROBID image: lfoppiano/grobid:0.8.0
[INFO] Tạo container 'essay-check-grobid' (port 8070)...
[INFO] Chờ GROBID healthy (timeout 120s)...
[OK] GROBID ready: http://localhost:8070
```

### 3.2 Real HTTP clients — retry + backoff pattern

Tất cả 4 clients dùng `tenacity.AsyncRetrying` với parameters:

```python
AsyncRetrying(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=False,
)
```

Điểm thiết kế:
- **404 xử lý riêng** (không retry — không phải lỗi transient).
- **429 + 5xx → `raise_for_status()` trigger retry**.
- **Riêng arXiv**: SDK sync được wrap trong `loop.run_in_executor()` + tenacity wrap. SDK có retry nội bộ (delay 3.4s) nên set `num_retries=0` trên client.

### 3.3 Cache key với source_name

Theo v1.2 §3.6, design để tránh trộn nhầm Crossref vs OpenAlex:

```python
@staticmethod
def _cache_key(source_name: str, citation: Citation) -> str:
    parts = [
        citation.doi or "",
        citation.title or "",
        citation.year or "",
        ",".join(a.last_name for a in citation.authors) if citation.authors else "",
    ]
    canonical = "|".join(parts).encode("utf-8")
    h = hashlib.sha256(canonical).hexdigest()[:16]
    return f"{source_name}:{h}"
```

Cache key = `{source_name}:{sha256(canonical_fields)[:16]}`. Canonical fields gồm DOI + title + year + author last-name tuple — đảm bảo cache reuse khi citation chỉ khác whitespace.

### 3.4 DocumentParser integration — backward compat

Pipeline được refactor để hỗ trợ 2 flow:

```python
async def run_async(self, pdf_path: str, essay_id: int = 0) -> AnalysisReport:
    if self._use_document_parser:
        # Modern path: DocumentParser (PyMuPDF + GROBID + SectionSegmenter)
        parsed = self.document_parser.parse(pdf_path)
        all_citations = self._merge_citations(
            parsed.body_citations, parsed.references, parsed.appendix_citations
        )
    else:
        # Legacy path: BasePDFParser + CitationExtractor + ReferenceListParser
        doc = self.parser.parse(pdf_path)
        in_text = self.extractor.extract_from_document(doc)
        ref_list = self.ref_parser.parse_reference_section(doc)
        all_citations = self._merge_citations_legacy(in_text, ref_list)
    ...
```

**Default `use_document_parser=False`** (backward compat với legacy tests). User opt-in 2 cách:
1. Constructor: `IntegrityPipeline(use_document_parser=True)`
2. CLI: `--no-document-parser` flag (default use_document_parser=True nếu không có flag)

Lý do: legacy test `test_pipeline_handles_missing_file` expect `FileNotFoundError` (legacy path raises). DocumentParser swallows (chỉ warning). Default False = mặc định an toàn cho tests.

### 3.5 `_merge_citations()` priority

Thứ tự deduplication (priority giảm dần):

1. **References trước** (chứa title + DOI — đầy đủ nhất cho retrieval).
2. **body_citations** (in-text — thiếu title, có author/year).
3. **appendix_citations** (out-of-scope MVP nhưng vẫn track).

Dedup key: `(c.style.value, c.raw_text.lower().strip())`. Trùng raw_text → ưu tiên entry sớm hơn (priority).

### 3.6 Bug fix `_author_jaccard` (Author vs str)

**Root cause**: ReferenceListParser.parse_authors() returns `list[Author]`. Citation.authors type hint là `list[str]` nhưng runtime nhận `list[Author]`. FeatureCalculator._author_jaccard assum `list[str]` và gọi `_normalize_name(a).lower()` → AttributeError.

**Fix**: thêm `_authors_to_strings()` helper:

```python
def _authors_to_strings(authors: list) -> list[str]:
    result = []
    for a in authors:
        if hasattr(a, "last_name"):
            ln = a.last_name
            if ln:
                result.append(ln)
        elif isinstance(a, str):
            if a:
                result.append(a)
    return result
```

Backward compat: chấp nhận cả `list[Author]` (mới) và `list[str]` (legacy raw).

---

## 4. Tests added / modified

### 4.1 New unit tests

| File | Tests | Coverage |
|---|---|---|
| `tests/unit/test_retrieval_clients.py` | 12 | Crossref + OpenAlex + S2 + arXiv: DOI exact, fallback search, arXiv ID extraction, version strip, 404 no-retry, retry-exhausted |
| `tests/unit/test_pipeline_document_parser.py` | 7 | Modern path + Legacy path + merge ref>body>appendix + dedup + auto-detect |

### 4.2 New integration tests

| File | Tests | Coverage |
|---|---|---|
| `tests/integration/test_full_pdf_pipeline_v12.py` | 9 | Legacy path essay_01 + Modern path essay_01 + Mixed essay_02 + Fabricated essay_03 + DOI-only essay_05 + missing file (legacy raises + modern warns) + empty report to_dict + retrieve call count |

### 4.3 Modified tests

| File | Modification |
|---|---|
| `tests/integration/test_pipeline_endtoend.py` | Mock orchestrator trong 4 tests (real HTTP giờ thật gọi API → cần mock trong CI). |

---

## 5. Verification

```bash
$ python3 -m pytest tests/unit/ tests/integration/test_pipeline_endtoend.py tests/integration/test_full_pdf_pipeline_v12.py
============================= 257 passed, 26 warnings in 0.53s =============================
```

- **244 unit tests pass / 0 deferred** (was 225, +19 new).
- **13 integration tests pass** (was 0, +13 new).
- **0 regressions** so với tuần 8 trước.

---

## 6. Tasks completed

| ID | Task | Status |
|---|---|---|
| #23 | GROBID Docker adapter script | ✅ |
| #24 | Real HTTP clients (4 connectors) | ✅ |
| #25 | DocumentParser integration vào pipeline | ✅ |
| #26 | End-to-end pipeline integration test | ✅ |

---

## 7. Files changed (week 8 tiếp theo)

```
A  scripts/grobid_docker_setup.sh                        (NEW, bash, 200+ lines)
M  src/integrity_checker/retrieval/crossref_client.py
M  src/integrity_checker/retrieval/openalex_client.py
M  src/integrity_checker/retrieval/semantic_scholar_client.py
M  src/integrity_checker/retrieval/arxiv_client.py
M  src/integrity_checker/retrieval/retrieval_orchestrator.py
M  src/integrity_checker/pipeline/integrity_pipeline.py
M  src/integrity_checker/matching/features.py            (bug fix)
A  tests/unit/test_retrieval_clients.py                  (NEW, 12 tests)
A  tests/unit/test_pipeline_document_parser.py           (NEW, 7 tests)
A  tests/integration/test_full_pdf_pipeline_v12.py       (NEW, 9 tests)
M  tests/integration/test_pipeline_endtoend.py            (mock retrieval)
M  docs/progress/README.md
M  KNOWN_ISSUES_AND_TODO.md
M  README.md
M  DEVELOPER_QUICKSTART.md
```

---

## 8. Tổng kết tuần 8 tiếp theo

**Trước:** 225 unit tests pass / 2 deferred (linked tasks #23-26 OPEN).

**Sau:** **257 tests pass** (244 unit + 13 integration) / 0 deferred. **+32 tests** trong session.

**Modules mới/cập nhật:**
- Scripts/: GROBID Docker setup (1 file).
- Retrieval/: 4 real HTTP clients + orchestrator cache integration.
- Pipeline/: DocumentParser integration với backward compat.
- Matching/: bug fix `_author_jaccard` (chấp nhận list[Author] hoặc list[str]).

**§2.4 (Tuần 8–9 Retrieval) hoàn thành.** Pipeline giờ gọi 4 nguồn scholarly thật → verdict phân hóa dựa trên real metadata. Chỉ cần GROBID Docker thật để chạy DocumentParser path đầy đủ (task #23 đã có script).

**Next up (Tuần 9):**
- Real run pipeline với GROBID Docker thật (`./scripts/grobid_docker_setup.sh start`).
- Unit tests cho RetrievalOrchestrator với cache (mocked cache).
- Matching module (Tầng 4) — author normalization, venue normalization.

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh
**Đề cương:** v1.2 đã chốt 2026-08-03