# Plan: Sửa UI Citations/References — dedupe, link display, status, cited-in-text

## Context

User báo lỗi UI trên `TranThanhPhuoc_523H0002_523H0054.pdf` (essay 43 — vừa chạy sau v1.7):

1. **Citations tab lặp cite**: `(WHO, 2023)` xuất hiện 2 lần, `[1]` xuất hiện 4 lần, `[24]` xuất hiện 4 lần, ... (33 unique in-text nhưng hiển thị 66 rows).
2. **Linked Reference cột trống**: tất cả rows hiển thị `—` (em-dash).
3. **Status cột toàn "Linked"** (xanh ✓) — không phân biệt được linked/missing/unresolved.
4. **References tab không có cột "cited in text"** — không biết ref nào được cite, ref nào không.

## Root cause

### Vấn đề #1 (lặp cite)

- Backend lưu **MỌI occurrence** vào `extracted_citations[]` (66 rows cho 33 unique in-text — đúng, đếm cả lặp).
- Frontend render nguyên si `extractedInText.map(...)` → 66 rows.
- **Fix cần**: dedupe theo `raw_text` + accumulate `occurrences: N` count. Vẫn giữ raw đầy đủ để hiển thị.

### Vấn đề #2 & #3 (Linked Reference trống + Status toàn Linked)

- `CitationRecord` (DB model) **không có** columns `mapping_status`, `mapping_confidence`, `citation_link`.
- `add_citations()` lúc lưu DB **BỎ QUA** 3 fields này.
- Lúc đọc lại từ DB, các fields này là `None` → API trả `null`.
- Frontend `mapping_status ?? 'matched'` → luôn `matched` → label = `'verified'` → "Linked" cho tất cả.
- Tương tự `citation_link?.reference_id` → null → Linked Reference trống.
- Đây là **regression từ v1.7**: đã thêm logic gắn `mapping_status` cho in-text trong pipeline (line 786-792 `integrity_pipeline.py`), nhưng khi persist xuống DB thì mất.

### Vấn đề #4 (References thiếu "cited in text")

- Frontend `references.map(...)` không có field `cited_in_text_count`.
- Cần compute ở backend: đếm số in-text có `citation_link.reference_id` match với ref id.

## Fix strategy

### Backend (3 files)

#### 1. `src/integrity_checker/db/models.py`

Thêm 3 columns vào `CitationRecord`:

```python
class CitationRecord(Base):
    # ... existing fields ...
    # NEW v1.8 — linking layer persisted for in-text citations (UI Citations tab)
    mapping_status: Mapped[str | None] = mapped_column(String, nullable=True)
    mapping_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    citation_link_json: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Lưu ý: `citation_link` là object phức tạp → serialize thành JSON string trong `citation_link_json`. Thêm helper `_serialize_citation_link_dict()` để trả về dict-friendly form (method enum, status enum cần convert sang string).

#### 2. `src/integrity_checker/db/session.py` — migration helper

Trước `Base.metadata.create_all`, thêm bước ALTER TABLE để add columns nếu chưa có (SQLite không có IF NOT EXISTS cho ADD COLUMN — check `pragma table_info`):

```python
def init_db() -> None:
    engine = get_engine()
    # ALTER TABLE cho SQLite (idempotent — bỏ qua nếu column đã có)
    with engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(citations)").fetchall()}
        if "mapping_status" not in cols:
            conn.exec_driver_sql("ALTER TABLE citations ADD COLUMN mapping_status VARCHAR")
        if "mapping_confidence" not in cols:
            conn.exec_driver_sql("ALTER TABLE citations ADD COLUMN mapping_confidence FLOAT DEFAULT 0")
        if "citation_link_json" not in cols:
            conn.exec_driver_sql("ALTER TABLE citations ADD COLUMN citation_link_json TEXT")
    Base.metadata.create_all(bind=engine)
