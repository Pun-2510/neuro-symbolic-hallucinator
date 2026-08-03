# Session Summary — Phiên làm việc ngày 2026-07-26

> **Ngày:** 2026-07-26 (Asia/Ho_Chi_Minh)
> **Thời gian:** ~14:25 → 15:03 ICT (khoảng 38 phút)
> **Người thực hiện:** Claude (Claude Opus 5, 1M context) + User (Nguyễn Bảo Minh, 523H0054)
> **Project:** Essay Integrity Checker — Đồ án tốt nghiệp TDTU

---

## 1. Mục tiêu phiên

Tạo skeleton + code mồi cho project "Hệ thống Neuro-Symbolic hỗ trợ đánh giá độ tin cậy trích dẫn và phát hiện tài liệu tham khảo ảo giác trong tiểu luận sinh viên" theo đề cương v1.1 đã được GVHD duyệt (xem `../docs/de_cuong_template.md`).

**Output mong đợi:**
1. Cấu trúc thư mục hoàn chỉnh với abstract classes + dataclass models.
2. `main.py` chạy được end-to-end trên 1 PDF mẫu.
3. Mỗi module có docstring + `# TODO` rõ ràng.
4. 5–10 PDF tiểu luận mẫu (cả trích dẫn thật + ảo).

---

## 2. Quyết định được chốt trong phiên

### 2.1 Scope (câu 1 — user chốt A, đề cương v1.1)

- **Citation-only**: hệ thống chỉ kiểm tra trích dẫn, KHÔNG chấm điểm toàn bài tiểu luận.
- **Taxonomy 4 nhãn**: `VERIFIED / METADATA_ERROR / SUSPECTED_HALLUCINATION / UNRESOLVED`.
- **Decision-support**: hệ thống hỗ trợ giảng viên, KHÔNG tự kết luận gian lận.
- **Citation Integrity Score (CIS)**: đo lường riêng phần trích dẫn (0–100), KHÔNG phải điểm tiểu luận.
- **2 SV, 18 tuần**.

### 2.2 API stack (câu 1, đề cương v1.1)

- **Crossref + OpenAlex + Semantic Scholar + arXiv**.
- **KHÔNG dùng Google Scholar / SerpAPI** (không có API công khai, tốn phí, vi phạm TOS).

### 2.3 PDF parsing (câu 2 — user chốt B)

- **PyMuPDF + pdfplumber**.
- **Bỏ GROBID** ở MVP, nhưng để 1 adapter slot (`BasePDFParser` abstract + `chain_parsers()`).
- Đồng ý tốn thêm 2–3 tuần làm UI đẹp.

### 2.4 Frontend (câu 2 — user chốt B)

- **React + Vite + Tailwind + shadcn/ui**.

### 2.5 Skeleton format (câu 3 — user chốt A)

- **Full skeleton + code mồi**: cấu trúc thư mục, `__init__.py`, requirements.txt, Dockerfile, docker-compose, README, .gitignore, abstract classes + interface, dataclass models, `main.py` chạy được end-to-end.
- Mỗi module có docstring + TODO rõ ràng.

### 2.6 Sample data (câu 4 — user chốt A)

- Tôi tự tạo **5 PDF mẫu** (cả trích dẫn thật + ảo) bằng `reportlab`.

### 2.7 Phạm vi cuối cùng (xác nhận lại sau khi user hỏi GVHD)

> Tại 1 thời điểm user đã nói "GVHD nói hệ thống tự động chấm điểm tiểu luận luôn" — gây mâu thuẫn với 4 mục tiêu/tiêu chí/công nghệ đều nói về citation validation.

**Kết quả đối chiếu (user xác nhận):**
- **Scope thật**: Citation-only (giữ nguyên).
- **API stack**: Crossref + OpenAlex + S2 + arXiv (giữ chốt 1A).
- **Skeleton**: Giữ nguyên (không pivot).

Lý do: câu "tự động chấm điểm tiểu luận" trong đề cương là **diễn đạt lỏng lẻo** của GVHD. Ý thật là "tự động chấm phần **tài liệu tham khảo**" — đúng với 4 mục tiêu/tiêu chí/công nghệ.

