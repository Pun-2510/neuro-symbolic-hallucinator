# Kế hoạch: Tích hợp GROBID làm nguồn trích xuất cấu trúc chính

**Ngày lập:** 30/09/2026  
**Ngày bắt đầu code:** 01/10/2026  
**Trạng thái:** Đã thống nhất — chưa bắt đầu triển khai code

## 1. Bối cảnh

Hiện tại pipeline dùng ba nguồn nhưng chưa có lớp hợp nhất hoàn chỉnh:

```text
PDF → PyMuPDF (text/page) + GROBID (TEI/metadata) + Regex (patterns/fallback)
                         ↓
             DocumentParser → Linker → Retrieval/Rules → CIS
```

GROBID đã có parser TEI cơ bản và được ưu tiên ở một số trường bibliography, nhưng output chưa được chuyển đầy đủ thành model nội bộ `Citation`, dữ liệu `Reference` và evidence cho `StyleFeatures`. Vì vậy regex vẫn phải parse lại nhiều dữ liệu; citation links từ TEI (`xml:id`/`ref`) chưa được tận dụng tối đa; provenance của từng trường chưa rõ.

## 2. Quyết định kiến trúc

**Nên xây adapter GROBID, nhưng không xóa toàn bộ regex.**

```text
GROBID       = structured extraction chính: metadata, sections, references, links
PyMuPDF      = text layer, page number, coordinates
Regex        = style evidence, citation bổ sung, validation, fallback
CitationLinker= mapping và quan hệ in-text ↔ reference
Rule engine  = verification, statuses, CIS
```

Adapter chỉ chuẩn hóa dữ liệu, không chấm điểm, không gọi retrieval và không tự kết luận integrity. Chiến lược là **merge**, không phải replace mù quáng.

## 3. Mục tiêu

- Chuyển `GrobidOutput` thành `Citation[]` reference-list và in-text.
- Giữ nguyên `xml:id`/`ref` để map trực tiếp citation ↔ reference.
- Hỗ trợ citation trỏ nhiều reference như `[1, 2]`.
- Merge GROBID với regex/PyMuPDF, không mất citation bị GROBID bỏ sót.
- Ghi rõ provenance (`grobid`, `regex`, `merged`) và conflict.
- Giữ fallback 100% khi Docker/GROBID lỗi, timeout, empty hoặc malformed TEI.
- StyleDetector vẫn phân loại `APA-like`, `IEEE-like`, `MIXED`, `UNKNOWN`; GROBID chỉ cung cấp evidence.
- In-text chỉ dùng cho linking/style; không gọi API verification nếu thiếu metadata.
- `verdicts[]` chỉ chứa reference entries có thể verify; CIS không tính nhầm in-text.

## 4. Phạm vi

### Trong phạm vi

1. Adapter `GrobidOutput → Citation[]`.
2. Chuẩn hóa bibliography: author, title, year, venue, DOI, volume, issue, pages.
3. Chuẩn hóa in-text citation và TEI link IDs.
4. Merge, dedupe, conflict diagnostics và provenance.
5. Tích hợp `DocumentParser`, `CitationLinker`, style evidence và pipeline.
6. Unit/integration/regression/evaluation.

### Ngoài phạm vi

- Fine-tune hoặc thay đổi model Java/GROBID image.
- OCR scanned PDF.
- Claim-level verification.
- Xóa toàn bộ regex patterns.
- Thay đổi retrieval provider không liên quan.
- Thiết kế UI lớn ngoài các field provenance cần thiết.

## 5. Thiết kế dữ liệu

Kiểm tra bổ sung backward-compatible vào `models/citation.py` (hoặc metadata nội bộ trước):

```python
source: Literal["grobid", "regex", "pymupdf", "merged"] = "regex"
source_confidence: float | None = None
grobid_ref_id: str | None = None
is_grobid_linked: bool = False
conflict_fields: list[str] = field(default_factory=list)
```

Quy ước:

- Normalize `xml:id`/`ref` về một dạng ổn định.
- Tạo map `grobid_ref_id → Citation.reference_id`.
- Không dùng số thứ tự hiển thị làm khóa duy nhất khi TEI có ID.
- Giữ `citation_links: list` cho multi-reference.
- DOI là khóa ưu tiên; sau đó normalized title + author + year; cuối cùng mới raw text/fuzzy.

`StyleFeatures` nhận thêm evidence như author-year count, numeric count, linked/unlinked count và sample raw citations, nhưng quyết định style vẫn thuộc `StyleDetector`.

## 6. Module và file

### Module mới

```text
src/integrity_checker/extraction/grobid_adapter.py
```

API dự kiến:

```python
def grobid_to_references(output: GrobidOutput) -> list[Citation]: ...
def grobid_to_in_text_citations(output: GrobidOutput) -> list[Citation]: ...
def build_grobid_id_map(citations: list[Citation]) -> dict[str, Citation]: ...
def merge_extraction_results(grobid, regex, *, document_text="") -> MergeResult: ...
```

### File cần kiểm tra/chỉnh sửa

- `extraction/grobid_parser.py`
- `extraction/document_parser.py`
- `models/citation.py`, `models/validation.py`
- `linking/citation_linker.py`, `linking/statuses.py`
- `extraction/style_detector.py`
- `pipeline/integrity_pipeline.py`
- `models/api_schemas.py` nếu expose provenance

### Test dự kiến

- `tests/unit/test_grobid_adapter.py`
- `tests/unit/test_grobid_merge.py`
- `tests/unit/test_grobid_style_evidence.py`
- `tests/integration/test_grobid_adapter_integration.py`
- Mở rộng test DocumentParser, GROBID integration, linker, pipeline và CIS.

## 7. Kế hoạch theo giai đoạn

### Giai đoạn 0 — Baseline (01/10/2026)

Trước khi code:

- Chạy toàn bộ test hiện tại.
- Chạy evaluation trên dataset hiện có.
- Chọn PDF IEEE nhiều cột, APA, Vancouver/AMA, luận văn tiếng Việt, reference lỗi và case GROBID fallback.
- Lưu citation/reference precision-recall, linking accuracy, style accuracy, verdict count, API calls và fallback rate.

Deliverable: `reports/grobid_adapter_baseline_2026-10-01.*`.

### Giai đoạn 1 — Adapter bibliography

- Map `GrobidBibEntry` → `CitationType.REFERENCE_LIST`.
- Map authors, title, year, venue, DOI, pages, volume, issue.
- Normalize author/DOI và giữ `grobid_ref_id`.
- Xử lý field thiếu mà không crash.
- Viết fixture TEI và unit tests trước khi nối pipeline.

**Done khi:** mapping field cơ bản đạt ≥95%, malformed/empty entry an toàn.

### Giai đoạn 2 — In-text và TEI links

- Map `GrobidCitation` → `IN_TEXT` hoặc `NUMERIC`.
- Giữ raw text, page/section nếu có.
- Map trực tiếp `ref_id` trước fuzzy linker.
- Hỗ trợ single và multi-reference.
- Giữ mapping status/confidence cho UI.

**Done khi:** `[1]`, `[1,2]`, `(Smith, 2020)` và multi-ref pass fixture tests.

### Giai đoạn 3 — Merge với regex/PyMuPDF

- Identity reference: DOI → title/author/year → normalized raw text.
- Identity occurrence: page/offset nếu có + raw text + normalized position.
- GROBID ưu tiên khi cấu trúc đầy đủ.
- Union citation regex bị GROBID bỏ sót.
- Dedupe chắc chắn; conflict thì giữ diagnostics, không xóa mù quáng.
- Đánh dấu `source="merged"` cho dữ liệu hợp nhất.

### Giai đoạn 4 — Tích hợp pipeline

- Gọi adapter tại một điểm duy nhất trong `DocumentParser`.
- Downstream nhận unified citations/references.
- Chỉ reference entries đi qua retrieval/checker.
- In-text chỉ đi qua linking/style evidence.
- CIS giữ `verified_ratio` trên references và consistency trên linking result.

### Giai đoạn 5 — Style và compatibility

- Truyền GROBID evidence vào `StyleDetector`.
- So sánh với regex evidence; evidence thiếu phải cho `UNKNOWN`, mâu thuẫn có thể cho `MIXED`.
- Test toàn bộ pattern modules khi GROBID disabled.

### Giai đoạn 6 — Evaluation và rollout

- Chạy toàn bộ tests và before/after evaluation.
- Có thể chạy `grobid_shadow` trước khi đổi output chính.
- Chỉ bật `grobid_primary` sau acceptance criteria.

## 8. Fallback và lỗi

| Tình huống | Hành vi |
|---|---|
| Docker Desktop chưa chạy | status unavailable, fallback regex |
| Timeout/HTTP 4xx/5xx | log warning, retry giới hạn, fallback |
| Empty/malformed TEI | output unavailable, fallback, không leak system detail |
| Thiếu bibliography | regex/reference parser |
| Thiếu citation links | CitationLinker xử lý tiếp |
| GROBID/regex conflict | giữ diagnostics, không tự xóa |
| PDF scan | giữ behavior hiện tại, không mở rộng OCR |

Contract:

```text
available   → adapter + merge
partial     → merge partial + diagnostics
unavailable → PyMuPDF + regex fallback
```