```

#### 3. `src/integrity_checker/db/repository.py` — `add_citations()`

Persist linking fields:

```python
def add_citations(self, essay_id: int, citations: list[Citation]) -> list[CitationRecord]:
    # ...
    records = [
        CitationRecord(
            # ... existing fields ...
            mapping_status=getattr(c, "mapping_status", None),
            mapping_confidence=getattr(c, "mapping_confidence", 0.0),
            citation_link_json=(
                json.dumps(_link_to_dict(getattr(c, "citation_link", None)), ensure_ascii=False)
                if getattr(c, "citation_link", None) is not None else None
            ),
        )
        for c in citations
    ]
```

#### 4. `src/integrity_checker/api/routes/report.py` — `_json_response()`

**Update `extracted_citations` serialization** (line 213-230): đọc trực tiếp từ `c.mapping_status`, `c.mapping_confidence`, deserialize `c.citation_link_json` thành dict.

**Add `cited_in_text_count` + `cited_on_pages` cho mỗi ref** trong `references[]`:

```python
# Build map: ref-NNNN → {count, pages}
in_text_by_link_ref = {}  # reference_id → {"count": N, "pages": [...]}
for c in citations:
    if c.citation_type in {"in_text", "numeric"} and getattr(c, "citation_link_json", None):
        link_dict = json.loads(c.citation_link_json)
        ref_link = link_dict.get("reference_id")
        if ref_link:
            entry = in_text_by_link_ref.setdefault(ref_link, {"count": 0, "pages": []})
            entry["count"] += 1
            if c.page_num:
                entry["pages"].append(c.page_num)

# Map refs by insertion order → ref-NNNN
ref_records_sorted = sorted(
    [c for c in citations if c.citation_type == "reference_list"],
    key=lambda c: c.id
)
ref_link_id_by_record_id = {r.id: f"ref-{i:04d}" for i, r in enumerate(ref_records_sorted)}

"references": [
    {
        # ... existing fields ...
        cited_in_text_count=in_text_by_link_ref.get(
            ref_link_id_by_record_id.get(c.id, ""), {"count": 0, "pages": []}
        )["count"],
        cited_on_pages=sorted(set(
            in_text_by_link_ref.get(
                ref_link_id_by_record_id.get(c.id, ""), {"count": 0, "pages": []}
            )["pages"]
        )),
    }
    for c in ref_records_sorted
],
```

**Đếm `unique_in_text_count` cho tab Citations** — trả `extracted_citations_unique: N` cho frontend dùng làm counter (frontend dedupe ở client).

### Frontend (3 files)

#### 5. `web/src/pages/EssayPage.tsx`

**Dedupe in-text citations theo `raw_text`** — giữ row đầu tiên, accumulate `occurrences`:

```typescript
// Compute deduped in-text citation groups
const inTextGroups = new Map<string, { 
  citation: Citation; 
  occurrences: number;
  refIds: Set<string>;  // distinct references cited by this group
}>();
for (const citation of extractedInText) {
  const key = citation.raw_text;
  if (!inTextGroups.has(key)) {
    inTextGroups.set(key, { citation, occurrences: 0, refIds: new Set() });
  }
  const group = inTextGroups.get(key)!;
  group.occurrences += 1;
  const refId = citation.citation_link?.reference_id;
  if (refId) group.refIds.add(refId);
}
const dedupedInText = Array.from(inTextGroups.values());
```

**Build `refId → Reference` map** (từ `report.references[]` theo order):

```typescript
// Map "ref-NNNN" → reference (by insertion order)
const refByLinkId = new Map<string, Citation>();
report.references?.forEach((ref, idx) => {
  refByLinkId.set(`ref-${String(idx).padStart(4, '0')}`, ref);
});
```

**Render Citations tab** — dùng `dedupedInText` thay cho `inTextVerdicts`. Mỗi row:
- Citation text + badge **`× N`** (theo user chọn) nếu occurrences > 1
- Linked Reference: hiển thị **`Ref #N — Author (Year)`** (theo user chọn). Resolve `ref-NNNN` → ref `order_index+1` → lấy ref từ `report.references[]` → render "Ref #1 — American Psychiatric Association (2022)"
- Status: dựa trên `mapping_status` thật
  - `matched` → "Linked" (xanh ✓)
  - `missing_reference` → "No Reference" (cam ⚠)
  - `unresolved` / khác → "Unverifiable" (xám)