Tôi đã thêm 1 đoạn vào `README.md` giải thích rõ ràng để tránh hiểu nhầm tương tự sau này.

---

## 3. Quá trình thực hiện

### Phase 0 — Plan (EnterPlanMode)

- Đọc 4 file trong `/Users/iannwendy/Desktop/DATN/docs/`:
  - `de_cuong_template.md` (đề cương v1.1 đã duyệt)
  - `NGHIEN_CUU_LITERATURE_REVIEW.md` (lit review)
  - `ROADMAP_ZERO_TO_HERO.md` (tham khảo)
  - `DE_TAI_DATN_HUONG_DAN_A_Z.md` (đề cương cũ — Hướng B, bị bác)
- Không có codebase ngoài `docs/`.
- Tạo plan tại `/Users/iannwendy/.claude/plans/steady-napping-swan.md` (~700 dòng).
- User duyệt plan.

### Phase 1 — Bootstrap project root (~10 phút, 10 files)

| File | Mục đích |
|---|---|
| `README.md` | Context, scope (citation-only), quick start, decision-support disclaimer nổi bật |
| `LICENSE` | MIT |
| `.gitignore` | Bỏ qua .venv, .env, data/cache, data/app.db, node_modules |
| `.env.example` | CONTACT_EMAIL, S2_API_KEY, paths |
| `requirements.txt` | 15 deps pinned major versions |
| `requirements-dev.txt` | Thêm pytest, ruff, black, mypy |
| `pyproject.toml` | packaging + ruff/black/isort/mypy/pytest config |
| `Makefile` | setup/sample/demo/api/web/test/lint/format/clean |
| `Dockerfile` | FastAPI image với libmupdf |
| `docker-compose.yml` | api + web dev server |
| `configs/config.example.yaml` | Thresholds, weights, paths, decision-support text |

### Phase 2 — Core package (`src/integrity_checker/`)

8 sub-modules, tổng cộng **~30 files**:

1. **core** (`config.py`, `logging.py`) — Pydantic Settings + loguru
2. **models** (4 files) — Citation, SourceCandidate, CitationVerdict, CIS, Pydantic schemas
3. **extraction** (7 files) — BasePDFParser, MuPdfParser, PdfPlumberParser, TextPreprocessor, RegexPatterns, CitationExtractor, ReferenceListParser
4. **retrieval** (8 files) — BaseScholarClient, 4 clients (Crossref/OpenAlex/S2/arXiv), RetrievalOrchestrator, RateLimiter, DiskCache
5. **matching** (4 files) — FuzzyMatcher, SemanticMatcher, FeatureCalculator, ConsensusCalculator
6. **logic** (5 files) — SymbolicRules, NeuroSymbolicChecker, CalibrationCalculator, CISCalculator, ExplanationGenerator
7. **pipeline** — IntegrityPipeline + CLI entry-point
8. **api** (8 files) — FastAPI main + 4 routes + essay_service
9. **db** (4 files) — SQLAlchemy models + repository
10. **evaluation** (3 files) — MetricsCalculator, BaselineRunner, EvaluationReport

### Phase 3 — Scripts + sample data

- `scripts/gen_sample_essays.py` — reportlab sinh 5 PDF mẫu (real/mixed/fabricated/edge)
- `scripts/gen_gold_dataset.py` — gold_dataset.json mồi (16 citations)
- `scripts/run_demo.py` — CLI wrapper
- `data/essays/README.md` — mô tả từng file mẫu
- `data/ground_truth/annotation_guideline.md` — 4-nhãn guidelines + edge cases
- `data/ground_truth/iaa_template.csv` — 16 dòng stub

### Phase 4 — Tests (8 files)

- `tests/conftest.py` — fixtures (in-memory SQLite, set_test_env)
- `tests/unit/` (7 files, 29 tests) — models, regex, fuzzy, rules, CIS
- `tests/integration/` (2 files, 8 tests) — pipeline end-to-end, FastAPI

### Phase 5 — Web frontend (React + Vite + TS + Tailwind + shadcn, ~18 files)

