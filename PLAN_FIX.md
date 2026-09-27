# Fix: Citation context + URL RESOURCE classification

## Context

Hai bug user report:

1. **Hard-coded context** trong DocumentInspectorPage.tsx — mọi citation đều hiển thị cùng câu "Recent studies in machine learning have explored various approaches to natural language processing... demonstrating significant improvements in performance benchmarks." Đây là text giả, không phải context thật của citation. Cần lấy sentence/paragraph thật xung quanh citation từ PDF.

2. **URL không được classify là RESOURCE** — User thấy các URL như `https://github.com/iann...` vẫn bị mark là `unresolved` (3 cái). Theo design, URL phải được auto-mark là RESOURCE (không tính vào verification). Bug ở regex quá strict — không match URL có trailing punctuation (e.g. URL ở cuối câu có dấu `.`).

Mục tiêu: hiển thị context thật cho từng citation, và URL luôn được RESOURCE (đúng nghĩa "URL/Reference link không phải academic citation").

## Changes

### Backend

#### 1. Populate `citation.context` trong pipeline
**File:** `src/integrity_checker/pipeline/integrity_pipeline.py` (line ~624-660)

Đã có sẵn function `_extract_citation_context()` (line 748-783) và đã được gọi để lấy `citation_context` local. Chỉ thiếu 1 dòng assign vào `citation.context`:

```python
# Line 624-634 hiện tại: compute citation_context (local variable)
citation_context = None
for page in document_pages:
    if citation.raw_text.lower() in page.text.lower():
        citation_context = IntegrityPipeline._extract_citation_context(
            citation.raw_text, page.text, window_chars=200,
        )
        break

# THÊM: Persist onto Citation object for serialization
citation.context = citation_context

# ... sau đó mới pass citation_context vào checker.check()
verdict = self.checker.check(citation, source, **check_kwargs)
```

`_serialize_citation` (line 1022-1048) đã include `"context": citation.context` — không cần thay đổi JSON schema. Cached reports cũ sẽ có `context = None` (handled bởi default).

#### 2. Robust URL detection + debug log
**File:** `src/integrity_checker/logic/neuro_symbolic_checker.py` (line 92-107)

**Vấn đề:** Regex `^(https?://|www\.)[^\s]+$` không match khi raw_text có trailing punctuation. E.g. raw_text = `"https://github.com/iann..."` (với dấu `...` ellipsis) fail vì `.` match `[^\s]+` rồi đến `$` thấy vẫn còn chars.

**Fix:**

```python
# Thêm import ở đầu file
from integrity_checker.logging import get_logger
logger = get_logger(__name__)

# Sửa logic check (line 92-107)
raw_text = citation.raw_text or ""
stripped_text = raw_text.strip()

# Strip trailing punctuation that commonly follows URLs in sentence context
url_candidate = stripped_text.rstrip(".,;:)\"'")

# Match if the candidate starts with URL scheme (not just full-string match)
url_pattern = re.compile(r'^(https?://|www\.)[^\s]+', re.IGNORECASE)
if url_pattern.match(url_candidate) and len(url_candidate) > len(url_candidate.split()[0]) >= 10:
    logger.debug(f"URL/RESOURCE detected: {raw_text[:80]}")
    return CitationVerdict(
        citation=citation,
        label=ValidationLabel.RESOURCE,
        confidence=0.95,
        matched_source=source,
        features=None,
        reasoning=f"URL/Reference link detected: {raw_text[:60]}... (not an academic citation)",
        triggered_rules=["R-URL-RESOURCE"],
        mismatched_fields=[],
    )

# Optional: log when raw_text looks URL-ish but didn't match (helps debug)
if re.match(r'^(https?://|www\.)', stripped_text) and not url_pattern.match(url_candidate):
    logger.debug(f"URL-like raw_text but no RESOURCE match: {raw_text[:80]}")
```

Lưu ý: Đổi từ `match()` anchor `^...$` sang match `^...` (chỉ check prefix) + verify độ dài URL đủ dài (≥10 chars để tránh false positive). Giữ logic strict nhưng robust hơn với punctuation.

### Frontend

#### 3. Add `context` field to Verdict interface
**File:** `web/src/api/client.ts` (line 90-110)

