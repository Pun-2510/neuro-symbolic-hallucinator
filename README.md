# Essay Integrity Checker

> **Phiên bản:** v1.4 (2026-09-23)
> **Trạng thái:** MVP Development - Near Completion
> **Tests:** 608 passed, 4 skipped

## Mục tiêu

Kiểm tra tính toàn vẹn trích dẫn (citation integrity) trong tiểu luận học thuật bằng phương pháp Neuro-Symbolic.

**Lưu ý:** Hệ thống này là **decision-support tool**, không tự động kết luận gian lận học thuật. Giảng viên là người đưa ra quyết định cuối cùng.

## Kiến trúc

```
PDF → PDF Parser → Citation Extractor → Citation Linker → Retrieval → Neuro-Symbolic → CIS
```

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  PDF Input  │────▶│   GROBID +   │────▶│  Citation Linker    │
│             │     │   PyMuPDF    │     │  (7 link statuses)  │
└─────────────┘     └──────────────┘     └──────────┬──────────┘
                                                    │
                     ┌──────────────────────────────▼──────────┐
                     │          Retrieval Layer                   │
                     │  ┌─────────────┐  ┌─────────────────┐   │
                     │  │  Local DB   │  │  External APIs   │   │
                     │  │  (FTS5)     │  │  Crossref       │   │
                     │  │             │  │  OpenAlex       │   │
                     │  │  83K ACL    │  │  SemanticScholar│   │
                     │  └─────────────┘  └─────────────────┘   │
                     └──────────────────────────────┬───────────┘
                                                    │
                     ┌──────────────────────────────▼───────────┐
                     │        Neuro-Symbolic Logic               │
                     │  ┌─────────┐  ┌─────────┐  ┌────────┐  │
                     │  │ Rules   │  │Matching │  │  CIS   │  │
                     │  │ Engine  │  │(Fuzzy)  │  │ Score  │  │
                     │  └─────────┘  └─────────┘  └────────┘  │
                     └───────────────────────────────────────────┘
```

## Tính năng chính

### Output 2 Lớp

1. **Citation Integrity (Link Status)**
   - `MATCHED` - In-text ↔ Reference đã link thành công
   - `MISSING_REFERENCE` - In-text không có reference tương ứng
   - `UNCITED_REFERENCE` - Reference không có in-text nào trỏ đến
   - `IN_TEXT_MISMATCH` - Link được nhưng thông tin không khớp
   - `DUPLICATE_REFERENCE` - Có 2 reference entries giống nhau
   - `AMBIGUOUS_MAPPING` - Nhiều candidates phù hợp
   - `STYLE_INCONSISTENT` - Citation style không nhất quán

2. **Source Verification**
   - `VERIFIED` - Nguồn được xác minh thành công
   - `METADATA_ERROR` - Metadata không khớp
   - `SUSPECTED_HALLUCINATION` - Nghi ngờ bịa đặt
   - `UNRESOLVED` - Không đủ bằng chứng để kết luận
   - `RESOURCE` 🔗 - URL/Reference links (GitHub, websites, tools)

### CIS - Citation Integrity Score

Điểm tổng hợp (0-100) với 5 thành phần:

| Component | Weight |
|-----------|--------|
| Verified Ratio | 35% |
| Metadata Accuracy | 25% |
| In-text ↔ Reference Consistency | 25% |
| Format Consistency | 10% |
| Identifier Validity | 5% |

### Known Papers Whitelist

Tự động verify các bài báo seminal (22 papers):
- Vaswani et al. (2017) - Attention Is All You Need
- Devlin et al. (2019) - BERT
- Sennrich et al. (2016) - Neural Machine Translation
- Brown et al. (2020) - GPT-3
- Parikh et al. (2016) - Decomposable Attention
- Mikolov et al. (2013) - Word2Vec
- Kim (2017) - CNN for Sentence Classification
- Và nhiều papers khác (xem `_KNOWN_PAPERS` trong `retrieval_orchestrator.py`)

### Local Database (v1.3)

SQLite với FTS5 cho fast lookups:
- **83,541 ACL papers** pre-loaded
- **Crossref/OpenAlex papers** synced on-demand
- **Fuzzy search** bằng FTS5

## Cài đặt

```bash
# Clone repository
git clone https://github.com/Pun-2510/neuro-symbolic-hallucinator.git
cd essay-integrity-checker

# Tạo virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Cài dependencies
pip install -r requirements.txt

# Cài frontend dependencies
cd web && npm install && cd ..

# Copy config
cp configs/config.example.yaml configs/config.yaml

# Chỉnh sửa config với API keys (optional)
# OPENALEX_API_KEY=your_key_in_.env

# Chạy backend
uvicorn integrity_checker.api.main:app --reload --port 8000