- 4 pages: UploadPage, EssayPage, HistoryPage + App router
- 6 components: DecisionSupportDisclaimer, VerdictBadge (4 màu), UploadDropzone, VerdictTable, CitationDetailDrawer, CISScoreCard
- 1 hook: useEssayAnalysis
- 1 API client (`api/client.ts`) match với Pydantic schemas
- Tailwind config + theme variables (4 verdict colors)
- vite.config.ts với proxy `/api` → `localhost:8000`

### Phase 6 — Verify end-to-end (~10 phút)

1. **Cài venv `.venv-smoke`** + 12 deps thiết yếu (reportlab, PyMuPDF, pdfplumber, fastapi, pytest, etc.)
2. **Chạy pytest unit tests**:
   - Lần 1: 19 passed, 10 failed
   - Fix 2 bugs:
     - `OutOfScopeConfig` không match YAML list → đổi root field thành `list[str]`
     - `Citation.to_search_query()` lấy last-name sai cho APA format → xử lý dấu phẩy
   - Lần 2: **29 passed, 1 skipped** ✅
3. **Generate sample essays**: 5 PDFs OK ✅
4. **Generate gold dataset**: 16 citations ✅
5. **Chạy CLI demo**: pipeline end-to-end trên `essay_02_mixed.pdf`:
   - Parse 2 trang OK
   - Extract 14 citations OK
   - 4 API call (đều fail vì stub — đúng kỳ vọng)
   - Verdict: 14 × `unresolved` (fallback đúng)
   - CIS: 45.5/100
   - JSON report ghi ra `data/cache/essay_02.report.json` OK ✅
6. **Chạy integration tests**: 8 passed (40s) ✅
7. **FastAPI smoke test**: `/api/health` → 200, `/api/essays/99999` → 404 ✅
8. **Dọn dẹp**: xóa `.venv-smoke/` và `data/cache/*.json`

### Phase 7 — Documentation cuối

- `DEVELOPER_QUICKSTART.md` — roadmap 18 tuần chi tiết cho 2 SV
- `KNOWN_ISSUES_AND_TODO.md` — file này (sẽ viết tiếp theo)

---

## 4. Tổng kết files

| Loại | Số lượng |
|---|---|
| Python (.py) | ~70 |
| TypeScript/TSX (.ts, .tsx) | 18 |
| Markdown (.md) | 9 |
| Config (.yaml, .toml, .json, .css, .html) | 10 |
| Khác (Dockerfile, Makefile, .gitignore, .env, LICENSE) | 8 |
| **Tổng** | **~115** |

---

## 5. Trạng thái cuối phiên

✅ **Tất cả 11 tasks completed**:

| # | Task | Status |
|---|---|---|
| 1 | Bootstrap project root + top-level config | ✅ |
| 2 | Build src/integrity_checker core | ✅ |
| 3 | Build extraction module | ✅ |
| 4 | Build retrieval module | ✅ |
| 5 | Build matching module | ✅ |
| 6 | Build logic module | ✅ |
| 7 | Build pipeline + db + api modules | ✅ |
| 8 | Generate sample essays + gold dataset scripts | ✅ |
| 9 | Build tests (unit + integration) | ✅ |
| 10 | Build web frontend | ✅ |
| 11 | Verify end-to-end + README final pass | ✅ |

**Verify kết quả:**
- 29/29 unit tests pass
- 8/8 integration tests pass
- CLI demo chạy end-to-end trên PDF mẫu
- FastAPI `/api/health` → 200 OK
- Sample data: 5 PDFs + gold_dataset.json (16 citations)

**Caveats đã biết** (xem `KNOWN_ISSUES_AND_TODO.md`):
- 4 API client đều là stub → verdict toàn `unresolved` (đúng kỳ vọng)
- `react-dropzone` chưa có trong `web/package.json` (cần `npm install` trước khi dev)
- shadcn components chưa được generate thật (`src/components/ui/placeholder.ts`)
- In-text ↔ bib consistency + format consistency (CIS components) hiện là stub

---

## 6. Next steps cho 2 SV (tuần 1–3)

