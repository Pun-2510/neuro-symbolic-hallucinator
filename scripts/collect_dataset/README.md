# Dataset Collection Pipeline

Thu thập dữ liệu citation từ arXiv → extract → enrich → format → annotate.

## Cấu trúc

```
scripts/collect_dataset/
├── 01_collect_arxiv.py      # Step 1: Download arXiv PDFs
├── 02_extract_citations.py  # Step 2: GROBID extract citations
├── 03_enrich_crossref.py    # Step 3: Crossref metadata lookup
├── 04_format_gold_dataset.py # Step 4: Format gold_dataset.json + CSV
├── README.md                 # This file

data/
└── raw/
    ├── pdf/                  # Downloaded PDFs (created by step 1)
    └── arxiv_metadata.json   # arXiv paper metadata
```

## Cách chạy

### Bước 1: Download arXiv papers
```bash
# Theo topic (danh sách tự do)
python scripts/collect_dataset/01_collect_arxiv.py \
    --search "ti:machine learning" \
    --n 50 \
    --output data/raw/pdf \
    --delay 3

# Theo arXiv ID cụ thể
python scripts/collect_dataset/01_collect_arxiv.py \
    --ids 2301.12345 2301.23456 2301.34567 \
    --output data/raw/pdf
```

### Bước 2: Extract citations (cần GROBID đang chạy)
```bash
# Start GROBID (Docker)
docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.0

# Extract citations
python scripts/collect_dataset/02_extract_citations.py \
    --pdf-dir data/raw/pdf \
    --output data/citations.json \
    --grobid http://localhost:8070
```

### Bước 3: Enrich với Crossref
```bash
python scripts/collect_dataset/03_enrich_crossref.py \
    --input data/citations.json \
    --output data/citations_enriched.json \
    --delay 0.33
```

### Bước 4: Tạo gold_dataset.json + CSV để annotate
```bash
python scripts/collect_dataset/04_format_gold_dataset.py \
    --input data/citations_enriched.json \
    --output data/gold_dataset.json \
    --csv data/gold_dataset_annotation.csv
```

## Phân công công việc

| Step | Ai làm | Thời gian |
|------|--------|-----------|
| 1. Download papers | **Tự động** (tôi) | 15–30 phút |
| 2. Extract citations | **Tự động** (GROBID) | 15–30 phút |
| 3. Enrich metadata | **Tự động** (Crossref API) | 10–20 phút |
| 4. Format dataset | **Tự động** (tôi) | 1 phút |
| **5. Annotate** | **Thủ công** (bạn) | 2–4 tiếng |

## Cách annotate

1. Mở `gold_dataset_annotation.csv` trong Excel / Google Sheets
2. Mỗi row = 1 citation
3. **Cột `ground_truth_label`:**
   - `verified` → Citation tồn tại, đúng metadata
   - `suspected_hallucination` → Citation không tìm thấy trên Crossref/Google Scholar
   - `metadata_error` → Citation tồn tại nhưng title/author/year sai
   - `unresolved` → Không xác định được
4. **Cột `ground_truth_mapping_status`:**
   - `matched` → Citation khớp (mặc định cho mọi citation trong arXiv paper)
   - `missing_reference` → Có in-text citation nhưng không có reference entry
   - `duplicate_reference` → Trùng lặp
   - `in_text_mismatch` → In-text khác reference list
5. **Cột `annotator`:** Ghi tên người annotate
6. **Cột `notes`:** Ghi chú thêm (tùy)

## arXiv topics gợi ý

| Topic | arXiv category | Notes |
|-------|---------------|-------|
| `cs.CL` | NLP / Computational Linguistics | Nhiều citations |
| `cs.AI` | Artificial Intelligence | Nhiều citations |
| `cs.LG` | Machine Learning | Phổ biến |
| `cs.CV` | Computer Vision | Nhiều citations |
| `eess.IV` | Information Vision | Ít hơn |

## Đề xuất

1. Chạy test với 5 papers trước:
   ```bash
   python scripts/collect_dataset/01_collect_arxiv.py --search "cs.CL" --n 5 --output data/raw/pdf --delay 3
   ```
2. Sau đó chạy full pipeline
3. Annotate 100 citations đầu tiên
4. Tính Cohen's kappa

## Tài liệu tham khảo

- arXiv API: https://info.arxiv.org/help/api/basics.html
- Crossref API: https://api.crossref.org
- GROBID: https://grobid.readthedocs.io
