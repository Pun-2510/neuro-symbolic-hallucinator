# Developer Quickstart

> Cho 2 SV thực hiện đồ án. Đọc file này **trước khi** code.
>
> **Đề cương hiện hành:** v1.2 (chốt với GVHD ngày 2026-08-03, xem `../final (1).docx`).
> So với v1.1, v1.2 thêm 3 cụm: **full-text extraction + GROBID**, **citation style detection**, **bidirectional linking** với 7 trạng thái mapping tách khỏi 4 nhãn nguồn.

## 0. Vài quyết định KHÔNG thay đổi được

- **Decision-support, không tự kết luận gian lận** — giảng viên quyết định cuối. Mọi label là "suspected" / "gợi ý" / "cần kiểm tra".
- **API stack**: Crossref + OpenAlex + Semantic Scholar + arXiv. **KHÔNG** dùng Google Scholar / SerpAPI.
- **PDF parsing (v1.2 — đã thay đổi)**: **GROBID + PyMuPDF + pdfplumber** (GROBID nay đã vào MVP, không còn "mở rộng tương lai").
- **Không chấm toàn bài tiểu luận** — chỉ kiểm tra 3 lớp: style, citation-graph integrity, source verification.
- **"Trích dẫn dư thừa" = `UNCITED_REFERENCE` ∪ `DUPLICATE_REFERENCE`** — KHÔNG mặc định cứng việc trích cùng một nguồn nhiều lần là dư thừa.

## 1. Setup (5 phút)

```bash
cd essay-integrity-checker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## 2. Chạy pipeline (30 giây)

```bash
# Generate sample PDFs
python scripts/gen_sample_essays.py
python scripts/gen_gold_dataset.py

# Run CLI demo
python -m integrity_checker.pipeline.integrity_pipeline \
    data/essays/essay_02_mixed.pdf --output report.json
```

Output mẫu:
```
 ESSAY: essay_02_mixed.pdf
 Pages: 2  |  Citations: 14
 CIS (Citation Integrity Score): 45.5/100  (unresolved: 14)

 Verdicts:
  ? [unresolved] conf=30% raw=...   ← vì API stub, tất cả unresolved
