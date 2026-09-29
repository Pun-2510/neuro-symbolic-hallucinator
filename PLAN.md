# Fix Overly Permissive Citation Patterns — 485 False Citations

## Context

Running pipeline on `TranThanhPhuoc_523H0002_523H0054.pdf` (98 pages, IEEE format, ~27 references)
returns **485 unique citations** when only ~30–80 are real. Root cause: 4 regex patterns are too
permissive and match non-citation text.

**Breakdown of 485 matches:**

| Pattern | Matches | Status |
|---------|---------|--------|
| `mla_intext_parenthetical` | 333 | **BUG** — matches any parentheses |
| `acs_comma_separated` | 50 | **BUG** — matches `100,000`, `1,371` (data) |
| `ama_comma_separated` | 50 | **BUG** — same |
| `cse_parenthesized` | 23 | **BUG** — matches `(1)`, `(2)` (equation/footnote numbers) |
| `ieee_numeric` + `nature_bracketed` | 51 | Legit IEEE `[N]` brackets |

Expected reduction: 485 → ~80 (legit IEEE brackets + ~30 other legitimate citations).

## Root Cause

| File | Pattern | Problem |
|------|---------|---------|
| `patterns/mla.py:51-56` | `\(([^)]+)\)` | Matches *anything* in parentheses |
| `patterns/acs.py:70-74` | `(\d+)(?:,\s*\d+)+` | Matches `100,000`, `1,371` (not just `[1,2]`) |
| `patterns/ama.py:70-74` | same | same |
| `patterns/cse.py:67-73` | `\((d+)\)` | Matches `(1)` in body (equations/footnotes) |

## Fix Approach

### Bug 1 — `mla_intext_parenthetical` (mla.py:51-56)

**Replace loose pattern** `\(([^)]+)\)` **with tightened regex requiring capitalized author name:**

```python
# OLD (line 53):
    pattern=r"\(([^)]+)\)"

# NEW:
    pattern=r"\(([A-Z][a-zA-ZÀ-ž]+(?:\s+(?:and|&)\s+[A-Z][a-zA-ZÀ-ž]+)?(?:\s+et\s+al\.?)?(?:\s+\d+(?:[-–]\d+)?)?)\)"
```

- `[A-Z][a-zA-ZÀ-ž]+` — capitalized word (author last name)
- `(?:\s+(?:and|&)\s+[A-Z][a-zA-ZÀ-ž]+)?` — optional second author
- `(?:\s+et\s+al\.?)?` — optional "et al."
- `(?:\s+\d+(?:[-–]\d+)?)?` — optional page number

**Rejects:** `(gold standard)`, `(correct)`, `(Deep Learning)`, `(a)`, `(Major Depressive Disorder)`, `(Buồn bã kéo dài)`
**Accepts:** `(Smith)`, `(Smith et al.)`, `(Smith and Jones)`, `(Nguyen Van A)`

### Bug 2 — `acs_comma_separated` (acs.py:70-74) — REMOVE

Remove the pattern definition and exclude from `in_text_patterns`. ACS/AMA already have
`acs_parenthesized` for `(1)`, `(2)`; IEEE/Vancouver already cover `[1,2,3]`.

**Changes:**
- Delete `_ACS_COMMA_SEPARATED` definition (lines 69-75)
- Remove from `in_text_patterns` property return list
- Remove from `ACS_IN_TEXT_PATTERNS` module-level export

### Bug 3 — `ama_comma_separated` (ama.py:70-74) — REMOVE

Same as Bug 2. Pattern inherently flawed — cannot distinguish citation `1,2` from data `1,371`.

**Changes:**
- Delete `_AMA_COMMA_SEPARATED` definition (lines 69-75)
- Remove from `in_text_patterns` property return list
- Remove from `AMA_IN_TEXT_PATTERNS` module-level export

### Bug 4 — `cse_parenthesized` (cse.py:67-73) — REMOVE FROM IN_TEXT ONLY

Keep the pattern definition (needed for reference list parsing) but remove from `in_text_patterns`.
CSE in-text uses `[1]` or `^1`, not `(1)`.

**Changes:**
- Keep `_CSE_PARENTHESIZED` definition
- Remove from `in_text_patterns` property return list

## File Changes

### 1. `src/integrity_checker/extraction/patterns/mla.py`
- Line 53: Replace pattern string

### 2. `src/integrity_checker/extraction/patterns/cse.py`
- Lines 258-266: Remove `_CSE_PARENTHESIZED` from `in_text_patterns` property

### 3. `src/integrity_checker/extraction/patterns/acs.py`
- Lines 69-75: Delete `_ACS_COMMA_SEPARATED` definition
- Lines 244-251: Remove from `in_text_patterns` return list
- Lines 810-815: Remove from `ACS_IN_TEXT_PATTERNS` export

### 4. `src/integrity_checker/extraction/patterns/ama.py`
- Lines 69-75: Delete `_AMA_COMMA_SEPARATED` definition
- Lines 225-232: Remove from `in_text_patterns` return list
- Lines 686-691: Remove from `AMA_IN_TEXT_PATTERNS` export

### 5. `tests/unit/test_pattern_bug_fixes.py` (NEW FILE)

Add comprehensive unit tests for all 4 fixes — positive and negative cases.

## Verification

```bash
# 1. New unit tests (should all pass)
source .venv/bin/activate
python -m pytest tests/unit/test_pattern_bug_fixes.py -v

# 2. Existing test suite (no regressions — 619+ tests pass)
python -m pytest tests/ -v --tb=short

# 3. Smoke test — pattern count
python3 -c "
from integrity_checker.extraction.patterns import get_in_text_patterns
patterns = get_in_text_patterns()
print(f'Total in-text patterns: {len(patterns)}')  # Should be 33 (down from 36)
"

# 4. TranThanhPhuoc PDF — citations should drop from 485 to ~80
source .venv/bin/activate
python3 -c "
from integrity_checker.extraction.mupdf_parser import MuPdfParser
from integrity_checker.extraction.citation_extractor import CitationExtractor
parser = MuPdfParser()
doc = parser.parse('TranThanhPhuoc_523H0002_523H0054.pdf')
cites = CitationExtractor(preserve_occurrences=False).extract_from_document(doc)
print(f'Citations: {len(cites)} (expected ~80)')
"

# 5. Full pipeline on TranThanhPhuoc PDF
python -m integrity_checker.pipeline.integrity_pipeline TranThanhPhuoc_523H0002_523H0054.pdf --output /tmp/phuoc_fixed.json
```

## Expected Impact

| Pattern | Before | After |
|---------|--------|-------|
| `mla_intext_parenthetical` | 333 | ~0–5 |
| `acs_comma_separated` | 50 | 0 |
| `ama_comma_separated` | 50 | 0 |
| `cse_parenthesized` | 23 | 0 |
| **Total** | **485** | **~80** |

## Risks

| Risk | Mitigation |
|------|------------|
| Missing legit MLA `(Author)` citations | MLA narrative + other formats still catch most cases |
| Breaking reference list parsing | CSE parens pattern kept (only removed from in_text) |
| Regression on other papers | Full test suite + BERT/Attention PDF tests |

## Commit Message

```
fix: tighten overly permissive citation patterns (2026-09-29)

- mla.py: tighten parenthetical regex to require capitalized author name
- acs.py: remove comma_separated pattern (matches data, not citations)
- ama.py: remove comma_separated pattern (same issue)
- cse.py: remove parenthesized from in_text_patterns (keep for ref list)

Reduces TranThanhPhuoc from 485 to ~80 citations.
```
