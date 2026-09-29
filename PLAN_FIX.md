# Plan: Sửa bug — chỉ reference list mới verify qua API, in-text chỉ cần linking

## Context

User báo cáo trên UI (essay 39, file `TranThanhPhuoc_523H0002_523H0054.pdf`) hiển thị:

- **Bảng "Citation Reference Linking"** (ảnh 2): tất cả in-text citations đều **Linked** (màu xanh ✓) → linking hoạt động đúng.
- **Bảng "Reference Verification"** (ảnh 1): hầu hết các dòng cùng raw_text ở trên lại hiển thị **Unresolved** với lý do "No matching publication found" / "Found a matching publication in Crossref" / "Found matching publications in the known-papers library".

User chỉ ra đây là logic sai:

> "nó là cite, chỉ kiểm tra nó có link tới ref hay không thôi. tại sao lại đi xác minh nó bằng cách gọi api?"

## Root cause

Pipeline hiện tại ở `src/integrity_checker/pipeline/integrity_pipeline.py`:

- **Line 536-538**: `_merge_citations(in_text, ref, [])` gộp **CẢ body citations (in-text) + reference list citations** thành 1 danh sách duy nhất.
- **Line 581-584**: `orchestrator.retrieve()` được gọi cho **MỌI unique citation** trong danh sách — bao gồm cả in-text như `(WHO, 2023)`, `[1]`, `(Sennrich et al., 2016)`, …
- **Line 623-734**: `checker.check()` được gọi cho cùng danh sách — gán `label` cho từng cái.

**Output thật của `TranThanhPhuoc_523H0002_523H0054.pdf`** (đã chạy & đọc log):

```
[ 1] type=reference_list     raw=[1] American Psychiatric…  label=verified     mapping=matched
[27] type=reference_list     raw=[27] Settles, B., & Craven… label=verified     mapping=matched
[28] type=in_text            raw=(WHO, 2023)                label=unresolved   mapping=missing_reference  ← LỖI
[31] type=in_text            raw=Sennrich et al. (2016)     label=verified     mapping=missing_reference  ← LỖI
[33] type=in_text            raw=Zou (2019)                 label=unresolved   mapping=missing_reference  ← LỖI
[56] type=in_text            raw=[2]                        label=unresolved   mapping=missing_reference  ← LỖI
```

Từ log retrieval ta thấy TẤT CẢ in-text citations `[1]`, `[4]`, `[17]`, `[24]` … đều đã được linker map sang reference tương ứng (xem bảng Linked Reference). Nhưng vì pipeline gộp cả in-text vào danh sách retrieve, nó gọi API cho `(WHO, 2023)` (1 in-text không có title) → API/local DB MISS → checker trả UNRESOLVED.

Vậy nên verdicts của in-text citations **không nên tồn tại**. Chúng đang được sinh ra vì pipeline gộp và verify nhầm.

## Mục tiêu fix (user confirmed)

1. **`verdicts[]` chỉ chứa CitationVerdict cho references.** In-text bỏ hẳn khỏi verdicts[].
2. **In-text citations vẫn xuất hiện trong `extracted_citations[]`** cho UI Citations tab.
3. **`mapping_status` cho mỗi in-text citation** được thêm vào `extracted_citations[]` (lấy từ linker) → Citations tab hiển thị đúng trạng thái Linked/Missing Reference.
4. **API shape JSON giữ nguyên** (chỉ thêm field `mapping_status` vào Citation trong extracted_citations[]).
5. **CIS tính đúng** — `verified_ratio` chỉ tính trên references, `in_text_bib_consistency` tính trên `LinkingResult.links`.
6. **Tests pass** — cập nhật tests bị ảnh hưởng.

## Approach

### Backend changes

#### 1. `src/integrity_checker/pipeline/integrity_pipeline.py`

**Thêm helper filter (private method):**

```python
@staticmethod
def _is_verifiable(citation: Citation) -> bool:
    """Citation này cần source verification (retrieve + checker)?

    Chỉ reference list entries (và DOI/URL inline có metadata đầy đủ) mới
    cần verify qua API/local DB. In-text citations chỉ cần linking —
    mapping_status từ CitationLinker là đủ.
    """
    if citation.citation_type == CitationType.REFERENCE_LIST:
        return True
    if citation.citation_type in {CitationType.DOI, CitationType.URL}:
        # Bare DOI/URL inline có title thì vẫn verify được
        return bool(citation.title or citation.doi or citation.url)
    return False
```

**Sửa `run_async()`:**

- **Line 561-573** (`unique_citations`): giữ nguyên — vẫn dedupe từ tất cả (in-text + ref).
- **Line 573** (`unique_list`): filter chỉ những citation verifiable (references).

```python
# Before:
unique_list = list(unique_citations.values())

# After:
unique_list = [c for c in unique_citations.values() if IntegrityPipeline._is_verifiable(c)]
```

- **Line 581-586**: retrieval chỉ chạy trên `unique_list` (đã filter) — không gọi API cho in-text.
- **Line 623-734**: verdict loop chỉ iterate qua `unique_list` — không có verdict cho in-text.
- **Line 771** (`num_citations`): `len(unique_list)` — chỉ đếm references (đúng nguyện vọng của user "chỉ cần check link tới ref").