```typescript
export interface Verdict {
  citation_id: string;
  citation_raw: string;
  // NEW: surrounding sentence/paragraph context (v1.5)
  context?: string;
  // ... existing fields
}
```

Lý do: optional vì cached reports cũ có thể không có field này.

#### 4. Render real context trong DocumentInspectorPage
**File:** `web/src/pages/DocumentInspectorPage.tsx`

- **Line 33-40** (`InlineCitation` interface): thêm `context?: string`
- **Line 43-52** (`buildInlineCitations`): thêm `context: v.context` vào mapping
- **Line 480-498** (citation document view): thay hard-coded text bằng context thật:

```tsx
{filteredCitations.map((citation, index) => (
  <div key={citation.id} className="relative">
    <span className="absolute -left-8 text-xs ...">p{citation.page}</span>
    <p className="pl-6">
      {citation.context ? (
        // Highlight citation within actual context (best-effort split)
        <ContextWithHighlight context={citation.context} marker={citation.raw} />
      ) : (
        <>No surrounding text extracted for this citation.</>
      )}
    </p>
  </div>
))}
```

Helper function `ContextWithHighlight` nhận context string, tìm citation marker bằng case-insensitive substring, render `<mark>` quanh nó. Optional enhancement: nếu user muốn tối giản, fallback dùng raw text nguyên cùng marker chip hiện tại.

- **Line 165-168** (Citation Detail modal): thêm section hiển thị context nếu có (optional polish)

## Verification

```bash
# Backend unit tests (URL regex change might affect existing tests)
cd /Users/iannwendy/Desktop/DATN/essay-integrity-checker
source .venv/bin/activate
python -m pytest tests/unit/test_bug_fixes.py -v
python -m pytest tests/unit/test_rules_fake_url.py -v
python -m pytest tests/unit/test_crossref_disabled.py -v

# Full test suite
python -m pytest tests/ -v

# Manual test on a real PDF
python -m integrity_checker.pipeline.integrity_pipeline TranThanhPhuoc_523H0002_523H0054.pdf --output /tmp/test_report.json
python -c "import json; d=json.load(open('/tmp/test_report.json')); [print(v['citation']['raw_text'][:50], '|', (v['citation'].get('context') or 'NO_CONTEXT')[:80]) for v in d['verdicts'] if 'github.com' in v['citation']['raw_text'].lower() or v['label'] == 'resource']"

# Frontend type check + tests
cd web
npm run build
npm run test:e2e -- --grep "Document Inspector"
```

### Acceptance criteria

- [ ] Mỗi citation trong Document View hiển thị câu/đoạn văn THẬT xung quanh nó (không phải hard-coded)
- [ ] URL citations (`https://...`, `www....`) đều được label = `resource` (không còn unresolved cho URLs)
- [ ] Log có dòng `URL/RESOURCE detected: ...` khi chạy pipeline với log level = DEBUG
- [ ] Existing tests pass (619 passed, 4 skipped)
- [ ] Cached reports cũ vẫn load được (context = null/undefined → fallback gracefully)

### Risks / Edge cases

- **Cached reports**: Reports đã cache trong `data/cache/reports/` không có field `context`. Cần invalidate cache hoặc handle `context = undefined` gracefully (frontend fallback "No surrounding text extracted").
- **Regex false positives**: Text bắt đầu bằng `www.` không phải URL hiếm gặp nhưng có thể — đã mitigate bằng check `len ≥ 10`.
- **Sentence splitting**: Trong context string, citation marker có thể xuất hiện nhiều lần (PDF lặp). Best-effort highlight lần xuất hiện đầu tiên.
- **HTML escape**: Khi render context, phải escape HTML để tránh XSS (React tự escape nếu dùng `{text}`).

## Files to modify

| File | Lines | Change |
|------|-------|--------|
| `src/integrity_checker/pipeline/integrity_pipeline.py` | 624-660 | Add `citation.context = citation_context` |
| `src/integrity_checker/logic/neuro_symbolic_checker.py` | 1-25, 92-107 | Add logger import + robust URL regex |
| `web/src/api/client.ts` | 90-110 | Add `context?: string` to Verdict |
| `web/src/pages/DocumentInspectorPage.tsx` | 33-52, 480-498 | Use real context from verdict |

## Estimated effort

~30 minutes implementation + 15 minutes testing.