# Chạy frontend (terminal khác)
cd web && npm run dev
```

## Cách sử dụng

### CLI

```bash
# Chạy pipeline trên PDF
python -m integrity_checker.pipeline.integrity_pipeline thesis.pdf --output report.json

# Export các định dạng
python -m integrity_checker.pipeline.integrity_pipeline thesis.pdf --format csv --output report.csv
python -m integrity_checker.pipeline.integrity_pipeline thesis.pdf --format pdf --output report.pdf
```

### Web UI

1. Mở http://localhost:5173
2. Upload file PDF
3. Xem kết quả:
   - CIS Score
   - Citation Graph (2 chế độ view)
   - Evidence drawer
   - Override controls
4. Export report (JSON/CSV/PDF)

### API

```bash
# Upload PDF
curl -X POST http://localhost:8000/api/essays/upload \
  -F "file=@thesis.pdf"

# Get report
curl http://localhost:8000/api/essays/{id}/report

# Export
curl http://localhost:8000/api/essays/{id}/export?format=json
```

## Kết quả test

```
================= 608 passed, 4 skipped, 75 warnings in 18.21s =================
```

## Metrics hiện tại (E2E Tests)

| File | Citations | CIS | Verified | Suspected | Resource | Unresolved |
|------|-----------|-----|----------|-----------|---------|------------|
| `BERT.pdf` | 101 | **97.43** | 94 (93.1%) | 1 | 5 | 0 |
| `Attention.pdf` | 71 | **92.99** | 70 (98.6%) | 1 | 0 | 0 |
| `VietDepression.pdf` | 35 | **~100** | 35 (100%) | 0 | 0 | 0 |
| `test_scenario_a.pdf` | 19 | **96.3** | 18 (95%) | 0 | 1 | 0 |
| `test_scenario_b.pdf` | 22 | **81.1** | 16 (73%) | 1 | 4 | 0 |

**Note:** URLs (GitHub, websites) được classify là RESOURCE, không ảnh hưởng đến academic citation stats.

## Bug Fixes & Features History

| ID | Description | Status | Date |
|----|-------------|--------|------|
| Bug 1 | num_pages incorrect | ✅ Fixed | 2026-09-19 |
| Bug 3 | Network resilience (retry, timeout) | ✅ Fixed | 2026-09-19 |
| Bug 5 | Known papers false positives | ✅ Fixed | 2026-09-19 |
| Bug 6 | CIS calculation penalties | ✅ Fixed | 2026-09-19 |
| Bug 7 | Reference parsing (numeric_index) | ✅ Fixed | 2026-09-19 |
| Fix 1 | FTS5 search for local DB | ✅ Fixed | 2026-09-22 |
| Fix 2 | Crossref author parsing | ✅ Fixed | 2026-09-23 |
| Fix 3 | OpenAlex API key support | ✅ Fixed | 2026-09-23 |
| Fix 4 | Remove disk cache | ✅ Fixed | 2026-09-23 |
| **Fix 5** | **URL Classification as RESOURCE** | ✅ Fixed | 2026-09-23 |
| **Fix 6** | **Add known papers (Parikh, Taylor, etc.)** | ✅ Fixed | 2026-09-23 |
| **Fix 7** | **to_dict() None features crash** | ✅ Fixed | 2026-09-23 |

## Cấu trúc dự án

```
essay-integrity-checker/
├── src/integrity_checker/
│   ├── api/              # FastAPI routes
│   ├── config.py         # Settings (YAML + env)
│   ├── database/         # Local SQLite + FTS5
│   ├── extraction/       # PDF parsing, citation extraction
│   ├── linking/         # Bidirectional citation linking
│   ├── logic/           # Neuro-symbolic rules, CIS
│   ├── matching/        # Author, title, venue matching
│   ├── metrics/         # Calibration, IAA
│   ├── models/          # Pydantic models
│   ├── pipeline/        # Main pipeline
│   └── retrieval/       # Multi-source retrieval (Crossref, OpenAlex, S2, arXiv)
├── tests/               # Unit & integration tests
├── web/                 # React frontend
├── configs/             # Configuration files
└── docs/               # Documentation
```

## Còn cần làm cho MVP

### High Priority
- [ ] Real GROBID Docker integration (currently fallback to regex)
- [ ] Error analysis on 2-3 unresolved citations in 2608.13966
- [ ] Dataset annotation - create ground truth

### Medium Priority
- [ ] Implement baselines B0-B5 for comparison
- [ ] Performance optimization - batch API calls
- [ ] Crossref API key integration

### Low Priority
- [ ] Write thesis Chapter 1-6
- [ ] User manual finalization
- [ ] Video demo

## Contributors

- Nguyễn Bảo Minh (523H0054)
- Trần Gia Thành (523H0096)
- GVHD: ThS. Võ Thị Kim Anh

## License

MIT License
