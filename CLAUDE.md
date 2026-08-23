# CLAUDE.md — Essay Integrity Checker

> **Ngày cập nhật:** 2026-08-23
> **Định hướng:** Engineering Contribution (đã chốt với GVHD)

---

## Đề tài

- **Tên:** Hệ thống Neuro-Symbolic hỗ trợ đánh giá tính toàn vẹn trích dẫn và phát hiện tài liệu tham khảo ảo giác trong tiểu luận sinh viên
- **SV:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
- **GVHD:** ThS. Võ Thị Kim Anh
- **Đề cương:** v1.2 đã chốt với GVHD

---

## Định hướng: ENGINEERING CONTRIBUTION

**KHÔNG phải ML Research. KHÔNG cần train model. KHÔNG cần gold dataset.**

### Focus hiện tại:
1. **API Integration** — gọi CrossRef, OpenAlex, Semantic Scholar, arXiv
2. **Cache Strategy** — tối ưu để "đã học thì nhớ", giảm API calls
3. **System Robustness** — retry, backoff, error handling, rate limiting
4. **Architecture** — clean code, maintainable, extensible

### KHÔNG cần làm:
- ❌ Gold dataset / ground truth / annotation
- ❌ Train model / fine-tune
- ❌ Precision / Recall / F1 metrics (formal evaluation)
- ❌ Baseline comparison B0-B5

---

## Kiến trúc 5 tầng (v1.2)

```
PDF → Tầng 1: PDF Parsing → Tầng 2: Style Detection + Bidirectional Linking 
     → Tầng 3: Multi-source API Retrieval → Tầng 4: Matching + Rules 
     → Tầng 5: Báo cáo (Integrity + Source tách rời)
```

### Hai lớp kết quả:

**Lớp 1 — Citation Integrity (`CitationMappingStatus`):**
- `MATCHED`, `MISSING_REFERENCE`, `UNCITED_REFERENCE`, `IN_TEXT_MISMATCH`, `DUPLICATE_REFERENCE`, `AMBIGUOUS_MAPPING`, `STYLE_INCONSISTENT`

**Lớp 2 — Source Verification (`ValidationLabel`):**
- `VERIFIED`, `METADATA_ERROR`, `SUSPECTED_HALLUCINATION`, `UNRESOLVED`

---

## Trạng thái hiện tại (2026-08-25)

### ✅ Đã hoàn thành:
- 4 API clients thật (CrossRef, OpenAlex, S2, arXiv)
- Tenacity retry + exponential backoff
- Cache với disk persistence + source_name trong key
- AuthorMatcher, VenueNormalizer, SourceConsensus
- Fuzzy threshold tuning, Calibration (Brier, ECE)
- StyleDetector, CitationLinker, DuplicateDetector
- 368 tests pass

### 🔄 Cần làm (priority order):
1. **ExplanationGenerator** — sinh lý do bằng tiếng Việt
2. **Web UI enhancements** — style profile view + citation graph
3. **Integration testing** thực tế với GROBID

---

## Quick Commands

```bash
# Setup
make setup
make sample

# Chạy demo
python -m integrity_checker.pipeline.integrity_pipeline data/essays/essay_02_mixed.pdf --output report.json

# Chạy tests
make test

# API server
uvicorn integrity_checker.api.main:app --reload

# Web frontend
cd web && npm install && npm run dev
```

---

## Cấu trúc chính

```
essay-integrity-checker/
├── src/integrity_checker/
│   ├── extraction/      # PDF → text, sections, citations
│   ├── linking/         # Bidirectional citation-reference linking
│   ├── retrieval/       # API clients (CrossRef, OpenAlex, S2, arXiv)
│   ├── matching/        # Author, venue, fuzzy matching
│   ├── logic/           # Rules engine, CIS, calibration
│   ├── pipeline/        # End-to-end orchestrator
│   └── api/             # FastAPI backend
├── web/                 # React + Vite + Tailwind
├── data/                # essays/, ground_truth/, cache/
├── scripts/             # Utilities
└── tests/               # Unit + integration
```

---

## Scope chính thức (v1.2)

### ✅ Trong scope:
- PDF upload + full-text extraction (PyMuPDF + GROBID)
- Citation extraction + bidirectional linking
- Multi-source API verification
- Citation Integrity Score (CIS) — 5 components, weights 35/25/25/10/5
- Web UI với evidence drawer + override capability

### ❌ Ngoài scope:
- OCR scanned PDF
- Sách / ISBN verification
- Claim-level verification (ngữ nghĩa)
- Auto-grade toàn bài tiểu luận
- Tự động kết luận gian lận
- Google Scholar / SerpAPI

---

## Nguyên tắc làm việc

1. **Mỗi tuần:** Update `tests/progress/SESSION_SUMMARY_WEEK{N}.md`
2. **Mỗi feature:** Viết tests TRƯỚC, rồi mới code
3. **Commit message:** Mô tả ngắn gọn đã làm gì
4. **Trước khi hỏi GVHD:** Kiểm tra lại KNOWN_ISSUES_AND_TODO.md xem đã có trong đó chưa

---

## Files quan trọng

| File | Mục đích |
|------|----------|
| `README.md` | Tổng quan project, quick start |
| `KNOWN_ISSUES_AND_TODO.md` | Bugs, TODOs, out-of-scope |
| `DEVELOPER_QUICKSTART.md` | Setup guide chi tiết |
| `tests/progress/SESSION_SUMMARY_*.md` | Progress theo tuần |

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**Last updated:** 2026-08-23
