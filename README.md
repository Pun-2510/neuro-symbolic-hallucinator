# Essay Integrity Checker

> **Hệ thống Neuro-Symbolic hỗ trợ đánh giá tính toàn vẹn trích dẫn và phát hiện tài liệu tham khảo "ảo giác" trong tiểu luận sinh viên**
>
> *A Neuro-Symbolic System for Citation Integrity Assessment and Hallucinated Reference Detection in Student Essays*

---

## Quyết định cốt lõi (đọc trước)

Đề cương đã được chốt với GVHD theo **v1.2** (xem `final (1).docx`). Hệ thống đọc **toàn văn** tiểu luận, suy luận **kiểu trích dẫn ở mức tài liệu**, đối chiếu **hai chiều** giữa in-text citations và danh mục tài liệu tham khảo, rồi xác minh sự tồn tại và metadata của từng nguồn. Hai lớp kết quả được tách rời:

1. **Tính nhất quán nội bộ (citation integrity)** — không phải đạo văn, không phải hallucination; chỉ trả lời "trích dẫn trong bài có khớp với danh mục tham khảo không".
2. **Độ tin cậy nguồn (source verification)** — nguồn đó có thật không, metadata có khớp không.

Hệ thống **KHÔNG chấm điểm toàn bài tiểu luận**, **KHÔNG tự kết luận gian lận**, **KHÔNG kiểm chứng claim-level** (xem §6).

> **Về cách hiểu "trích dẫn dư thừa"**: dư thừa chỉ khi reference entry **không có in-text occurrence** (orphan/uncited) hoặc **nhiều entry trỏ cùng một công trình** (duplicate). Trích cùng một nguồn nhiều lần trong các đoạn khác nhau **không** mặc định là dư thừa.

> **Triết lý an toàn**: mọi cảnh báo đều kèm bằng chứng; mọi trường hợp chưa chắc chắn được tách riêng (`UNRESOLVED` / `AMBIGUOUS_MAPPING`) và chuyển cho giảng viên; mọi quyết định đều ghi rule đã kích hoạt, điểm từng trường và source provenance để tái kiểm tra.

---

## Đề tài

- Đồ án tốt nghiệp — Khoa CNTT, **Trường Đại học Tôn Đức Thắng (TDTU)**
- Sinh viên: 523H0054 (Nguyễn Bảo Minh) & 523H0096 (Trần Gia Thành)
- GVHD: ThS. Võ Thị Kim Anh
- Theo **đề cương v1.2 đã chốt với GVHD** (xem `final (1).docx`)

---

## Kiến trúc tổng quan (đặc tả v1.2)

```
PDF upload
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Tầng 1 — Full-text extraction (§3.4)                        │
│   PyMuPDF + pdfplumber (luôn luôn) + GROBID (cho MVP)        │
│   Phân vùng body / appendix / footnote / bibliography        │
│   Phát hiện in-text spans  + bounding box                   │
│   Tách reference entries  + trích fields                    │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Tầng 2 — Style inference + Bidirectional linking (§3.5)     │
│   StyleDetector → {APA-like, IEEE-like, MIXED, UNKNOWN}+conf │
│   CitationLinker → 2 chiều in-text ↔ reference entry         │
│   Mapping statuses:                                          │
│     MATCHED · MISSING_REFERENCE · UNCITED_REFERENCE          │
│     IN_TEXT_MISMATCH · DUPLICATE_REFERENCE ·                 │
│     AMBIGUOUS_MAPPING · STYLE_INCONSISTENT                   │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Tầng 3 — Multi-source candidate retrieval (§3.6)            │
│   Crossref · OpenAlex · Semantic Scholar · arXiv             │
│   cache + retry + backoff + rate limit per source            │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Tầng 4 — Matching + Neuro-Symbolic checker (§3.7–3.8)       │
│   7 feature groups: identifier / title-lexical /             │
│     title-semantic / author / year-venue / source consensus  │
│     / retrieval rank                                         │
│   Symbolic rules + abstention band → Decision               │
└──────────────────────────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Tầng 5 — Báo cáo (§3.9, §4.3)                              │
│   CitationMappingStatus (integrity) – độc lập                │
│   ValidationLabel nguồn (4 nhãn) – độc lập                   │
│   CIS = 5 components, weights (35/25/25/10/5)               │
│   Evidence layer + human override                            │
└──────────────────────────────────────────────────────────────┘
```