**Render References tab** — thêm cột "Cited in Text":
- Theo user chọn: **Icon + tooltip** — icon ✓ xanh + tooltip "Cited 3 times on pages 1, 5, 12" khi count > 0, icon xám + "Not cited in text" khi count = 0
- Hover vào icon hiển thị pages list (từ `cited_on_pages` field trả về từ API)

#### 6. `web/src/api/client.ts` — Type updates

```typescript
export interface Citation {
  // ... existing fields ...
  mapping_status?: CitationMappingStatus;
  mapping_confidence?: number;
  citation_link?: CitationLink;
  cited_in_text_count?: number;  // NEW — chỉ cho refs (số lần được cite in-text)
  cited_on_pages?: number[];     // NEW — chỉ cho refs (page numbers where cited)
}
```

## Verification plan

1. **Migration** chạy clean: restart backend → init_db thêm columns OK (idempotent ALTER TABLE). **Note**: essays chạy TRƯỚC fix này sẽ có `mapping_status`/`citation_link_json` = NULL trong DB → frontend sẽ fallback hiển thị như cũ. Cần re-run pipeline trên `TranThanhPhuoc_523H0002_523H0054.pdf` để test.

2. **API test** (`curl /api/essays/43/report`):
   - `extracted_citations[i].mapping_status` reflect đúng (30 matched, 36 missing_reference).
   - `extracted_citations[i].citation_link.reference_id` có giá trị `ref-NNNN` cho matched.
   - `references[i].cited_in_text_count` đúng.

3. **Frontend (Playwright)** — bật playwright, navigate `localhost:5173/verification/report/43`:
   - Tab Citations: count unique rows = 33 (không phải 66), mỗi row có count.
   - Tab Citations: Linked Reference column hiển thị ref number + title.
   - Tab Citations: Status khác nhau cho matched vs missing_reference.
   - Tab References: cột "Cited in Text" hiển thị số lần.

4. **Run tests**:
   ```bash
   source .venv/bin/activate && python -m pytest tests/ -v
   ```
   Expect: 619+ tests pass (existing). Có thể 1-2 tests fail do schema change → fix.

5. **Regression** — chạy với `Attention.pdf`, `BERT.pdf`, `VietDepression.pdf` để đảm bảo không vỡ logic cũ.

## Files to modify

| File | Change |
|------|--------|
| `src/integrity_checker/db/models.py` | Add 3 columns to CitationRecord |
| `src/integrity_checker/db/session.py` | ALTER TABLE migration helper in init_db |
| `src/integrity_checker/db/repository.py` | Persist mapping_status/confidence/citation_link in add_citations |
| `src/integrity_checker/api/routes/report.py` | Read back linking data + compute cited_in_text_count |
| `web/src/api/client.ts` | Update Citation interface (add cited_in_text_count) |
| `web/src/pages/EssayPage.tsx` | Dedupe in-text, fix Linked Reference, fix Status, add cited column |

## Reference functions / patterns

- **CitationLinker.link()** (`src/integrity_checker/linking/citation_linker.py:79-152`) — giữ nguyên, đã tạo CitationLink với reference_id đúng.
- **Citation mapping_status attach** (`src/integrity_checker/pipeline/integrity_pipeline.py:771-792`) — đã đúng, chỉ cần persist xuống DB.
- **_serialize_citation_link()** (`src/integrity_checker/pipeline/integrity_pipeline.py:1346`) — pattern cho serialize CitationLink → dict.
- **ALTER TABLE migration** — pattern idempotent check `PRAGMA table_info`.
