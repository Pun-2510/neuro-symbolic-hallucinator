# Known Issues & TODO — Essay Integrity Checker

> **Ngày cập nhật cuối:** 2026-07-26 (Asia/Ho_Chi_Minh)
>
> **Trạng thái project:** Skeleton Phase 1 hoàn tất. Có thể chạy end-to-end trên sample PDF, nhưng **4 API client đều là stub** → verdict toàn UNRESOLVED. Logic Neuro-Symbolic, CIS, regex extraction, FastAPI đều chạy được.

File này liệt kê:

1. **Critical bugs / sai logic** cần fix trước khi dùng thật
2. **Missing implementations** (đã đánh dấu TODO trong code)
3. **Caveats kỹ thuật** (thiết kế hiện tại chưa tối ưu, sẽ refactor sau)
4. **Out-of-scope** (không làm, để tránh scope creep)
5. **Testing gaps** (chỗ chưa có test hoặc coverage thấp)
6. **Security / privacy notes**

---

## 1. Critical bugs / sai logic — fix NGAY (tuần 3)

> Những phát hiện trong lúc smoke-test ngày 2026-07-26.

### 1.1 ❌ `Citation.to_search_query()` lấy last-name sai cho APA format

**Vấn đề:** Logic ban đầu lấy `split()[-1]` (token cuối). Nhưng APA format `"Vaswani, A."` có last-name ở **token đầu**, không phải cuối. Đã fix 1 phần (xử lý có dấu phẩy), nhưng vẫn chưa robust cho các biến thể:

```python
# Chưa xử lý:
# - "Smith, J. K."        → last-name = "Smith"          ✓ handled
# - "Smith, John K."      → last-name = "Smith"          ✓ handled
# - "van der Berg, J."    → last-name = "van der Berg"   ❌ (chỉ lấy "van")
# - "O'Brien, M."         → last-name = "O'Brien"        ✓ handled
# - "Smith J. K."         → last-name = "Smith"          ❌ (không có dấu phẩy)
# - "J. K. Smith"         → last-name = "Smith"          ❌ (không có dấu phẩy)
```

**Fix proposal:** Author parser riêng (tuần 4–5) — module `matching/author_parser.py` chuẩn hoá last-name + initials + full-name.

### 1.2 ❌ `datetime.utcnow()` deprecated trong Python 3.14

```
DeprecationWarning: datetime.datetime.utcnow() is deprecated
```

**Vị trí:** `src/integrity_checker/pipeline/integrity_pipeline.py:178`.

**Fix:** Đổi thành `datetime.now(timezone.utc)`.

### 1.3 ⚠️ `pytest` không nhận `asyncio_mode = "auto"` config option

```
PytestConfigWarning: Unknown config option: asyncio_mode
```

**Fix:** Cài `pytest-asyncio` rồi đảm bảo `[tool.pytest.ini_options]` có đúng format (đã có trong pyproject.toml, vấn đề là dependency chưa có khi chạy bằng system python).

### 1.4 ⚠️ SwigPyObject/SwigPyPacked deprecation warning từ PyMuPDF

```
DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
```

**Fix:** Không cần — warning từ PyMuPDF upstream, không ảnh hưởng logic.