**Điểm mới so với v1.1:**
- Tầng 1 bắt buộc đọc full-text + GROBID (v1.1 để GROBID là "mở rộng").
- Tầng 2 hoàn toàn mới: style detection ở document level + bidirectional linking.
- Tầng 5 tách đôi output: integrity vs source.
- "Dư thừa" được định nghĩa thao tác (uncited / duplicate), không mặc định cứng theo số lần trích.

---

## Quick start

```bash
# 1. Tạo môi trường ảo
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Cài dependencies
pip install -r requirements-dev.txt

# 3. Sinh PDF mẫu + gold dataset mồi
python scripts/gen_sample_essays.py
python scripts/gen_gold_dataset.py

# 4. Chạy CLI demo (chạy được end-to-end; kết quả UNRESOLVED cho đến khi 4 API client thật)
python -m integrity_checker.pipeline.integrity_pipeline \
    data/essays/essay_02_mixed.pdf --output report.json

# 5. Chạy FastAPI backend
uvicorn integrity_checker.api.main:app --reload

# 6. Chạy frontend
cd web && npm install && npm run dev
# → http://localhost:5173
```

Hoặc dùng Makefile:
```bash
make setup    # create venv + install
make sample   # generate sample essays + gold dataset
make demo     # run CLI demo
make api      # run FastAPI server
make web      # run Vite dev server
make test     # run pytest
```

> **Trạng thái dự kiến sau khi `make demo`** trong giai đoạn skeleton: trích xuất & mapping có dữ liệu (style profile, in-text spans, reference entries, mapping statuses); phần xác minh nguồn sẽ trả `UNRESOLVED` đến khi 4 API client được nối thật (tuần 8–9).

---

## Cấu trúc thư mục (rút gọc theo v1.2)

```
essay-integrity-checker/
├── src/integrity_checker/   # package chính
│   ├── extraction/          # Tầng 1: PDF → Page/Section/Span/Entry
│   ├── linking/             # Tầng 2b: CitationLinker, DuplicateDetector, StyleDet… (MỚI)
│   ├── retrieval/           # Tầng 3: multi-source
│   ├── matching/            # Tầng 4: features + consensus
│   ├── logic/               # Tầng 4: rules + CIS + calibration
│   ├── pipeline/            # End-to-end orchestrator
│   ├── api/                 # FastAPI backend
│   ├── db/                  # SQLAlchemy persistence
│   ├── models/              # Citation, SourceResult, MappingStatus, CISComponents…
│   └── evaluation/          # Metrics + baselines B0–B5 (tuần 16–17)
├── web/                     # React + Vite + Tailwind + shadcn/ui
├── data/                    # essays/, ground_truth/, cache/
├── scripts/                 # gen_sample_essays, gen_gold_dataset, run_demo
├── tests/                   # unit + integration
├── configs/                 # config.example.yaml (đã cập nhật v1.2 weights)
└── docs/                    # (tham chiếu ../docs)
```

---

## Hai lớp kết quả (đặc tả v1.2, §3.2.2)

Hệ thống xuất **hai nhóm kết quả tách rời** cho mỗi reference entry:

### Lớp 1 — Citation integrity (`CitationMappingStatus`, 7 trạng thái)

