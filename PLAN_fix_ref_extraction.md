# Plan: Fix Reference Extraction & Linking for PDFs without "References" Header

## Context

User uploaded `VietDepression_Research_Article.pdf` (19 pages, IEEE-style with 18 numeric citations).
The current pipeline returns **33 unresolved citations, 0 extracted references** — every citation shows
"Missing Reference" and "Unresolved" with reasoning "Tất cả API đều fail — không đủ bằng chứng để kết luận."

Root cause (verified by tracing the pipeline):

1. **`SectionSegmenter` fails to detect bibliography** because the PDF has no explicit `References` header.
   The bibliography just starts mid-document on page 18 with `[8] Y. Liu et al., "RoBERTa..."`.
   Result: `body_citations` ends up containing both real in-text citations [1]–[18] AND
   16 spurious DOI/URL fragments from the bibliography pages; `references` is `[]`.

2. **Bare numeric citations cannot resolve via APIs.** `[1]` alone has no DOI/title/author, so
   Crossref/OpenAlex/Semantic Scholar/arxiv all return 404 → `unresolved`.

3. **Reference entries are not parsed at all** because the bibliography region is part of "body",
   so neither `_extract_references` nor `ReferenceListParser` runs against it.

4. **`_populate_citation_metadata` never fires** because `link_by_raw_text` lookup keys are
   normalized via `_normalize_identifier` (DOI/URL forms), not by the `[N]` numeric index — so
   the in-text `[1]` cannot be linked to whatever is in `references` (which is empty anyway).

## Goal

Fix the extraction → linking → metadata-population chain so that:
- References in IEEE format (numeric `[N]` + author + title + venue + DOI/URL) are extracted even
  when the PDF has no "References" / "Bibliography" header.
- In-text numeric citations `[N]` are linked to the corresponding reference entry by `numeric_index`.
- The matched reference's `title`, `authors`, `year`, `doi`, `venue` are copied onto the in-text
  citation **before** retrieval runs, so the APIs can resolve them.
- The pipeline still works for APA-style papers and for papers that DO have a header.

## Approach

### Fix 1 — Robust implicit-bibliography detection in `SectionSegmenter`

File: `src/integrity_checker/extraction/section_segmenter.py`

Add a second detection path in `_find_boundaries` that runs when no explicit header is found:

```
IF no bibliography header found anywhere:
    for each page (after the first 50% of the doc to avoid false positives on abstract pages):
        count lines matching r'^\s*\[\d+\]\s+\S'  (IEEE reference markers)
        count sentences ending in '. ' (regular prose)
        ratio = ieee_lines / max(1, ieee_lines + sentences)
        IF ratio >= 0.30 AND ieee_lines >= 3:
            this page starts an implicit bibliography
```

Use the first such page as `biblio_start`. Continue accumulating pages until a page has no
`[N]` markers AND has substantial prose → that's where bibliography ends.

### Fix 2 — Run `ReferenceListParser` over the detected bibliography section

File: `src/integrity_checker/extraction/document_parser.py`

No code change needed in the merge step — it already calls `self._reference_parser` against
sections where `section_type == BIBLIOGRAPHY`. Once Fix 1 makes the segmenter return a proper
BIBLIOGRAPHY section, the existing pipeline will pick it up.

### Fix 3 — Strip spurious DOI/URL fragments from body citations

File: `src/integrity_checker/extraction/citation_extractor.py`

Currently pages 18–19 produce citations with `raw_text='10.1609/icwsm.v7i1.14432.'` because the
DOI regex fires inside a "body" page. After Fix 1, these pages become BIBLIOGRAPHY, so the
extractor will skip them (it already does — `_extract_body_citations` only runs on BODY).

No code change here — this is fixed for free once Fix 1 lands.

### Fix 4 — Fallback reference entry parser when IEEE regex fails

File: `src/integrity_checker/extraction/reference_parser.py`

