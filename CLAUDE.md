# CLAUDE.md — Essay Integrity Checker

## Mục đích

Đây là hướng dẫn cho Claude Code (AI assistant) khi làm việc trong repository này.

## Dự án

**Essay Integrity Checker** - Hệ thống kiểm tra tính toàn vẹn trích dẫn trong tiểu luận học thuật.

- **Version:** v1.2
- **Updated:** 2026-09-19
- **Tests:** 576 passed, 4 skipped

## Cấu trúc quan trọng

```
essay-integrity-checker/
├── src/integrity_checker/
│   ├── api/              # FastAPI routes
│   ├── extraction/       # PDF parsing (PyMuPDF + GROBID)
│   ├── linking/          # Citation-Reference linking
│   ├── logic/            # Neuro-symbolic rules, CIS
│   ├── matching/         # Author/Title/Venue matching
│   ├── models/           # Pydantic models
│   ├── pipeline/         # Main pipeline
│   └── retrieval/         # Multi-source retrieval
├── tests/
│   └── unit/            # Unit tests
├── web/                  # React frontend
└── configs/             # Configuration
```

## Bug Fixes gần đây (2026-09-19)

1. **Bug 1:** `num_pages` = `document.num_pages` (was `len(sections)`)
2. **Bug 3:** Retry config (3→5), backoff (10→120s), timeout (10→30s)
3. **Bug 5:** Known papers whitelist (Vaswani, Devlin, Sennrich, etc.)
4. **Bug 6:** CIS `MAPPING_PENALTIES` aligned with rubric
5. **Bug 7:** Reference `numeric_index` extraction + page number fix

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
uvicorn integrity_checker.api.main:app --reload --port 8000

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
| `tests/unit/test_bug_fixes.py` | Bug fix tests (19 tests) |

## Known Issues

1. **GROBID Docker** - 4 tests skipped (memory constraint)
2. **Missing Reference** - 5 cases còn lại (3 known papers + 2 suspected)
3. **Unresolved** - 26 IEEE numeric citations

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