```

> Hiện tại verdict toàn `unresolved` vì **4 API client là stub** (chưa implement). Đây là expected. Sau v1.2 tuần 6–7, output schema sẽ tách thêm **mapping statuses** (MATCHED/MISSING/UNCITED/...) — phần này sẽ xuất hiện trong JSON ngay cả khi chưa có retrieval thật.

## 3. Chạy web (1 phút)

Backend:
```bash
uvicorn integrity_checker.api.main:app --reload
# → http://localhost:8000/api/health
```

Frontend (terminal khác):
```bash
cd web && npm install && npm run dev
# → http://localhost:5173
```

> Lưu ý `web/package.json` hiện thiếu `react-dropzone` — `npm install` sẽ fail ở màn hình Upload. Cần `npm install react-dropzone` trước.

## 4. Chạy tests

```bash
pytest tests/unit/ -v                       # 244 tests (~0.5s, 0 deferred)
pytest tests/integration/ -v                # 13 tests, cần sample PDFs + mock retrieval
pytest tests/integration/test_full_pdf_pipeline_v12.py -v   # 9 tests
```

**Test breakdown (2026-08-25):**

| Module | File test | Pass/Total |
|---|---|---|
| `section_segmenter.py` | `test_section_segmenter.py` | 15/15 |
| `author_parser.py` | `test_author_parser.py` | 27/27 |
| `reference_parser.py` (mở rộng) | `test_reference_parser.py` | 21/21 (backlog #18 closed) |
| `grobid_parser.py` | `test_grobid_parser.py` | 15/15 |
| `style_detector.py` | `test_style_detector.py` | 12/12 |
| `linking/` (tuần 8) | `test_linking_statuses.py` + `test_citation_linker.py` + `test_duplicate_detector.py` | 62/62 |
| `document_parser.py` (tuần 8) | `test_document_parser.py` | 10/10 |
| `retrieval_clients.py` (tuần 8+) | `test_retrieval_clients.py` | 12/12 (4 connectors real HTTP) |
| `pipeline_document_parser.py` (tuần 8+) | `test_pipeline_document_parser.py` | 7/7 (modern + legacy flow) |
| `author_matcher.py` (Sprint 1, task #29) | `test_author_matcher.py` | 19/19 |
| `venue_normalizer.py` (Sprint 2, task #30) | `test_venue_normalizer.py` | 21/21 |
| `source_consensus.py` (Sprint 2, task #31) | `test_source_consensus.py` | 12/12 |
| `fuzzy.py` + `FuzzyTuner` (Sprint 2, task #32) | `test_fuzzy_tuning.py` | 18/18 |
| `rules.py` v1.2 ext (Sprint 2, task #33) | `test_rules_v12.py` | 13/13 |
| `calibration.py` (Sprint 2, task #34) | `test_calibration.py` | 24/24 |
| Integration end-to-end (tuần 8+) | `test_full_pdf_pipeline_v12.py` + `test_pipeline_endtoend.py` | 13/13 |
| Skeleton cũ (v1.1) | nhiều | 63/63 (subset kế thừa, include citation_extractor + author_parser) |

## 5. Lộ trình 18 tuần (v1.2 §5.2)

| Tuần | Giai đoạn | Công việc | Module | Mốc |
|---|---|---|---|---|
| 1–2 | Khảo sát | Chốt vấn đề, literature matrix, scope, style families, taxonomy và schema chung. | — | **M1**: GVHD chốt phạm vi, style families, 2 lớp taxonomy, dữ liệu, tiêu chí nghiệm thu. |
| 3–5 | Dữ liệu | Thu thập / ẩn danh; guideline 3 mức (document / span-link / source); pilot; đo agreement. | `data/ground_truth/` | **M2**: Gold pilot 3 mức đủ tốt; guideline khóa. |
| 6–7 | **Full-text audit** ⭐ | Phân vùng PDF (GROBID + PyMuPDF); in-text/reference extraction; **StyleDetector**; **CitationLinker** + DuplicateDetector + 7 trạng thái. | `extraction/`, `linking/` (MỚI) | — |
| 8–9 | Retrieval | Crossref, OpenAlex, S2, arXiv thật; cache; hợp nhất candidate; tenacity retry. | `retrieval/` | **M3**: PDF → style profile → citation graph → candidate top-K chạy end-to-end trên bộ mẫu. |
| 10–11 | Matching | Fuzzy/embedding features; author/year/venue normalization; consensus; build B0–B5 baselines. | `matching/`, `evaluation/` | — |
| 12–13 | Logic | Symbolic rules cho mapping + nguồn; abstention; calibration; **CIS weights 35/25/25/10/5** real (không còn stub). | `logic/` | **M4**: Có mapping statuses + 4 nhãn nguồn + evidence + abstention + validation report. |
| 14 | IAA | 2 SV cùng annotate; Cohen's kappa / Krippendorff's alpha target ≥ 0.7. | `data/ground_truth/` | — |
| 14–15 | Ứng dụng | Style profile view + citation graph view + override mapping/labels + export PDF/CSV/JSON; Docker. | `web/`, `Dockerfile`, `docker-compose.yml` | **M5**: Web MVP chạy bằng Docker. |
| 16–17 | Thực nghiệm | Baseline B0–B5; ablation; calibration; error analysis theo từng mô-đun; usability test. | `evaluation/` | **M6**: Đóng băng kết quả. |
| 18 | Hoàn thiện | Báo cáo tốt nghiệp, poster, slide, video, rehearsal, đóng gói. | `docs/`, `README.md` | **M7**: Bản nộp + mã nguồn + dữ liệu được phép chia sẻ + video demo. |

### Bảng phân công (v1.2 §5.1)

| SV1 — Document & Application | SV2 — Retrieval & Verification | Chung |
|---|---|---|
| Full-text/PDF parsing (GROBID + PyMuPDF). Phân vùng body/bibliography. **StyleDetector**. In-text extraction. **CitationLinker** + DuplicateDetector. Bounding box + highlight (nếu có). FastAPI/Streamlit. Đánh giá style / span / link. | Scholarly APIs (4 connector thật). Candidate retrieval. Fuzzy/embedding features. Author/year/venue normalization. Source consensus. Logic checker (rules + abstention + calibration). Đánh giá retrieval/classification. | Literature review. Annotation guideline 3 mức. Gán nhãn + IAA. Thiết kế thực nghiệm (B0–B5 + ablation). Tích hợp + viết báo cáo. Demo + bảo vệ. |

## 6. Quy tắc code

- **Mỗi module** có docstring ở đầu file + `# TODO(user, week X):` cho phần cần implement.
- **Mỗi public function/class** có docstring ngắn gọn.
- **Tách 2 lớp output rõ ràng**: không trộn `CitationMappingStatus` (integrity) với `ValidationLabel` (source) trong cùng một dataclass, trừ khi cố ý làm ở layer tổng hợp.
- **Test trước khi commit**: `pytest tests/unit/ -v` phải pass.
- **Git**: nhánh riêng cho mỗi module, PR review lẫn nhau.
- **KHÔNG commit**: `.env`, `data/cache/`, `data/app.db`, `node_modules/`, `.venv/`, essay thật (kể cả đã ẩn danh nếu chưa được phép).