| Trạng thái | Nghĩa |
|---|---|
| `MATCHED` | In-text ánh xạ duy nhất tới reference entry và các khóa cốt lõi nhất quán. |
| `MISSING_REFERENCE` | Có in-text nhưng không có reference entry tương ứng. |
| `UNCITED_REFERENCE` | Reference entry không có in-text occurrence hợp lệ sau khi loại trừ vùng không tính. |
| `IN_TEXT_MISMATCH` | Có candidate liên kết rõ nhưng author/year/số thứ tự/hậu tố không nhất quán. |
| `DUPLICATE_REFERENCE` | Hai entry nhiều khả năng trỏ cùng một công trình. |
| `AMBIGUOUS_MAPPING` | ≥2 candidate hợp lý hoặc chuỗi mơ hồ — không liên kết chắc chắn. |
| `STYLE_INCONSISTENT` | Occurrence lệch khỏi style chủ đạo mà không có lý do rõ. |

> **"Dư thừa" trong v1.2 = `UNCITED_REFERENCE` ∪ `DUPLICATE_REFERENCE`**. Một nguồn được trích nhiều lần trong các đoạn khác nhau **không** bị gộp thành "dư thừa".

### Lớp 2 — Source verification (`ValidationLabel`, 4 nhãn)

| Nhãn | Nghĩa |
|---|---|
| `VERIFIED` | Có scholarly record phù hợp; các trường cốt lõi khớp trong sai số cho phép. |
| `METADATA_ERROR` | Nguồn có thật nhưng ≥1 trường khai báo sai đáng kể (year, author, venue, DOI trỏ sang bài khác). |
| `SUSPECTED_HALLUCINATION` | Không tìm thấy record tương ứng sau quy trình truy hồi đa nguồn + manual protocol; chỉ dán nhãn khi các nguồn dữ liệu hoạt động bình thường. |
| `UNRESOLVED` | Không đủ evidence (API lỗi, tài liệu hiếm, candidate cạnh tranh, điểm biên). |

> Nguyên tắc an toàn: **"không tìm thấy"** chỉ thành `SUSPECTED_HALLUCINATION` khi đã chạy đủ chiến lược + API khỏe; nếu không thỏa → `UNRESOLVED`.

---

## Citation style detection (đặc tả v1.2, §3.5)

StyleDetector trả về **profile ở mức tài liệu**, kèm confidence và đặc trưng hỗ trợ:

| Nhãn | Tín hiệu trong thân bài | Tín hiệu trong danh mục |
|---|---|---|
| `APA-like` | `(Nguyen, 2024)`, `Nguyen et al. (2024)` | Thường sắp theo tác giả; năm gần tác giả; không bắt buộc đánh số. |
| `IEEE-like` | `[3]`, `[2]-[5]`, `[1, 4]` | Mục đánh số; mapping theo index, thường theo thứ tự xuất hiện. |
| `MIXED` | Hai họ marker cùng xuất hiện đáng kể hoặc thay đổi theo vùng. | Danh mục và thân bài dùng cấu trúc không nhất quán. |
| `UNKNOWN` | Quá ít bằng chứng, marker mơ hồ hoặc style ngoài phạm vi. | Danh mục thiếu/không chuẩn hoặc không đủ đặc trưng. |

> Hai nhóm tín hiệu (thân bài & bibliography) được kết hợp; nếu xung đột hoặc quá ít occurrence → `MIXED/UNKNOWN` thay vì ép về APA/IEEE.

---

## Citation Integrity Score (đặc tả v1.2, §3.9)

CIS là **điểm hỗ trợ theo rubric, KHÔNG phải điểm toàn bài**. Báo cáo hiển thị **riêng** hai nhóm thành phần (integrity vs source) rồi mới tổng hợp nếu GVHD chấp thuận.

```
CIS = 100 × (Σ wⱼ · mⱼ · sⱼ) / (Σ wⱼ · mⱼ)
mⱼ = 1 nếu thành phần j có đủ dữ liệu, 0 nếu thiếu.
```

| Thành phần | Trọng số khởi tạo | Cách đo |
|---|---|---|
| Tỷ lệ nguồn xác minh được | **35%** | Tỷ lệ `VERIFIED` trên các nguồn đã có đủ evidence. |
| Độ chính xác metadata | **25%** | Mức khớp title / author / year / venue / identifier. |
| Đối chiếu hai chiều | **25%** | Coverage in-text→ref và ref→in-text; phạt `MISSING/UNCITED/MISMATCH/DUPLICATE` theo rubric. |
| Tính nhất quán kiểu trích dẫn | **10%** | Mức phù hợp với style profile; **không** thay thế bộ kiểm tra APA/IEEE đầy đủ. |
| Định danh/đường dẫn | **5%** | DOI/URL hợp lệ; broken link chỉ là tín hiệu phụ. |

