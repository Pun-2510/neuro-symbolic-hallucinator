# Essay Integrity Checker

> **Phiên bản:** v1.2 (2026-09-19)
> **Trạng thái:** MVP hoàn thành - Đang phát triển
> **Tests:** 576 passed, 4 skipped

## Mục tiêu

Kiểm tra tính toàn vẹn trích dẫn (citation integrity) trong tiểu luận học thuật bằng phương pháp Neuro-Symbolic.

**Lưu ý:** Hệ thống này là **decision-support tool**, không tự động kết luận gian lận học thuật. Giảng viên là người đưa ra quyết định cuối cùng.

## Kiến trúc

```
PDF → PDF Parser → Citation Extractor → Citation Linker → Retrieval → Neuro-Symbolic → CIS
```

### 5 Tầng

| Tầng | Chức năng |
|-------|------------|
| **1. Extraction** | PyMuPDF + GROBID, Section Segmentation, Citation Extraction |
| **2. Linking** | Bidirectional Citation-Reference Linking (7 trạng thái) |
| **3. Retrieval** | Crossref, OpenAlex, Semantic Scholar, arXiv (multi-source) |
| **4. Matching** | Author/Tile/Venue matching, Fuzzy matching, Source consensus |
| **5. Logic** | Neuro-Symbolic rules, Calibration, CIS calculation |

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

Tự động verify các bài báo seminal:
- Vaswani et al. (2017) - Attention Is All You Need
- Devlin et al. (2019) - BERT
- Sennrich et al. (2016) - Neural Machine Translation
- Và nhiều papers khác

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
================= 576 passed, 4 skipped, 62 warnings in 21.24s =================
```

## Metrics hiện tại (thesis.pdf)

| Metric | Value |
|--------|-------|
| num_pages | 91 |
| Total Citations | 57 |
| Verified | 28 (49%) |
| Matched | 52 (91%) |
| CIS Score | 74.02/100 |
| in_text_bib_consistency | 96.6% |

## Cấu trúc dự án

```
essay-integrity-checker/
├── src/integrity_checker/
│   ├── api/              # FastAPI routes
│   ├── config.py         # Settings
│   ├── extraction/       # PDF parsing, citation extraction
│   ├── linking/         # Bidirectional citation linking
│   ├── logic/           # Neuro-symbolic rules, CIS
│   ├── matching/        # Author, title, venue matching
│   ├── metrics/         # Calibration, IAA
│   ├── models/          # Pydantic models
│   ├── pipeline/        # Main pipeline
│   └── retrieval/       # Multi-source retrieval
├── tests/               # Unit & integration tests
├── web/                 # React frontend
├── configs/             # Configuration files
└── docs/               # Documentation
```

## Bug Fixes (2026-09-19)

| Bug | Description | Status |
|-----|-------------|--------|
| Bug 1 | num_pages incorrect | ✅ Fixed |
| Bug 3 | Network resilience (retry, timeout) | ✅ Fixed |
| Bug 5 | Known papers false positives | ✅ Fixed |
| Bug 6 | CIS calculation penalties | ✅ Fixed |
| Bug 7 | Reference parsing (numeric_index) | ✅ Fixed |

## Còn cần làm

- [ ] Chạy real GROBID Docker
- [ ] Dataset thật + annotation
- [ ] Implement baselines B0-B5
- [ ] Error analysis
- [ ] Viết luận văn (Chapter 1-6)

## Contributors

- Nguyễn Bảo Minh (523H0054)
- Trần Gia Thành (523H0096)
- GVHD: ThS. Võ Thị Kim Anh

## License

MIT License
