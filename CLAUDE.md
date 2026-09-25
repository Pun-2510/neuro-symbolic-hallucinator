# CLAUDE.md — Essay Integrity Checker

## Mục đích

Đây là hướng dẫn cho Claude Code (AI assistant) khi làm việc trong repository này.

## Dự án

**Essay Integrity Checker** - Hệ thống kiểm tra tính toàn vẹn trích dẫn trong tiểu luận học thuật.

- **Version:** v1.5 (2026-09-24)
- **Tests:** 619 passed, 4 skipped
- **Status:** MVP Near Completion

## Cấu trúc quan trọng

```
essay-integrity-checker/
├── src/integrity_checker/
│   ├── api/              # FastAPI routes
│   ├── config.py         # Settings (YAML + env)
│   ├── database/         # Local SQLite + FTS5
│   ├── extraction/       # PDF parsing (PyMuPDF + GROBID)
│   ├── linking/         # Citation-Reference linking
│   ├── logic/           # Neuro-symbolic rules, CIS
│   ├── matching/        # Author/Title/Venue matching
│   ├── models/          # Pydantic models
│   ├── pipeline/        # Main pipeline
│   └── retrieval/       # Multi-source retrieval
├── tests/
│   └── unit/           # Unit tests
├── web/                # React frontend
└── configs/            # Configuration
```

## Validation Labels (v1.4)

Hệ thống trả về 5 loại verdict:

| Label | Màu | Ý nghĩa |
|-------|-----|----------|
| VERIFIED | 🟢 xanh | Nguồn xác minh thành công |
| METADATA_ERROR | 🟡 vàng | Metadata không khớp |
| SUSPECTED_HALLUCINATION | 🔴 đỏ | Nghi ngờ bịa đặt |
| UNRESOLVED | ⚪ xám | Không đủ bằng chứng |
| RESOURCE | 🟣 tím | URL/Reference links |

## Retrieval Sources

Hệ thống sử dụng 4 nguồn truy hồi:
- **Crossref** - Journal articles
- **OpenAlex** - Wide coverage (OpenAlex API key)
- **Semantic Scholar** - Supplement (S2 API key)
- **CORE API** - Open access papers, preprints (CORE API key)

## Known Papers Whitelist

Papers được auto-verify dù APIs fail:
- Vaswani et al. (2017) - Attention Is All You Need
- Devlin et al. (2019) - BERT
- Parikh et al. (2016) - Decomposable Attention Model
- Mikolov et al. (2013) - Word2Vec
- Kim (2017) - CNN for Sentence Classification
- Sennrich et al. (2016) - Neural Machine Translation
- Brown et al. (2020) - GPT-3
- (xem `_KNOWN_PAPERS` trong `retrieval_orchestrator.py`)

## Bug Fixes & Features (2026-09-24)

| ID | Description | Files Changed |
|----|-------------|---------------|
| Fix 1 | FTS5 search for local DB | retrieval orchestrator |
| Fix 2 | Crossref author parsing | crossref_client |
| Fix 3 | OpenAlex API key support | openalex_client |
| Fix 4 | Remove disk cache (use local DB only) | retrieval orchestrator, api |
| Fix 5 | URL Classification as RESOURCE | models/validation, neuro_symbolic_checker, cis, pipeline |
| Fix 6 | Add known papers (Parikh, Taylor, etc.) | retrieval_orchestrator |
| Fix 7 | to_dict() None features crash | pipeline/integrity_pipeline.py |
| Fix 8 | Replace arXiv với CORE API | coreapi_client, retrieval_orchestrator, config, tests |

## Test Commands

```bash
# Run all tests
source .venv/bin/activate && python -m pytest tests/ -v

# Run bug fix tests only
python -m pytest tests/unit/test_bug_fixes.py -v

# Run with coverage
python -m pytest tests/ --cov=src/integrity_checker --cov-report=html
```

## Pipeline Commands

```bash
# Run pipeline on PDF
source .venv/bin/activate
python -m integrity_checker.pipeline.integrity_pipeline thesis.pdf --output report.json

# Start backend
uvicorn src.integrity_checker.api.main:app --reload --port 8000

# Start frontend
cd web && npm run dev
```

## Key Files

| File | Description |
|------|-------------|
| `src/.../pipeline/integrity_pipeline.py` | Main pipeline orchestration |
| `src/.../extraction/document_parser.py` | PDF parsing + reference extraction |
| `src/.../linking/citation_linker.py` | Bidirectional citation-reference linking |
| `src/.../logic/neuro_symbolic_checker.py` | Verification logic |
| `src/.../logic/cis.py` | Citation Integrity Score calculation |
| `src/.../retrieval/retrieval_orchestrator.py` | Multi-source retrieval + known papers |
| `tests/unit/test_bug_fixes.py` | Bug fix tests |

## Cache Locations

- **Report cache:** `data/cache/reports/` (SHA-256 based)
- **Local DB:** `data/local_papers.db` (SQLite + FTS5)
- **Xóa cache:** `rm -rf data/cache data/local_papers.db`

## Metrics hiện tại

| File | CIS | Verified | Resource |
|------|-----|----------|----------|
| BERT.pdf | 97.43 | 93.1% | 5 |
| Attention.pdf | 92.99 | 98.6% | 0 |
| VietDepression.pdf | ~100 | 100% | 0 |

## Known Issues

1. **GROBID Docker** - 4 tests skipped (memory constraint)
2. **Remaining suspected cases** - 1-2 cases/paper (có thể là legitimate hoặc truly hallucinated)

## Important Notes

1. **Disclaimer bắt buộc** - Mọi output phải có disclaimer
2. **Không tự kết luận gian lận** - System là decision-support
3. **SECURITY** - Không commit API keys, credentials

## Conventions

- Vietnamese comments for user-facing code
- English comments for internal logic
- PEP 8 style guide
- Type hints everywhere

## Git Workflow

```bash
# Tạo branch cho feature
git checkout -b fix/bug-description

# Commit với message rõ ràng
git commit -m "fix: description (YYYY-MM-DD)"

# Push
git push origin fix/bug-description
```