### 1.5 ⚠️ FastAPI TestClient + httpx deprecation warning

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated
```

**Fix:** Chuyển sang `httpx2` khi stable. Hiện tại bỏ qua.

---

## 2. Missing implementations — theo tuần

### 2.1 Tuần 3 — CitationExtractor hoàn chỉnh
- [ ] Author parsing chuẩn (xem 1.1)
- [ ] Vietnamese citation support (regex riêng cho format VN)
- [ ] Numeric superscript citations (`^1`, `^2,3`)
- [ ] Citation với page numbers (`(Smith, 2020, p. 45)`)
- [ ] Author groups chuẩn (`Smith, J., & Jones, A.`)

### 2.2 Tuần 4–5 — Regex patterns
- [ ] MLA regex pattern
- [ ] Chicago (notes-bibliography + author-date) patterns
- [ ] IEEE numeric range (`[1-5]`)
- [ ] Harvard (author-date, UK style)

### 2.3 Tuần 6 — Reference list parser đa style
- [ ] `MLARefParser`, `ChicagoRefParser`, `IEEERefParser`
- [ ] Title trong ngoặc kép vs. italics detection
- [ ] DOI/URL cuối entry

### 2.4 Tuần 7 — Pipeline
- [ ] Batch processing nhiều PDF
- [ ] Persistent cache (key = SHA256 của citation + content)

### 2.5 Tuần 9–10 — **Critical: 4 API clients**

| File | Status | Cần làm |
|---|---|---|
| `crossref_client.py` | ❌ STUB | `GET /works/{doi}` exact + `/works?query.bibliographic=...` |
| `openalex_client.py` | ❌ STUB | `GET /works?search=...&filter=...` |
| `semantic_scholar_client.py` | ❌ STUB | `GET /paper/search?query=...&fields=...` |
| `arxiv_client.py` | ❌ STUB | `arxiv.Search(query=..., max_results=5)` qua SDK |

**Hiện tại:** tất cả 4 client đều trả `SourceCandidate(found=False)` → pipeline luôn rơi vào nhánh `UNRESOLVED`.

### 2.6 Tuần 11 — Matching tuning
- [ ] Author normalization (last-name canonical, diacritics)
- [ ] Venue normalization (viết tắt vs đầy đủ)
- [ ] Fuzzy threshold tuning trên validation set

### 2.7 Tuần 12 — Symbolic rules
- [ ] Thêm rule: DOI resolve nhưng title mismatch → `METADATA_ERROR` (đã có, cần test thêm)
- [ ] Tuning thresholds trên validation set
- [ ] Abstention band tối ưu (ECE-driven)

### 2.8 Tuần 13 — CIS weights
- [ ] Optimization trên validation set (GridSearch hoặc theo rubric GVHD)
- [ ] In-text ↔ bib consistency thật (cần map citation in-text ↔ reference list entry)
- [ ] Format consistency thật (cần style detector)

### 2.9 Tuần 14 — IAA
- [ ] 2 SV cùng annotate 100 citation
- [ ] Tính Cohen's kappa — target ≥0.7
- [ ] `data/ground_truth/iaa_template.csv` hiện tại chỉ là stub

### 2.10 Tuần 15 — Web UI polish
- [ ] Chạy `npx shadcn@latest add button card table dialog` để sinh components
- [ ] `HistoryPage` cần backend endpoint `GET /api/essays` (list) — chưa có
- [ ] `DecisionSupportDisclaimer` đang fetch từ `/api/health` mỗi lần mount — OK nhưng có thể cache
- [ ] Override verdict UI (giảng viên sửa nhãn → log vào `audit_logs`) — chưa có

### 2.11 Tuần 16 — Baselines + Metrics
- [ ] B0: Link/DOI only (chỉ check DOI resolve)
- [ ] B1: Crossref top-1
- [ ] B2: Fuzzy matching (title + author)
- [ ] B3: Embedding only (cosine similarity)
- [ ] B4: ML classifier (LogisticRegression / XGBoost)
- [ ] Proposed: Multi-source + neural + symbolic + abstention
- [ ] So sánh P/R/F1 trên gold dataset

---

## 3. Caveats kỹ thuật — refactor sau

### 3.1 PDF parsing
- ⚠️ **Hybrid parser chain** đã có (`chain_parsers([MuPdfParser(), PdfPlumberParser()])`) nhưng `BasePDFParser.is_supported()` chỉ check extension `.pdf` — chưa check magic bytes.
- ⚠️ **OCR fallback** (`fallback_to_ocr: false`): hiện tại nếu PDF là scan (không có text layer), pipeline fail im lặng. Cần raise exception rõ ràng hoặc integrate OCR.
- ⚠️ **Encrypted PDF**: chưa handle — sẽ raise exception từ PyMuPDF.

### 3.2 Retrieval
- ⚠️ **Retry logic**: hiện tại không có. Khi API timeout/5xx sẽ fail. Cần integrate `tenacity` retry exponential backoff.
- ⚠️ **Cache key**: hiện tại `DiskCache._key_to_path` chỉ dùng SHA256-style hash của raw text. Chưa truyền source name vào key → có thể conflict giữa Crossref và OpenAlex cùng return cùng record.
- ⚠️ **Rate limiter**: dùng spacing cố định. Khi chạy song song (`parallel=True`), spacing giữa các source name khác nhau → vẫn OK, nhưng **không sliding-window**. Sẽ vỡ rate limit nếu gọi đột biến.

### 3.3 Logic
- ⚠️ **In-text ↔ bib consistency** (CIS component): hiện tại stub `0.8` — **KHÔNG phản ánh thật**. Cần implement ở tuần 13.
- ⚠️ **Format consistency** (CIS component): hiện tại stub `0.85` — **KHÔNG phản ánh thật**. Cần implement ở tuần 13.
- ⚠️ **`NeuroSymbolicChecker` thiếu classifier ML** (đã đánh dấu TODO tuần 12–13).

### 3.4 Pipeline
- ⚠️ **`asyncio.run` trong sync wrapper**: nếu gọi `pipeline.run()` từ trong async context (vd. từ FastAPI endpoint đã có event loop), sẽ raise `RuntimeError: asyncio.run() cannot be called from a running event loop`. Cần detect và dùng `loop.run_until_complete` hoặc `loop.run_in_executor`.

### 3.5 DB
- ⚠️ **Không có Alembic migrations** — dùng `Base.metadata.create_all()` lúc startup. OK cho MVP, nhưng khi schema đổi sẽ khó migrate.
- ⚠️ **SQLite only** — production cần PostgreSQL. Settings đã có `database.url` configurable.
- ⚠️ **`audit_logs` table có nhưng chưa có API để log override**.

### 3.6 Web
- ⚠️ **shadcn components** chưa được generate thật (`src/components/ui/placeholder.ts`). Hiện tại UI dùng Tailwind classes trực tiếp. Cần chạy `npx shadcn@latest add` tuần 15.
- ⚠️ **`react-dropzone` chưa có trong package.json** — thiếu dependency! UI sẽ fail compile.
- ⚠️ **`useEssayAnalysis` hook** không có polling — chỉ fetch 1 lần.
- ⚠️ **`VITE_API_BASE_URL` mặc định** = `/api` (qua Vite proxy) — OK cho dev, cần override cho prod.

---

## 4. Out-of-scope (ghi rõ để tránh scope creep)

Theo đề cương + user chốt 2026-07-26:

- ❌ Chấm điểm content / organization / language / vocabulary / mechanics
- ❌ AES rubric (Quadratic Weighted Kappa, holistic scoring)
- ❌ Phát hiện đạo văn
- ❌ Phát hiện toàn bộ văn bản do AI tạo
- ❌ **Tự động kết luận gian lận học thuật** — hệ thống là decision-support
- ❌ Claim-level verification toàn diện
- ❌ OCR scanned PDF (mở rộng tương lai)
- ❌ Sách / ISBN (mở rộng tương lai)
- ❌ Google Scholar / SerpAPI (bị loại — không có API công khai, vi phạm TOS)
- ❌ GROBID (mở rộng tương lai — đã có adapter slot)
- ❌ **Auto-grade toàn bài tiểu luận** (dù GVHD có nói lỏng lẻo trong đề cương, các mục tiêu/tiêu chí/công nghệ đều nói citation-only — user đã xác nhận 2026-07-26)

---

## 5. Testing gaps

### 5.1 Tests chưa có
- [ ] `tests/unit/test_extraction_preprocessor.py` (Unicode, ligature)
- [ ] `tests/unit/test_semantic_matcher.py` (lazy-load model)
- [ ] `tests/unit/test_retrieval_orchestrator.py` (parallel + dedupe)
- [ ] `tests/unit/test_consensus.py`
- [ ] `tests/unit/test_calibration.py` (ECE/Brier math)
- [ ] `tests/unit/test_explanation.py` (Vietnamese template)
- [ ] `tests/unit/test_db_repository.py`
- [ ] `tests/integration/test_full_pdf_pipeline.py` (nhiều PDF batch)
- [ ] `tests/integration/test_api_upload.py` (upload thật qua multipart)

### 5.2 Coverage thấp
- `pipeline/integrity_pipeline.py`: chỉ test happy path. Chưa test:
  - 0 citations extracted
  - 1 citation duy nhất
  - Toàn bộ API fail (đã test qua SymbolicRules)
- `db/repository.py`: chưa có test thật.

### 5.3 Property-based tests chưa có
- Có thể thêm `hypothesis` library để test parser với input random.

---

## 6. Security / Privacy notes

### 6.1 Quyền riêng tư
- ⚠️ **Tiểu luận SV là dữ liệu nhạy cảm**. Mặc dù đề cương có ghi "đã được ẩn danh", vẫn cần:
  - Không commit essay thật vào git
  - Không gửi essay qua API bên thứ ba nếu không cần thiết
  - Cache TTL 24h — sau 24h sẽ bị xoá
- ⚠️ **Gold dataset cũng có thể chứa thông tin nhạy cảm** — cần review trước khi công khai

### 6.2 API keys
- ⚠️ `S2_API_KEY` chỉ optional, không commit
- ⚠️ `CONTACT_EMAIL` đang mặc định `student@tdtu.edu.vn` — đổi sang email thật của nhóm trước khi demo

### 6.3 Disclaimer bắt buộc
- ⚠️ Mọi page web PHẢI có `<DecisionSupportDisclaimer />`
- ⚠️ Mọi report export PHẢI có disclaimer đầu trang (đã có trong `_json_response` và `_csv_response`)
- ⚠️ FastAPI `/api/health` PHẢI trả disclaimer (đã có)

### 6.4 Security findings (từ automated review 2026-07-26) — KHÔNG fix trong skeleton phase

> Background security review phát hiện 8 issues ở mức MEDIUM/HIGH. **Tôi không fix** theo yêu cầu của user (chỉ là skeleton — security chưa trong scope MVP). Cần xử lý **trước khi deploy production**, ước lượng 1–2 tuần.

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
- Hệ thống MVP chỉ dùng **trong nội bộ nhóm TDTU** — authentication thật (qua SSO TDTU) sẽ tích hợp ở tuần 15–16 khi deploy.
- `findings` này đã được ghi nhận, không bỏ qua. Sẽ address trước khi production.

---

## 7. Dependencies — pinned versions cần update

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

---

## 8. Lịch sử thay đổi

| Ngày | Thay đổi |
|---|---|
| 2026-07-26 | Skeleton Phase 1 — tạo 115 files. 29/29 unit tests pass, 8/8 integration tests pass. CLI demo chạy end-to-end. CIS = 45.5/100 (vì API stub → toàn UNRESOLVED). |
| 2026-07-26 | Fix bug `to_search_query()` cho APA format. Fix `out_of_scope` config shape (YAML list). |

---

## 9. Action items ngay sau skeleton

**Tuần 1–2 (SV làm):**
1. Đọc `README.md` + `DEVELOPER_QUICKSTART.md` + file này.
2. `make setup` → `make sample` → `make demo` → `make test`.
3. Mỗi SV đọc `data/ground_truth/annotation_guideline.md` và bắt đầu thu thập 30–50 tiểu luận mẫu thật (đã ẩn danh) để bổ sung cho `data/essays/`.

**Tuần 3 (SV làm):**
1. Implement author parser chuẩn (`matching/author_parser.py`).
2. Thêm Vietnamese regex patterns.
3. Fix `datetime.utcnow()` deprecation warning.

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh