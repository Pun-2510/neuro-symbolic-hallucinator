# Developer Quickstart

> Cho 2 SV thực hiện đồ án. Đọc file này **trước khi** code.

## 0. Vài quyết định KHÔNG thay đổi được

- **Citation-only** (đề cương v1.1 đã duyệt). KHÔNG chấm điểm toàn bài.
- **API stack**: Crossref + OpenAlex + Semantic Scholar + arXiv. KHÔNG Google Scholar / SerpAPI.
- **PDF parsing**: PyMuPDF + pdfplumber. GROBID bỏ MVP (để adapter slot).
- **Decision-support**: hệ thống không tự kết luận gian lận — giảng viên quyết định cuối.

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

> **Lưu ý**: hiện tại verdict toàn `unresolved` là do **4 API client là stub** (chưa implement). Đây là expected. Xem mục 5 để biết implement tuần nào.

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

## 4. Chạy tests

```bash
pytest tests/unit/ -v            # 29 tests, ~0.2s
pytest tests/integration/ -v     # 8 tests, cần sample PDFs, ~40s
```

## 5. Lộ trình 18 tuần — tuần nào làm gì

| Tuần | Nội dung | Module |
|---|---|---|
| 1–2 | EDA, đọc lit review, thu thập tiểu luận mẫu thật | — |
| 3 | CitationExtractor hoàn chỉnh, author parsing | `extraction/` |
| 4–5 | Regex patterns (APA/MLA/IEEE/Chicago/Vietnamese) | `extraction/regex_patterns.py` |
| 6 | Reference list parser đa style | `extraction/reference_parser.py` |
| 7 | Pipeline orchestrator | `pipeline/integrity_pipeline.py` |
| 8 | **Mid-term demo** — pipeline end-to-end trên 20 PDF | — |
| 9 | CrossrefClient thật | `retrieval/crossref_client.py` |
| 10 | OpenAlex + Semantic Scholar + arXiv clients | `retrieval/{openalex,semantic_scholar,arxiv}_client.py` |
| 11 | Author parsing chuẩn, fuzzy/semantic tuning | `matching/` |
| 12 | Symbolic rules tuning (decision table) | `logic/rules.py` |
| 13 | CIS weights optimization trên validation set | `logic/cis.py` |
| 14 | IAA: 2 SV cùng annotate 100 citation, tính Cohen's kappa | `data/ground_truth/` |
| 15 | Web UI polish, shadcn components đầy đủ | `web/src/components/ui/` |
| 16 | Baselines B0–B4, đo P/R/F1 trên gold dataset | `evaluation/` |
| 17 | Final experiments + viết thesis Ch. 4 (Results) | — |
| 18 | **Bảo vệ** | — |

## 6. Quy tắc code

- **Mỗi module** có docstring ở đầu file + `# TODO(user, week X):` cho phần cần implement.
- **Mỗi public function/class** có docstring ngắn gọn.
- **Test trước khi commit**: `pytest tests/unit/ -v` phải pass.
- **Git**: nhánh riêng cho mỗi module, PR review lẫn nhau.
- **KHÔNG commit**: `.env`, `data/cache/`, `data/app.db`, `node_modules/`, `.venv/`.

## 7. Resources

- **Đề cương v1.1** (canonical source): `../docs/de_cuong_template.md`
- **Lit review**: `../docs/NGHIEN_CUU_LITERATURE_REVIEW.md`
- **Roadmap**: `../docs/ROADMAP_ZERO_TO_HERO.md`
- **Annotation guideline**: `data/ground_truth/annotation_guideline.md`
- **Sample essays**: `data/essays/README.md`
- **API docs của các nguồn**:
  - Crossref: https://api.crossref.org
  - OpenAlex: https://docs.openalex.org
  - Semantic Scholar: https://api.semanticscholar.org
  - arXiv: https://arxiv.org/help/api

## 8. Câu hỏi thường gặp

**Q: Tại sao tất cả citation đều `unresolved` khi chạy demo?**
A: Vì 4 API client là stub (TODO tuần 9–10). Implement thật sẽ tự động sinh verdict phân hóa.

**Q: Tại sao bỏ GROBID?**
A: Theo quyết định chốt 2B. Adapter slot đã có sẵn — muốn dùng lại chỉ cần tạo `GrobidParser(BasePDFParser)`.

**Q: Tại sao không dùng Google Scholar?**
A: Không có API công khai chính thức; SerpAPI tốn tiền + vi phạm TOS. Đề cương đã chốt dùng 4 nguồn trên.

**Q: Có nên dùng LLM (GPT-4 / Claude) để parse citation?**
A: Có thể thử ở giai đoạn sau (tuần 11–12) làm **baseline B5** so với Neuro-Symbolic. Nhưng pipeline chính vẫn là rule-based để có thể giải thích được.

**Q: CIS là gì, có phải điểm tiểu luận không?**
A: KHÔNG. CIS = Citation Integrity Score, chỉ đo phần trích dẫn. Trọng số mặc định trong `configs/config.example.yaml` sẽ tối ưu lại ở tuần 13.