Current `_parse_entry` returns `None` if APA / IEEE / Vancouver regexes all fail, even when the
entry starts with `[N]` and has extractable DOI/URL. Add a fallback **inside `_parse_entry`** that:

- If entry starts with `[N]`, extract `numeric_index`.
- Extract DOI / arXiv URL / authors (year) from `entry`.
- Build a `Citation` with `style=IEEE`, `numeric_index=N`, those fields, and `confidence=0.7`.

This handles real-world IEEE entries where the title doesn't have quotes or the entry is
broken across lines.

### Fix 5 — Index link lookup by numeric index, not just normalized identifier

File: `src/integrity_checker/pipeline/integrity_pipeline.py::_build_link_lookup`

The current lookup uses `_normalize_identifier(citation.raw_text)` which maps `[1]` → `1`
(lowercased, punctuation-stripped) — but the evidence stored in the link is the in-text
citation's `raw_text` (which is `[1]` itself, not a DOI). They won't match.

Fix: also index each link by:
- The numeric index extracted from the in-text `raw_text` (e.g. `1`, `2` for `[1]`, `[1-3]`).
  Map: `[N]` → `{N}`, `[1,2]` → `{1, 2}`, `[1-3]` → `{1, 2, 3}`.

And, in `_populate_citation_metadata`, accept either:
- a normalized-identifier match (current behavior), OR
- a numeric-index match against an IEEE-style reference's `numeric_index`.

### Fix 6 — Populate metadata on numeric in-text citations before retrieval

File: `src/integrity_checker/pipeline/integrity_pipeline.py::_populate_citation_metadata`

After linking, for each in-text citation that has only `[N]`:
- Find the link by the numeric index path (Fix 5).
- Copy `title`, `authors`, `year`, `doi`, `venue` from the matched reference.
- This makes the subsequent `RetrieverOrchestrator.retrieve(citation)` succeed because the
  DOI/title are now present.

This step is already implemented — it just needs the link lookup to find the link for `[N]`.

## Critical files to modify

- `src/integrity_checker/extraction/section_segmenter.py` — add implicit-bibliography detection.
- `src/integrity_checker/extraction/reference_parser.py` — fallback parser for IEEE entries with
  DOI/URL but no quoted title.
- `src/integrity_checker/pipeline/integrity_pipeline.py` — index link lookup by numeric index
  and populate metadata accordingly.

## Tests to add

`tests/unit/test_bibliography_detection.py` (new):
- PDFs without explicit "References" header but with `[N]`-pattern pages → bibliography detected.
- PDFs WITH explicit header → behavior unchanged.

`tests/unit/test_reference_parser.py` (extend):
- IEEE entry with only DOI, no quoted title → returns Citation with `numeric_index`, `doi`,
  fallback `confidence=0.7`.

`tests/unit/test_pipeline_linking.py` (new):
- In-text `[1]` ↔ reference with `numeric_index=1` → link `MATCHED`, metadata populated.
- In-text `[1]` when no matching reference exists → `MISSING_REFERENCE`, retrieval uses fallback.

## Verification

1. Run the V1 pipeline against `VietDepression_Research_Article.pdf`:
   ```
   source .venv/bin/activate
   python -m integrity_checker.pipeline.integrity_pipeline \
       VietDepression_Research_Article.pdf --output /tmp/vietdep.json
   ```
   Expect: `references >= 18`, `body_citations` ≈ 18 numeric (not 33), at least 12 of 18
   `[N]` citations resolved against APIs, `missing_reference` count drops from 18 to ≤ 6.

2. Run the existing test suite:
   ```
   python -m pytest tests/ -v
   ```
   Expect: 576+ existing tests still pass + new tests pass.

3. Upload the same PDF via the FastAPI endpoint and confirm the VerdictTable now shows real
   "Verified" / "Neural content alignment verified" verdicts instead of 18× "Unresolved".

## Out of scope

- Improving GROBID extraction (GROBID is unavailable; not running).
- Improving APA author-year linking (already works for APA papers).
- Adding a frontend-side change (the bug is purely backend extraction/linking).