**Thêm: gắn `mapping_status` cho in-text citations trước khi build `extracted_citations`.**

Trong verdict loop hiện tại (line 623-734), ta đã có `mapping_status` cho từng citation đã iterate. Sau fix, ta KHÔNG iterate qua in-text → ta cần 1 pass riêng để gắn `mapping_status` cho in-text.

**Approach:** Trước khi build `AnalysisReport`, ta attach `mapping_status` cho in-text citations:

```python
# Sau verdict loop, trước AnalysisReport build
in_text_by_raw = {c.raw_text: c for c in in_text_citations}
for link in linking_result.links:
    if link.status and link.occurrence_id:
        # lookup in_text citation by occurrence_id
        for cit in in_text_citations:
            if cit.reference_id == link.occurrence_id:
                cit.mapping_status = link.status  # new field on Citation
                cit.mapping_confidence = link.confidence
                cit.citation_link = link
                break
```

**Cần thêm field `mapping_status`, `mapping_confidence`, `citation_link` vào `Citation` dataclass** (line 53-107 trong `src/integrity_checker/models/citation.py`).

#### 2. `src/integrity_checker/models/citation.py`

**Thêm fields (backward compat):**

```python
# NEW v1.7 — linking layer attached to Citation (for in-text display in UI)
mapping_status: Optional[str] = None  # CitationMappingStatus.value
mapping_confidence: float = 0.0
citation_link: Optional[object] = None  # CitationLink
```

Cập nhật `_serialize_citation()` (line 1095-1121 trong pipeline) và `from_raw()` (line 137-159) để bao gồm các field mới.

#### 3. `src/integrity_checker/pipeline/integrity_pipeline.py` — `_serialize_citation()` (line 1095-1121)

```python
def _serialize_citation(citation: Citation) -> dict[str, Any]:
    return {
        ...existing fields...
        "mapping_status": getattr(citation, "mapping_status", None),
        "mapping_confidence": getattr(citation, "mapping_confidence", 0.0),
        "citation_link": _serialize_citation_link(getattr(citation, "citation_link", None)),
    }
```

#### 4. `src/integrity_checker/api/routes/report.py`

**Line 213-224** (`extracted_citations` serialization): thêm `mapping_status`, `mapping_confidence`, `citation_link` vào dict.

```python
"extracted_citations": [
    {
        "id": c.id,
        "raw_text": c.raw_text,
        "citation_type": c.citation_type,
        "style": c.style,
        "page_num": c.page_num,
        "confidence": c.confidence,
        # NEW v1.7 — linking layer cho UI Citations tab
        "mapping_status": getattr(c, "mapping_status", None),
        "mapping_confidence": getattr(c, "mapping_confidence", 0.0),
        "citation_link": getattr(c, "citation_link", None),
    }
    for c in citations
    if c.citation_type in {"in_text", "numeric"}
],
```

**Line 118-132** (`linking_summary`): KHÔNG cần đổi. Sau fix:
- Verdicts chỉ có references → `linking_summary` count chính xác cho references.
- In-text mapping status sẽ được hiển thị qua Citations tab (mỗi dòng có `mapping_status` riêng).

**Line 186-202** (`cis_dict` fallback): KHÔNG cần đổi. Sau fix, `academic_verdicts` chỉ có references → `verified_ratio` chính xác hơn.

### Frontend changes

#### 5. `web/src/api/client.ts`

**Line 187-200** (`Citation` interface):

```typescript
export interface Citation {
  id?: number;
  raw_text: string;
  citation_type: CitationType;
  style: string;
  authors: string[];
  year?: string | null;
  title?: string | null;
  venue?: string | null;
  doi?: string | null;
  url?: string | null;
  page_num: number;
  confidence: number;
  // NEW v1.7 — linking layer
  mapping_status?: CitationMappingStatus;
  mapping_confidence?: number;
  citation_link?: CitationLink;
}
```

#### 6. `web/src/pages/EssayPage.tsx` — Citations tab (line 139-162)

**Before** (hardcode mapping_status='matched', label='verified'):

```typescript
const inTextVerdicts = extractedInText.map((citation) => ({
  citation_id: `v${citation.id ?? citation.raw_text}`,
  ...
  mapping_status: 'matched' as const,
  label: 'verified' as const,
  ...
}));
```

**After** (đọc mapping_status thật từ citation):

```typescript
const inTextVerdicts = extractedInText.map((citation) => {
  const mappingStatus = citation.mapping_status ?? 'matched';
  const mappingConfidence = citation.mapping_confidence ?? 0;
  return {
    citation_id: `c${citation.id ?? citation.raw_text}`,
    citation_raw: citation.raw_text,
    citation_type: citation.citation_type,
    mapping_status: mappingStatus,
    mapping_confidence: mappingConfidence,
    citation_link: citation.citation_link,
    // In-text không có source verification → label = VERIFIED (pass linking)
    // nếu mapping matched, ngược lại UNRESOLVED.
    label: mappingStatus === 'matched' ? 'verified' : 'unresolved',
    confidence: mappingConfidence,
    reasoning: '',
    triggered_rules: [],
    mismatched_fields: [],
    matched_sources: [],
    is_overridden: false,
  };
});
```

