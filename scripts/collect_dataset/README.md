# Dataset Collection Pipeline

Thu thập dữ liệu citation từ arXiv → extract → enrich → format → annotate → split.

## Cấu trúc

```
scripts/collect_dataset/
├── 01_collect_arxiv.py             # Step 1: Download arXiv PDFs (scrape + direct PDF)
├── 02_extract_citations.py          # Step 2: GROBID extract (requires Docker)
├── 02_extract_citations_mupdf.py      # Step 2b: PyMuPDF extract (offline, no Docker)
├── 03_enrich_crossref.py            # Step 3: Crossref API lookup
├── 04_format_gold_dataset.py        # Step 4: gold_dataset.json + annotation CSV
├── 05_compute_iaa.py                # Step 5: Cohen's kappa + Krippendorff's alpha
├── 06_split_dataset.py              # Step 6: train/val/test split
└── README.md                        # This file

data/
├── raw/pdf/                         # Downloaded PDFs (55 papers, ~119MB)
├── arxiv_metadata.json              # arXiv paper metadata
├── citations.json                   # 174 citations (5 papers)
├── citations_full.json              # 2887 citations (55 papers)
├── citations_enriched.json          # Crossref-enriched (5 papers)
├── citations_full_enriched.json     # Crossref-enriched (55 papers, in progress)
├── gold_dataset.json                # Full structured dataset
├── gold_dataset_annotation.csv      # CSV for human annotation
├── gold_dataset_train.json          # 70% split
├── gold_dataset_val.json            # 15% split
├── gold_dataset_test.json           # 15% split
└── data_split_manifest.json         # Split metadata
```

## Cách chạy (pipeline hoàn chỉnh)

### Bước 1: Download arXiv papers
```bash
# Theo topic
python scripts/collect_dataset/01_collect_arxiv.py \
    --search "cs.CL" --n 50 --output data/raw/pdf --delay 2

# Theo arXiv ID cụ thể
python scripts/collect_dataset/01_collect_arxiv.py \
    --ids 1810.04805 1706.03762 --output data/raw/pdf
```

### Bước 2: Extract citations
```bash
# PyMuPDF (offline, no Docker) — RECOMMENDED
python scripts/collect_dataset/02_extract_citations_mupdf.py \
    --pdf-dir data/raw/pdf --output data/citations_full.json --overwrite

# Hoặc GROBID (nếu có Docker)
docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.0
python scripts/collect_dataset/02_extract_citations.py \
    --pdf-dir data/raw/pdf --output data/citations.json --grobid http://localhost:8070
```

### Bước 3: Enrich Crossref
```bash
python scripts/collect_dataset/03_enrich_crossref.py \
    --input data/citations_full.json \
    --output data/citations_full_enriched.json \
    --delay 0.15
```

### Bước 4: Format gold_dataset
```bash
python scripts/collect_dataset/04_format_gold_dataset.py \
    --input data/citations_full_enriched.json \
    --output data/gold_dataset.json \
    --csv data/gold_dataset_annotation.csv
```

### Bước 5: Annotate (THỦ CÔNG)
Mở `data/gold_dataset_annotation.csv` trong Google Sheets / Excel.

### Bước 6: Tính IAA
```bash
# 2 annotators → Cohen's kappa
python scripts/collect_dataset/05_compute_iaa.py \
    --csv data/gold_dataset_annotation.csv \
    --annotator1 student_A \
    --annotator2 student_B

# → data/iaa_report.json
```

### Bước 7: Split train/val/test
```bash
# Split by paper (tránh citation leakage)
python scripts/collect_dataset/06_split_dataset.py \
    --input data/gold_dataset.json \
    --output data/ \
    --split-by paper \
    --train 0.7 --val 0.15 --test 0.15 \
    --seed 42

# → gold_dataset_train.json / val / test + data_split_manifest.json
```

## Phân công

| Step | Ai làm | Thời gian |
|------|--------|-----------|
| 1. Download papers | ✅ Tự động | 15–30 phút |
| 2. Extract citations | ✅ Tự động | 10–15 phút |
| 3. Enrich Crossref | ✅ Tự động | 15–30 phút |
| 4. Format dataset | ✅ Tự động | 1 phút |
| **5. Annotate** | ⚠️ **Thủ công** | 2–4 tiếng |
| 6. IAA | ✅ Tự động | 1 phút |
| 7. Split | ✅ Tự động | 1 phút |

## Annotation schema

**Cột `ground_truth_label`:**
- `verified` — Citation tồn tại, đúng metadata
- `suspected_hallucination` — Citation không tìm thấy
- `metadata_error` — Tồn tại nhưng title/author/year sai
- `unresolved` — Không xác định được

**Cột `ground_truth_mapping_status`:**
- `matched` — Khớp (default)
- `missing_reference` — In-text không có reference entry
- `duplicate_reference` — Trùng lặp
- `in_text_mismatch` — In-text ≠ reference list
- `unresolved` — Không xác định

## arXiv topics

`cs.CL` `cs.AI` `cs.LG` `cs.CV` `cs.NE` `cs.IR` `cs.CL`
