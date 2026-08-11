---
name: sprint-2-week8-progress
description: Sprint 2 Tuần 8 — ALL TASKS #20-#30 hoàn thành, 346/346 tests pass
metadata:
  type: project
---

# Sprint 2 — Tuần 8 Progress Summary

**Ngày:** 2026-08-11 (final session)
**Trạng thái:** ALL TASKS #20–#30 ✅ hoàn thành. **346/346 tests pass.**

## Tasks Completed (All 11 tasks)

| # | Task | Status | Tests |
|---|---|---|---|
| #20 | `linking/` package (statuses, CitationLinker, DuplicateDetector) | ✅ | 57 |
| #21 | `document_parser.py` orchestrator | ✅ | 10 |
| #22 | ReferenceListParser backlog fix (Dutch + 2-line APA) | ✅ | 21 |
| #23 | 4 real API clients (Crossref, OpenAlex, S2, arXiv) | ✅ | 12 |
| #24 | AuthorMatcher + VenueNormalizer | ✅ | 94 |
| #25 | VenueNormalizer (verify) | ✅ | (included above) |
| #26 | SourceConsensus | ✅ | (included above) |
| #27 | FuzzyTuner + CalibrationCalculator | ✅ | (included above) |
| #28 | rules.py + CIS real components | ✅ | 17 |
| #29 | Integration end-to-end pipeline | ✅ | 13 |
| #30 | IAA measurement (Cohen's kappa + Krippendorff's alpha) | ✅ | 16 |

**Total: 346/346 tests pass.**

## Key Deliverables

### metrics/iaa_calculator.py (NEW — task #30)
```python
from integrity_checker.metrics import compute_iaa, cohen_kappa, krippendorffs_alpha
results = compute_iaa("iaa_annotator_A.csv", "iaa_annotator_B.csv")
# results['cohen_kappa_overall'], results['krippendorff_alpha'], results['target_met']
```
CLI: `python -m integrity_checker.metrics.iaa_calculator csv_a csv_b --output result.json`

### All 4 matching modules verified (task #24–#27):
- AuthorMatcher, VenueNormalizer, SourceConsensus, FuzzyTuner, CalibrationCalculator
- 94 tests pass across 5 test files

### Backward compat fixes:
- `StyleProfile` accepts `style=`, `apa_count=`, `evidence=`
- `CitationLink.method` is `str | MappingMethod`
- `CitationOccurrence/ReferenceEntry` stubs
- Pipeline uses actual `CitationLinker.link()` API

## Command
```bash
source .venv/bin/activate
PYTHONPATH=src python3 -m pytest tests/ --noconftest
# Expected: 346 passed, 27 warnings
```

## Tasks Completed

| # | Task | Tests | Notes |
|---|---|---|---|
| #20 | `linking/` package scaffold | 57/57 ✅ | CitationMappingStatus (8 values), CitationLinker, DuplicateDetector, LinkingResult |
| #21 | `document_parser.py` orchestrator | 10/10 ✅ | Already existed, verified working |
| #22 | Backlog: Dutch + 2-line APA fix | 21/21 ✅ | Already fixed, verified |
| #23 | 4 real API clients | 12/12 ✅ | Already implemented |

## Total Test Count

**330/330 tests pass** (unit + integration)

## Key Technical Decisions

### CitationLinker API
- Dùng `Citation[]` trực tiếp thay vì `CitationOccurrence/ReferenceEntry` wrappers
- Match priority: DOI exact → NUMERIC_INDEX → AUTHOR_YEAR (+ year_suffix) → FUZZY
- Same reference entry có thể match nhiều in-text occurrences (valid use)
- `Author` objects (từ `author_parser.py`) được hỗ trợ trong author normalization

### CitationMappingStatus (8 values)
```
MATCHED, MISSING_REFERENCE, UNCITED_REFERENCE, IN_TEXT_MISMATCH,
DUPLICATE_REFERENCE, AMBIGUOUS_MAPPING, STYLE_INCONSISTENT, UNRESOLVED
```
Penalty table: MISSING=1.0, MISMATCH=0.8, DUPLICATE=0.6, UNCITED=0.5, AMBIGUOUS=0.4, STYLE=0.2

### Backward Compatibility Fixes
- `StyleProfile` chấp nhận `style=`, `apa_count=`, `numeric_count=`, `evidence=` (old API)
- `CitationLink.method` là `str | MappingMethod` (pipeline pass strings)
- `CitationOccurrence` + `ReferenceEntry` stubs trong `linking/statuses.py`

### Files Created/Modified
- `src/integrity_checker/linking/statuses.py` (mới)
- `src/integrity_checker/linking/citation_linker.py` (mới)
- `src/integrity_checker/linking/duplicate_detector.py` (mới)
- `src/integrity_checker/linking/__init__.py` (mới)
- `tests/unit/test_linking_statuses.py` (viết lại)
- `tests/unit/test_citation_linker.py` (viết lại)
- `tests/unit/test_duplicate_detector.py` (mới)
- `src/integrity_checker/extraction/style_detector.py` (thêm backward compat)
- `src/integrity_checker/models/validation.py` (CitationLink.method fix)
- `src/integrity_checker/pipeline/integrity_pipeline.py` (dùng actual API)
- `tests/unit/test_rules_v12.py` (fix import)

## Next Tasks Pending
- #24: AuthorMatcher
- #25: VenueNormalizer
- #26: SourceConsensus
- #27: FuzzyTuner + CalibrationCalculator
- #28: rules.py + CIS real components
- #29: Integration end-to-end (M3 milestone)
- #30: IAA measurement

## Command
```bash
source .venv/bin/activate
PYTHONPATH=src python3 -m pytest tests/ -v --noconftest
# Expected: 330 passed, 27 warnings
```