## 9. Kiểm thử và lệnh xác minh

### Unit

- Bibliography field mapping, authors, DOI/year/pages.
- ID normalization, single/multi links.
- Empty/malformed TEI.
- Dedupe, conflict, provenance/confidence.

### Integration/regression

- PDF → PyMuPDF + GROBID → unified output.
- GROBID unavailable → regex fallback.
- Direct TEI mapping trước fuzzy mapping.
- In-text có `mapping_status` nhưng không có retrieval verdict.
- CIS và style không regression.

```bash
source .venv/bin/activate
python -m pytest tests/unit/test_grobid_adapter.py -v
python -m pytest tests/integration/test_grobid_adapter_integration.py -v -m integration
python -m pytest tests/ -v --tb=short
python -m ruff check src/ tests/
python -m compileall -q src
docker context show
curl -fsS http://localhost:8070/api/isalive
```

## 10. Acceptance criteria

- [ ] Adapter riêng, API và tests rõ ràng.
- [ ] GROBID bibliography chuyển đúng model nội bộ.
- [ ] TEI links được giữ, normalize và ưu tiên.
- [ ] Multi-reference không mất link.
- [ ] Regex fallback hoạt động khi GROBID unavailable.
- [ ] Empty/malformed TEI không crash.
- [ ] Không verify in-text thiếu metadata.
- [ ] Không có verdict unresolved giả cho in-text.
- [ ] StyleDetector giữ đúng `APA-like`/`IEEE-like`/`MIXED`/`UNKNOWN`.
- [ ] Test hiện tại pass hoặc regression được giải thích.
- [ ] Có baseline và before/after report.

Ngưỡng định lượng đề xuất:

- Citation/reference recall không giảm quá 1%.
- Linking accuracy ≥95% trên gold fixtures.
- Field mapping title/author/year/DOI ≥95%.
- Fallback success rate 100% trong test lỗi.
- Duplicate occurrence không tăng quá 1%.
- API calls cho in-text giảm ≥80% trên bài author-year/numeric.

## 11. Rủi ro và giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| GROBID parse sai PDF tiếng Việt | merge, regex fallback, evaluation riêng |
| GROBID bỏ sót citation | union với regex, dedupe |
| TEI ID không ổn định | normalize ID, fallback CitationLinker |
| Mất multi-ref | giữ `citation_links: list`, fixture bắt buộc |
| Quá tin GROBID | provenance, conflict diagnostics |
| Vỡ API schema | optional/backward-compatible fields |
| Runtime tăng | SHA256 cache, feature flag, đo latency |
| Startup chậm | health check, retry giới hạn, fallback |
| Regression CIS | snapshot metrics và dedicated tests |

## 12. Feature flags và rollout

```text
legacy_regex  = chỉ regex hiện tại
grobid_shadow = chạy adapter để đo, chưa đổi output
grobid_merge  = GROBID + regex merge
grobid_primary= GROBID ưu tiên, regex validation/fallback
```

Thứ tự: `legacy_regex` → `grobid_shadow` → `grobid_merge` → `grobid_primary`. Không bật primary ngay commit đầu tiên.

## 13. Deliverables

1. `PLAN_GROBID_ADAPTER.md`.
2. `grobid_adapter.py` và merge/provenance model.
3. Tích hợp DocumentParser/pipeline.
4. Unit, integration, regression tests.
5. Baseline và before/after evaluation reports.
6. README/quickstart/changelog cập nhật nếu command hoặc mode thay đổi.

## 14. Checklist bắt đầu ngày 01/10/2026

- [ ] Branch sạch và commit kế hoạch.
- [ ] `docker context show` trả `desktop-linux`.
- [ ] `curl http://localhost:8070/api/isalive` trả `true`.
- [ ] Chạy baseline tests/evaluation.
- [ ] Đọc model `Citation`, `CitationLink`, `LinkingResult`, `StyleFeatures`.
- [ ] Chốt provenance fields tối thiểu.
- [ ] Viết fixture TEI nhỏ.
- [ ] Viết test adapter trước implementation lớn.
- [ ] Chỉ nối DocumentParser sau khi adapter unit tests pass.
- [ ] Không xóa regex patterns.
- [ ] Commit theo từng giai đoạn nhỏ để rollback dễ.

## 15. Kết luận

**Triển khai adapter GROBID; không loại bỏ regex.** Bắt đầu ngày 01/10/2026 bằng baseline và adapter bibliography, sau đó mới tích hợp citation links, merge, pipeline và evaluation. Mục tiêu là GROBID trở thành structured extractor chính nhưng hệ thống vẫn có regex validation/fallback, provenance rõ ràng và khả năng hoạt động ổn định khi GROBID không sẵn sàng.