### Tests

#### 7. `tests/unit/test_pipeline_document_parser.py`

Test `test_pipeline_uses_document_parser_when_enabled` (line 96-167) expect `len(report.verdicts) == 1` với 1 body citation IN_TEXT. Sau fix:
- Nếu body citation là IN_TEXT, không có verdict → `len(report.verdicts) == 0`.
- Hoặc sửa test data để body citation có `citation_type=REFERENCE_LIST` và `title="..."` (mock API).

Cập nhật expectation tương ứng.

#### 8. `tests/unit/test_cis.py`

Thêm test:
- `test_verified_ratio_excludes_in_text` — gọi `CISCalculator.compute()` với verdicts chỉ chứa references, verify `verified_ratio` đúng.
- `test_in_text_bib_consistency_uses_linking_result` — verify rằng consistency vẫn tính đúng khi verdicts chỉ có references nhưng có LinkingResult.

#### 9. `tests/integration/test_pipeline_endtoend.py`

Verify end-to-end: PDF → AnalysisReport với:
- `verdicts[]` chỉ có references.
- `extracted_citations[]` có cả in-text và references.
- `extracted_citations[i].mapping_status` cho in-text citations.

## Reference functions / patterns to reuse

- **`IntegrityPipeline._merge_citations`** (line 858-884) — giữ nguyên. Ta dùng nó để compute `citation_keys` cho `unique_citations`, sau đó filter `unique_list` theo `_is_verifiable`.

- **`CitationLinker.link()`** (`src/integrity_checker/linking/citation_linker.py:79-152`) — đã chạy đúng, tạo `CitationLink` cho mỗi in-text occurrence. Ta tái sử dụng `linking_result.links` để attach `mapping_status` cho in-text citations.

- **`CISCalculator.compute()`** (`src/integrity_checker/logic/cis.py:71-119`) — KHÔNG cần đổi. Đã ưu tiên `linking_result.links` cho `in_text_bib_consistency`.

- **`NeuroSymbolicChecker.check()`** (`src/integrity_checker/logic/neuro_symbolic_checker.py:72-248`) — KHÔNG cần đổi.

- **`repository.add_verdicts()`** (`src/integrity_checker/db/repository.py:88`) — KHÔNG cần đổi. Chỉ persist `report.verdicts` (sau fix chỉ có references).

- **`repository.add_citations()`** (`src/integrity_checker/db/repository.py:44`) — KHÔNG cần đổi. Persist tất cả `report.extracted_citations` (gồm in-text + references).

## Files to modify (summary)

| File | Change |
|------|--------|
| `src/integrity_checker/models/citation.py` | Add `mapping_status`, `mapping_confidence`, `citation_link` fields |
| `src/integrity_checker/pipeline/integrity_pipeline.py` | Add `_is_verifiable()`, filter `unique_list`, attach mapping to in-text, update `_serialize_citation()` |
| `src/integrity_checker/api/routes/report.py` | Add `mapping_status` to extracted_citations serialization |
| `web/src/api/client.ts` | Add `mapping_status` to `Citation` interface |
| `web/src/pages/EssayPage.tsx` | Read `mapping_status` from `citation` instead of hardcoding |
| `tests/unit/test_pipeline_document_parser.py` | Update expectations |
| `tests/unit/test_cis.py` | Add tests for new behavior |

## Verification plan

1. **Run pipeline trên `TranThanhPhuoc_523H0002_523H0054.pdf`** — confirm:
   - `verdicts[]` chỉ chứa 27 reference entries (không phải 56).
   - Tất cả verdicts đều `verified` (vì local DB có hết).
   - `extracted_citations[]` vẫn chứa 66 in-text + 27 ref.
   - `extracted_citations[i].mapping_status` cho in-text citations (Linked/Missing Reference).
   - `linking_summary` cho references đúng.
   - CIS score vẫn cao (≥90).

2. **Run tests**:
   ```bash
   source .venv/bin/activate && python -m pytest tests/ -v
   ```
   - Fix broken tests từ expectation mới.
   - Đảm bảo 619+ tests pass.

3. **Manual UI check** — upload file qua web UI:
   - Tab "Overview" → Reference Verification chỉ hiển thị 27 references (đã verified).
   - Tab "Citations" → hiển thị tất cả 66 in-text với mapping_status đúng (Linked = ✓ xanh).
   - Tab "References" → hiển thị 27 bibliography entries.

4. **Regression check** — chạy pipeline với file test khác (ví dụ `Attention.pdf`, `BERT.pdf`) để đảm bảo không vỡ logic cũ.

5. **Edge cases**:
   - PDF không có reference list → 0 verdicts, chỉ có in-text extracted_citations.
   - PDF chỉ có DOI inline → DOI có title → verify, không có title → không verify.
   - PDF có URL inline (RESOURCE) → classification ngắn mạch trước, không qua API.
