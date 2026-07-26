# Sample Essays — `/data/essays/`

5 PDF tiểu luận mẫu để chạy pipeline end-to-end và đo P/R sơ bộ.

Được sinh tự động bởi `scripts/gen_sample_essays.py` (dùng ReportLab).

## Phân bố

| File | Loại | Mục đích test |
|---|---|---|
| `essay_01_real_only.pdf` | 5 citation thật (DOI crossref-resolvable) | Control — pipeline nên trả tất cả VERIFIED |
| `essay_02_mixed.pdf` | 2 thật + 1 metadata_error (year sai) + 1 fabricated | Mixed — kiểm tra 3 nhãn khác nhau |
| `essay_03_fabricated.pdf` | 3 citation bịa (DOI/author/venue fake) | Kiểm tra nhãn SUSPECTED_HALLUCINATION |
| `essay_04_real_small.pdf` | 2 citation thật, citation ít | Kiểm tra edge case: essay ngắn |
| `essay_05_edge_doi_only.pdf` | Chỉ có DOI trong in-text, không có author/year | Kiểm tra edge case: trích xuất từ DOI-only |

## Citation thật được dùng

| # | Authors | Year | Title | DOI |
|---|---|---|---|---|
| 1 | Vaswani et al. | 2017 | Attention is all you need | 10.48550/arXiv.1706.03762 |
| 2 | Devlin et al. | 2019 | BERT | 10.18653/v1/N19-1423 |
| 3 | He et al. | 2016 | Deep residual learning | 10.1109/CVPR.2016.90 |
| 4 | Brown et al. | 2020 | GPT-3 | 10.48550/arXiv.2005.14165 |
| 5 | LeCun et al. | 2015 | Deep learning (Nature) | 10.1038/nature14539 |

## Citation fabricated (DOI/author/venue fake)

| # | Authors | Year | Title | DOI |
|---|---|---|---|---|
| F1 | Smith & Doe | 2024 | "novel framework..." | 10.9999/jiar.2024.9999 |
| F2 | Nguyen et al. | 2023 | "citation integrity..." | 10.5555/hcea.2023.5.100 |
| F3 | Anderson & Brown | 2025 | "reference hallucination..." | 10.0000/njai.2025.001 |

## Cách chạy

```bash
# Tạo lại file (sau khi chỉnh scripts/gen_sample_essays.py)
python scripts/gen_sample_essays.py

# Chạy pipeline trên từng file
for f in data/essays/*.pdf; do
    python -m integrity_checker.pipeline.integrity_pipeline "$f" \
        --output "data/cache/$(basename "$f" .pdf).report.json"
done
```

## Lưu ý

- Đây là dữ liệu MỒI cho việc test ban đầu. **Gold dataset thật sẽ do 2 SV tự annotate** theo `data/ground_truth/annotation_guideline.md`.
- Để đo IAA, dùng `data/ground_truth/iaa_template.csv`.