> Trọng số là giả định khởi tạo. Nếu CIS được dùng trong đánh giá thật, phải hiệu chỉnh theo rubric và báo cáo Spearman / weighted kappa / MAE với giảng viên.

---

## APIs / nguồn tham khảo

| API | Mục đích |
|---|---|
| **Crossref** | DOI exact lookup + bibliographic search |
| **OpenAlex** | Title + author + year coverage rộng |
| **Semantic Scholar** | Supplement, citation graph |
| **arXiv** | Preprint CS/engineering |

Mỗi connector chạy qua interface chung nên có thể tạm ngừng / thay nguồn mà không hỏng pipeline. **KHÔNG dùng Google Scholar / SerpAPI** (đề cương đã chốt).

---

## Trạng thái hiện tại

Repo hiện đang ở **v1.2 — MVP kỹ thuật** (cập nhật trạng thái ngày 2026-09-12). Pipeline lõi đã chạy end-to-end với mock/injectable integrations; phần còn thiếu chủ yếu là real GROBID Docker verification, dataset/annotation thật, baseline và đánh giá đồ án.

- ✅ **Có sẵn**: 4 lớp nhãn nguồn; multi-source retrieval thật (Crossref/OpenAlex/S2/arXiv); matching layer với 7 feature groups; symbolic rules + calibration; FastAPI + React/Vite UI; SQLite/Postgres-compatible configuration; sample essays + gold set mồi.
- ✅ **Hoàn thành tuần 6 (2026-08-10 đến 2026-08-15)**:
  - `extraction/section_segmenter.py` — phân vùng body / bibliography / appendix / footnote / figure caption (15/15 tests).
  - `matching/author_parser.py` — chuẩn hoá last-name + initials + Dutch + Vietnamese + suffix (27/27 tests).
  - `extraction/reference_parser.py` (mở rộng) — APA + IEEE + Vancouver parsers, trích title + numeric_index + year_suffix + order_index (21/21 tests — backlog #18 closed).
  - `extraction/grobid_parser.py` — TEI XML parser (defusedxml XXE-safe) + HTTP client injectable + SHA256 cache (15/15 tests).
- ✅ **Hoàn thành tuần 7 (2026-08-17)**:
  - `extraction/style_detector.py` — document-level style profile (APA-like / IEEE-like / MIXED / UNKNOWN) + confidence + features + ratios + explanation (12/12 tests).
- ✅ **Hoàn thành tuần 8 (2026-08-24)**:
  - `linking/` package — `statuses.py` + `citation_linker.py` + `duplicate_detector.py` (62 tests pass).
  - `extraction/document_parser.py` — orchestrator PDF → muPDF + GROBID (10 tests pass).
  - 4 API client thật — Crossref/OpenAlex/S2/arXiv với Tenacity retry + cache + polite pool.
- ✅ **Hoàn thành Sprint 1 — Tuần 9 (2026-08-25)**:
  - **Output schema tách integrity vs source** (`CitationVerdict.mapping_status` + `CitationMappingStatus` enum) + `AnalysisReport.linking_summary`.
  - **CIS real components** — `CISCalculator.compute()` nhận `linking_result` + `style_profile`, tính `in_text_bib_consistency` từ `LinkingResult.links` với `MAPPING_PENALTIES`, tính `format_consistency` từ `StyleProfile`.
  - **Author matching** — `matching/author_matcher.py` với diacritics-fold + particle strip + last-name canonical.
- ✅ **Hoàn thành Sprint 2 — Tuần 10–11 (2026-08-25)**:
  - **VenueNormalizer** — `matching/venue_normalizer.py` với ISSN + 24-entry dict + fuzzy fallback.
  - **Source consensus** — `matching/source_consensus.py` với `analyze_consensus()` trả `independent_source_count`.
  - **Fuzzy threshold tuning** — `FuzzyTuner.evaluate()` + `find_optimal_abstention_threshold()`.
  - **Rules extension** — `R-STYLE-INCONSISTENT` + `R-AMBIGUOUS-MAPPING` + `R-DOMAIN-EXCEPTION` trong `logic/rules.py`.
  - **Calibration metrics** — `logic/calibration.py` full Brier + ECE + coverage-accuracy implementation.
- ✅ **Đã hoàn thành sau đó**:
  - `ExplanationGenerator` tiếng Việt có cấu trúc + 43 unit tests.
  - Web UI style profile, citation graph, evidence drawer, override controls và export PDF/CSV/JSON.
  - GROBID mock integration: 16 pass, 4 real-Docker tests được skip khi Docker/OOM chưa sẵn sàng.
- 🔄 **Còn lại để hoàn thiện đồ án**:
  - Dataset thật 3 mức + annotation guideline v2 + IAA thực tế.
  - Baselines B0–B5 và bộ test/đánh giá tương ứng.
  - Real GROBID Docker run trên máy đủ RAM.
  - Error analysis, usability study, API hardening và tài liệu/luận văn.

**Test count xác nhận ngày 2026-09-12:** **467 passed, 4 skipped** bằng `.venv/bin/python -m pytest -q`. Frontend `npm run build` cũng pass.

---

## 6 câu hỏi nghiên cứu (v1.2 §1.5)

| ID | Câu hỏi |
|---|---|
| RQ1 | Có thể nhận diện APA-like / IEEE-like / MIXED / UNKNOWN từ đặc trưng toàn văn + bibliography với độ chính xác nào; mỗi nhóm đặc trưng đóng góp ra sao? |
| RQ2 | Hệ thống trích xuất và liên kết hai chiều in-text ↔ reference entry chính xác đến mức nào, đặc biệt với `MISSING/UNCITED/MISMATCH/DUPLICATE`/mapping mơ hồ? |
| RQ3 | Truy hồi đa nguồn có cải thiện Recall@K và giảm trường hợp bỏ sót nguồn thật so với chỉ dùng một cơ sở dữ liệu hay không? |
| RQ4 | Phương pháp Neuro-Symbolic có cải thiện Macro-F1 và precision lớp `SUSPECTED_HALLUCINATION` so với fuzzy / embedding / ML classifier độc lập hay không? |
| RQ5 | Cơ chế `UNRESOLVED` / `AMBIGUOUS_MAPPING` và abstention ảnh hưởng thế nào đến trade-off coverage–accuracy ở cả liên kết nội văn và xác minh nguồn? |
| RQ6 | Báo cáo hai lớp evidence và CIS có giúp giảng viên rà soát nhanh hơn và đồng thuận hơn so với quy trình thủ công hay không? |

---

## Ngoài phạm vi (v1.2, ghi rõ trong config + UI)

- Chấm điểm content / organization / language / vocabulary / mechanics.
- AES rubric (QWK, holistic scoring).
- Phát hiện đạo văn.
- Phát hiện toàn bộ văn bản do AI tạo.
- **Tự động kết luận gian lận học thuật**.
- **Claim-level verification toàn diện** (câu văn có được nguồn hỗ trợ về ngữ nghĩa không — không thuộc MVP).
- OCR scanned PDF (mở rộng).
- Sách / ISBN (mở rộng).
- Highlight trực tiếp lên PDF (mở rộng).
- Google Scholar / SerpAPI (bị loại).

---

## Citation

Mọi paper cite hệ thống này, vui lòng tham chiếu đề cương v1.2 + 2 nhóm tác giả:

```
Nguyễn Bảo Minh & Trần Gia Thành (2026).
Hệ thống Neuro-Symbolic hỗ trợ đánh giá tính toàn vẹn trích dẫn
và phát hiện tài liệu tham khảo ảo giác trong tiểu luận sinh viên.
Đồ án tốt nghiệp, TDTU.
```