## 7. Mở rộng v1.1 → v1.2 (cần biết)

Đọc `docs/CHANGES_VS_V1.1.md` (sẽ viết trong tuần 1–2) hoặc xem §3 trong `KNOWN_ISSUES_AND_TODO.md`. Tóm tắt:

| Thứ cũ (v1.1) | Nay (v1.2) | Action |
|---|---|---|
| GROBID là mở rộng | MVP must-have | Tạo Docker adapter + client tuần 6–7 |
| Đọc PDF chỉ để trích citation | Đọc toàn văn + phân vùng body/bibliography | Tạo `extraction/section_segmenter.py` tuần 6–7 |
| Style detection ẩn | Document-level style profile + confidence | Tạo `extraction/style_detector.py` tuần 6–7 |
| Mapping 1 chiều hoặc không có | Bidirectional + 7 trạng thái | Tạo `linking/` package tuần 6–7 |
| "Dư thừa" mặc định cứng | `UNCITED ∪ DUPLICATE` | Cập nhật annotation guideline tuần 3–5 |
| CIS weights `45/25/15/10/5` | `35/25/25/10/5` | Đã cập nhật `configs/config.example.yaml` |
| 2 CIS component là stub | Real (tính từ linker + style) | Triển khai tuần 12–13 |
| 1 lớp output (nhãn nguồn) | 2 lớp (integrity + source) | Mở rộng `models/validation.py` tuần 6 |

## 8. Resources

- **Đề cương v1.2** (canonical): `../final (1).docx`.
- **Lit review**: `../docs/NGHIEN_CUU_LITERATURE_REVIEW.md`.
- **Roadmap tổng**: `../docs/ROADMAP_ZERO_TO_HERO.md` (lập theo v1.1, đã bị thay thế một phần).
- **Annotation guideline v2**: `data/ground_truth/annotation_guideline.md` (sẽ viết lại ở tuần 3–5).
- **Sample essays**: `data/essays/README.md`.
- **API docs**:
  - Crossref: https://api.crossref.org
  - OpenAlex: https://docs.openalex.org
  - Semantic Scholar: https://api.semanticscholar.org
  - arXiv: https://arxiv.org/help/api
  - **GROBID** (MỚI trong v1.2): https://grobid.readthedocs.io

## 9. Câu hỏi thường gặp

**Q: Tại sao tất cả citation đều `unresolved` khi chạy demo?**
A: Vì 4 API client là stub (xem `KNOWN_ISSUES_AND_TODO.md` §2.4). Implement thật ở tuần 8–9 sẽ tự động sinh verdict phân hóa.

**Q: CIS có phải điểm tiểu luận không?**
A: KHÔNG. CIS = Citation Integrity Score, chỉ đo phần trích dẫn (integrity + source). Trọng số `35/25/25/10/5` là khởi tạo, sẽ hiệu chỉnh ở tuần 12–13 theo rubric GVHD.

**Q: Hệ thống có tự phát hiện đạo văn / gian lận không?**
A: KHÔNG. Decision-support only; giảng viên là người quyết định cuối. Xem `KNOWN_ISSUES_AND_TODO.md` §5.

**Q: Style "MIXED" và "UNKNOWN" có phải lỗi không?**
A: KHÔNG — đó là cơ chế an toàn khi evidence chưa đủ. MVP chấp nhận cả 2 như output hợp lệ.

**Q: Có nên dùng LLM (GPT-4 / Claude) để parse citation?**
A: Có thể thử ở giai đoạn sau (tuần 16–17) làm **baseline so sánh**. Nhưng pipeline chính vẫn là rule-based (regex + GROBID) để có thể giải thích được.

**Q: Tại sao citation gộp `(Smith, 2020; Doe, 2021)` chỉ được tính 1 link?**
A: CitationLinker tách thành nhiều quan hệ (multi-occurrence). Mỗi occurrence có `CitationLink` riêng; cùng chia sẻ một reference entry.

**Q: DOI resolve được thì đã đủ xác minh chưa?**
A: CHƯA — DOI phân giải được là tín hiệu mạnh, nhưng vẫn phải đối chiếu metadata đích. Logic rule R-DOI-TITLE-MISMATCH xử lý trường hợp DOI trỏ sang bài khác.

**Q: URL/DOI lỗi có nghĩa là nguồn không tồn tại không?**
A: KHÔNG. URL/DOI lỗi là `BROKEN_LINK` — tách riêng khỏi existence verification. Source vẫn có thể tồn tại, có thể chỉ là link tạm thời không truy cập.
