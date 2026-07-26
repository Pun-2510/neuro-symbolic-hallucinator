# Essay Integrity Checker

> **Hệ thống Neuro-Symbolic hỗ trợ đánh giá độ tin cậy trích dẫn và phát hiện tài liệu tham khảo "ảo giác" trong tiểu luận sinh viên**
>
> *A Neuro-Symbolic System for Citation Integrity Scoring and Hallucinated Reference Detection in Student Essays*

---

## ⚠️ Quyết định cốt lõi (đọc trước)

Hệ thống này **CHỈ kiểm tra trích dẫn** (đánh dấu đỏ nguồn không có thật / bị AI bịa), **KHÔNG chấm điểm toàn bài tiểu luận**.

> **Lưu ý về cách diễn đạt của GVHD:** đề cương có ghi "hệ thống tự động chấm điểm tiểu luận" nhưng 4 mục tiêu / tiêu chí / công nghệ của đề tài đều nói về **citation validation** ("đánh dấu đỏ những nguồn không có thật hoặc bị AI bịa ra"). Skeleton này bám sát phần diễn đạt **citation-only** — khớp với:
> - Mục tiêu: "đánh dấu đỏ những nguồn tài liệu không có thật hoặc bị AI bịa ra"
> - Tiêu chí: "tỷ lệ phát hiện chính xác nguồn tài liệu giả mạo"
> - Công nghệ: regex nâng cao + NLP text similarity + API scholarly
>
> Nếu sau này GVHD thật sự yêu cầu full essay auto-grade, sẽ cần **pivot** thêm 4–6 tuần và viết lại phần lớn pipeline.

- ✅ **TRONG PHẠM VI**: trích xuất citation, xác minh existence + metadata, phân loại 4 nhãn, tính **Citation Integrity Score (CIS)**.
- ❌ **NGOÀI PHẠM VI**: chấm content / organization / language / vocabulary / mechanics, AES rubric, đạo văn, phát hiện toàn văn AI-generated, **tự động kết luận gian lận**.

Mọi đầu ra của hệ thống là **decision-support** cho giảng viên. Giảng viên là người ra quyết định cuối cùng. Mọi màn hình web + mọi report export đều có disclaimer.

---

## Đề tài

- Đồ án tốt nghiệp — Khoa CNTT, **Trường Đại học Tôn Đức Thắng**
- Sinh viên: 523H0054 (Nguyễn Bảo Minh) & 523H0096 (Trần Gia Thành)
- GVHD: ThS. Võ Thị Kim Anh
- Theo đề cương v1.1 đã duyệt (xem `../docs/de_cuong_template.md`)

---

## Kiến trúc tổng quan

```
PDF upload
   │
   ▼
PyMuPDF / pdfplumber parser  ──►  TextPreprocessor
   │
   ▼
CitationExtractor (regex + heuristics)  ──►  Citation[]
   │
   ▼
RetrievalOrchestrator  ──►  Crossref + OpenAlex + Semantic Scholar + arXiv
   │
   ▼
Matching (RapidFuzz + sentence-transformers)  ──►  feature vector
   │
   ▼
NeuroSymbolicChecker (symbolic rules + abstention)  ──►  CitationVerdict
   │
   ▼
CIS aggregator  ──►  CitationIntegrityScore (0–100)
   │
   ▼
AnalysisReport  ──►  JSON / CSV / PDF  +  Web UI
```

GROBID support là **mở rộng tương lai** (đã có adapter slot).

---

## Quick start

```bash
# 1. Tạo môi trường ảo
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Cài dependencies
pip install -r requirements.txt

# 3. Sinh PDF mẫu + gold dataset mồi
python scripts/gen_sample_essays.py
python scripts/gen_gold_dataset.py

# 4. Chạy CLI demo (chạy được end-to-end không cần server)
python -m integrity_checker.pipeline.integrity_pipeline \
    data/essays/essay_02_mixed.pdf --output report.json

# 5. Chạy FastAPI backend
uvicorn integrity_checker.api.main:app --reload

# 6. Chạy frontend (terminal khác)
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

---

## Cấu trúc thư mục (rút gọn)

```
essay-integrity-checker/
├── src/integrity_checker/   # package chính
│   ├── extraction/          # PDF → Citation
│   ├── retrieval/           # Multi-source lookup
│   ├── matching/            # Fuzzy + semantic + features
│   ├── logic/               # Neuro-Symbolic checker + CIS
│   ├── pipeline/            # End-to-end orchestrator
│   ├── api/                 # FastAPI backend
│   ├── db/                  # SQLAlchemy persistence
│   └── evaluation/          # Metrics (tuần 16–17)
├── web/                     # React + Vite + Tailwind + shadcn/ui
├── data/                    # essays/, ground_truth/, cache/
├── scripts/                 # gen_sample_essays, gen_gold_dataset, run_demo
├── tests/                   # unit + integration
├── configs/                 # config.example.yaml
└── docs/                    # (tham chiếu ../docs trong repo gốc)
```

---

## Taxonomy 4 nhãn (đề cương §5.2)

| Nhãn | Ý nghĩa |
|---|---|
| `VERIFIED` | Nguồn tồn tại, title + author + DOI khớp |
| `METADATA_ERROR` | Nguồn có thật nhưng 1+ trường sai (year, author, venue, DOI) |
| `SUSPECTED_HALLUCINATION` | Không tìm thấy candidate qua mọi nguồn, API 200 OK |
| `UNRESOLVED` | Không đủ bằng chứng hoặc dữ liệu mâu thuẫn → hệ thống từ chối kết luận |

---

## APIs sử dụng

| API | Mục đích | Rate limit |
|---|---|---|
| **Crossref** | DOI exact lookup + bibliographic search | 50 req/s (polite pool với email) |
| **OpenAlex** | Title + author + year coverage rộng | generous (User-Agent polite) |
| **Semantic Scholar** | Supplement, citation graph | 100 req/s (optional API key) |
| **arXiv** | Preprint CS/engineering | 3 req/s |

**KHÔNG dùng Google Scholar / SerpAPI** (đề cương đã chốt).

---

## Trạng thái skeleton

Đây là **skeleton + code mồi**: mỗi module có interface + signature + 1 happy-path tối thiểu + `# TODO` rõ ràng. Logic chi tiết sẽ implement theo tuần (xem `../docs/ROADMAP_ZERO_TO_HERO.md`).

Để xem plan đầy đủ đã duyệt: `~/.claude/plans/steady-napping-swan.md`.

---

## Ngoài phạm vi (ghi rõ trong config + UI)

- Chấm điểm content / organization / language / vocabulary / mechanics.
- AES rubric (QWK, holistic scoring).
- Phát hiện đạo văn.
- Phát hiện toàn bộ văn bản do AI tạo.
- Tự động kết luận gian lận học thuật.
- Claim-level verification toàn diện.
- OCR scanned PDF (mở rộng).
- Sách / ISBN (mở rộng).
- Google Scholar / SerpAPI (bị loại).
- GROBID (mở rộng, đã có adapter slot).

---

## Citation

Mọi paper cite hệ thống này, vui lòng tham chiếu đề cương v1.1 + 2 nhóm tác giả:

```
Nguyễn Bảo Minh & Trần Gia Thành (2026).
Hệ thống Neuro-Symbolic hỗ trợ đánh giá độ tin cậy trích dẫn và phát hiện
tài liệu tham khảo ảo giác trong tiểu luận sinh viên.
Đồ án tốt nghiệp, TDTU.
```