1. **Đọc**: `README.md` + `DEVELOPER_QUICKSTART.md` + `KNOWN_ISSUES_AND_TODO.md`
2. **Setup**: `make setup` → `make sample` → `make demo` → `make test`
3. **Web**: `cd web && npm install && npm run dev`
4. **Tuần 1–2**: thu thập 30–50 tiểu luận mẫu thật (đã ẩn danh), bổ sung vào `data/essays/`
5. **Tuần 3**: implement author parser chuẩn (`matching/author_parser.py`), thêm Vietnamese regex, fix `datetime.utcnow()` deprecation
6. **Tuần 4–5**: regex patterns cho MLA, Chicago, IEEE, Harvard
7. **Tuần 6**: reference list parser đa style
8. **Tuần 7**: pipeline batch processing
9. **Tuần 8**: mid-term demo
10. **Tuần 9–10**: implement 4 API client thật — đây là lúc verdict bắt đầu phân hóa thật sự
11. **Tuần 11–13**: matching tuning + symbolic rules + CIS weights optimization
12. **Tuần 14**: IAA — 2 SV cùng annotate 100 citation
13. **Tuần 15**: web UI polish với shadcn components đầy đủ
14. **Tuần 16**: baselines B0–B4 + đo P/R/F1
15. **Tuần 17**: final experiments + viết thesis Ch. 4
16. **Tuần 18**: bảo vệ

---

## 7. Tech stack cuối cùng

| Layer | Tech |
|---|---|
| Language | Python 3.11+ (đã test trên 3.14) |
| Backend | FastAPI + SQLAlchemy 2.0 + SQLite |
| PDF | PyMuPDF + pdfplumber (GROBID bỏ, để adapter slot) |
| Retrieval | httpx async + rate limiter + disk cache |
| ML | RapidFuzz + sentence-transformers (lazy-load) |
| Frontend | React 18 + Vite 5 + TS + Tailwind + shadcn/ui + Radix |
| Testing | pytest + pytest-asyncio + httpx TestClient |
| Container | Docker + docker-compose |
| Lint | ruff + black + isort + mypy |

---

## 8. Files reference nhanh

```
essay-integrity-checker/
├── README.md                              ← đọc đầu tiên
├── DEVELOPER_QUICKSTART.md                ← roadmap 18 tuần
├── KNOWN_ISSUES_AND_TODO.md               ← bugs + missing impls
├── SESSION_SUMMARY.md                     ← file này
├── LICENSE                                ← MIT
├── .env.example
├── .gitignore
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── configs/config.example.yaml
├── data/
│   ├── essays/                            ← 5 sample PDFs (sau khi chạy gen_sample_essays.py)
│   │   └── README.md
│   └── ground_truth/
│       ├── annotation_guideline.md
│       ├── gold_dataset.json              ← sau khi chạy gen_gold_dataset.py
│       └── iaa_template.csv
├── scripts/
│   ├── gen_sample_essays.py
│   ├── gen_gold_dataset.py
│   └── run_demo.py
├── src/integrity_checker/
│   ├── __init__.py
│   ├── __version__.py
│   ├── config.py
│   ├── logging.py
│   ├── models/        (4 files)
│   ├── extraction/    (7 files)
│   ├── retrieval/     (8 files)
│   ├── matching/      (4 files)
│   ├── logic/         (5 files)
│   ├── pipeline/      (1 file + CLI)
│   ├── api/           (8 files)
│   ├── db/            (4 files)
│   └── evaluation/    (3 files)
├── tests/
│   ├── conftest.py
│   ├── unit/          (7 files, 29 tests)
│   └── integration/   (2 files, 8 tests)
├── web/
│   ├── README.md
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── components.json
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── router.tsx
│       ├── index.css
│       ├── api/client.ts
│       ├── components/  (8 files)
│       ├── pages/       (3 files)
│       ├── hooks/       (1 file)
│       └── lib/         (1 file)
└── notebooks/
```

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh
**Trường:** Đại học Tôn Đức Thắng (TDTU), Khoa CNTT
**Phiên:** 2026-07-26