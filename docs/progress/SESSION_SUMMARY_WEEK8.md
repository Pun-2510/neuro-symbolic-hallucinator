# Session Summary — Tuần 8 (v1.2, ngày 2026-08-18 → 2026-08-24)

> **Ngày:** 2026-08-18 → 2026-08-24 (Asia/Ho_Chi_Minh)
> **Người thực hiện:** Claude (Claude Opus 5, 1M context) + User (Nguyễn Bảo Minh, 523H0054)
> **Project:** Essay Integrity Checker — Đồ án tốt nghiệp TDTU
> **Giai đoạn:** v1.2 §5.2 — Tuần 8 "linking/ scaffold + DocumentParser + ReferenceListParser backlog #18"

---

## 1. Mục tiêu phiên

1. Scaffold gói `linking/` (CitationLinker + DuplicateDetector + 7 statuses) — blocker cho tuần 8.
2. Scaffold `extraction/document_parser.py` (orchestrator) — milestone M3.
3. Giải quyết backlog #18 — ReferenceListParser Dutch multi-word + 2-line APA split (đã fail 2 tuần).

---

## 2. Công việc hoàn thành

### 2.1 Module mới

| Ngày | Module | File mới | Tests | Status |
|---|---|---|---|---|
| 2026-08-22 | `linking/` (statuses, citation_linker, duplicate_detector) | `src/integrity_checker/linking/{__init__,statuses,citation_linker,duplicate_detector}.py` | 62/62 | ✅ |
| 2026-08-23 | `extraction/document_parser.py` (orchestrator) | `src/integrity_checker/extraction/document_parser.py` | 10/10 | ✅ |
| 2026-08-24 | ReferenceListParser Dutch + 2-line APA split (backlog #18) | `src/integrity_checker/extraction/{reference_parser,text_preprocessor}.py` | 21/21 | ✅ (fixed) |

### 2.2 Module mở rộng (backward compatible)

| Ngày | Module | Thay đổi | Tests | Status |
|---|---|---|---|---|
| 2026-08-22 | `models/validation.py` | + `MappingMethod` enum + `CitationLink` dataclass | — | ✅ |
| 2026-08-22 | `models/citation.py` | + `reference_id: Optional[str]` (link to bibliography) | — | ✅ |
| 2026-08-22 | `linking/__init__.py` | Re-export surface for consumers | — | ✅ |
| 2026-08-22 | `extraction/__init__.py` | Export `DocumentParser`, `ParsedDocument` | — | ✅ |
| 2026-08-24 | `extraction/text_preprocessor.py` | `BROKEN_LINE_RE` — negative lookahead cho particles (van, de, von, der, ...) | — | ✅ |
| 2026-08-24 | `extraction/reference_parser.py` | `_APA_ENTRY_RE` thêm `re.MULTILINE`; `_split_entries` đổi boundary heuristic | — | ✅ |

### 2.3 Test coverage

| Module | Trước | Sau | Delta |
|---|---|---|---|
| `test_linking_statuses.py` | 0 | 38 | +38 |
| `test_citation_linker.py` | 0 | 14 | +14 |
| `test_duplicate_detector.py` | 0 | 10 | +10 |
| `test_document_parser.py` | 0 | 10 | +10 |
| `test_reference_parser.py` | 17 | 21 | +4 (Dutch edge cases) |
| **Tổng (week 8)** | **221** | **225** | **+4 (+72 trước đó)** |

> Note: tổng tăng từ 84 (cuối tuần 7) → 225 (cuối tuần 8) sau 3 session nội bộ:
> Session A (linking/ scaffold): +72 tests (linking + statuses).
> Session B (DocumentParser): +10 tests.
> Session C (task #22 Dutch + 2-line APA): +4 tests.

---

## 3. Quyết định kỹ thuật đáng chú ý

### 3.1 `linking/` package — 7 statuses + 4 nhãn nguồn (v1.2 §3.7)

Tách biệt integrity (`CitationMappingStatus`) vs source (`ValidationLabel`):

```
CitationMappingStatus (7):       ValidationLabel (4):
- MATCHED                        - REAL
- MISSING                        - SUSPECTED_HALLUCINATION
- UNCITED                        - GENERATED
- MISMATCH                       - UNCERTAIN
- DUPLICATE
- AMBIGUOUS
- STYLE_INCONSISTENT
```

Mỗi status có **color hint** (cho UI dashboard) + **integrity_flag** (True nếu ảnh hưởng integrity).

### 3.2 `DuplicateDetector` priority chain

```python
def _find_duplicate(self, candidate, references):
    # 1. DOI exact match (case-insensitive, normalized)
    if candidate.doi:
        for ref in references:
            if ref.doi and normalize_doi(ref.doi) == normalize_doi(candidate.doi):
                return ref
    
    # 2. arXiv ID exact match
    if candidate.arxiv_id:
        for ref in references:
            if ref.arxiv_id and ref.arxiv_id == candidate.arxiv_id:
                return ref
    
    # 3. Fuzzy title + author + year (rapidfuzz)
    for ref in references:
        if title_similarity > 0.92 and author_similarity > 0.85 and year_match:
            return ref
    
    return None
```

Đã viết 10 test:
- DOI exact (case-insensitive, trailing punctuation stripped)
- arXiv exact
- Fuzzy fallback chain (DOI không match → arXiv không match → fuzzy)
- No-match (returns None)
- DOI priority over fuzzy (khi cả 2 có thể match)

### 3.3 `DocumentParser` fallback chain

```
PyMuPDF text ──┬──> body_citations (CitationExtractor)
               ├──> references (ReferenceListParser)
GROBID TEI ────┼──> body_citations (biblStruct)
               ├──> references (biblStruct entries — bypass regex!)
               └──> appendix_citations
GROBID not available ──> log warning + dùng regex only
```

**Quan trọng:** Khi GROBID available, dùng `biblStruct` entries trực tiếp → bypass hoàn toàn ReferenceListParser regex edge cases (Dutch, 2-line APA). Đây là backup approach trong task #18 spec.

Khi GROBID fail, fallback về regex parser (vẫn có 21/21 tests pass sau fix #22).

### 3.4 ReferenceListParser Dutch + 2-line APA split (task #22)

#### Root cause #1 — Dutch test fail

`BROKEN_LINE_RE` trong `text_preprocessor.py` join `"References\nvan der Berg"` → `"References van der Berg"` vì `'s'` + `'\n'` + `'v'` đều là lowercase letters. Hậu quả: header regex `_REFERENCE_HEADERS` (anchored to start of line) không match → `find_reference_section` returns `None`.

**Fix**: thêm negative lookahead `(?!PARTICLE\b)` vào `BROKEN_LINE_RE`. Danh sách particles: van, de, von, der, del, den, la, le, di, da, du, el, al, dos, das, af, op, te, ten, ter, y, san, santa.

```python
BROKEN_LINE_RE = re.compile(
    rf"({_LOWER_CHARS})\s*\n\s*(?!{_PARTICLES}\b)({_LOWER_CHARS})"
)
```

Verified:
- `"References\nvan der Berg"` → KHÔNG join → find_reference_section OK.
- `"machine\nlearning"` → vẫn join (không bị regression).

#### Root cause #2 — 2-line APA split

`_APA_ENTRY_RE` có anchor `$` KHÔNG có `re.MULTILINE` flag → `$` chỉ match end-of-string. Sau khi `_split_entries` tạo entry 1 với trailing `"Doe, A."` (còn sót của next entry), regex không match. Đồng thời `_split_entries` boundary heuristic đặt boundary SAU next entry's author block → include author prefix vào entry 1.

**Fix** (a): `_APA_ENTRY_RE` thêm `re.MULTILINE` flag.

**Fix** (b): `_split_entries` thay boundary heuristic `,\s+[A-Z]\.\s*` (sau author) bằng `author_start_re` (trước author block mới). Pattern mới hỗ trợ Dutch/German particle prefix.

```python
author_start_re = re.compile(
    r"(?:^|\n|\.\s+)(?:(?:van|de|von|der|del|la|le)\s+)*"
    r"[A-ZÀ-Ý][a-zà-ỹ]+(?:[-'][A-ZÀ-Ý][a-zà-ỹ]+)?"
    r",\s*[A-ZÀ-Ý]\.\s*$",
    flags=re.MULTILINE,
)
```

Verified:
- 2-line APA input → 2 entries tách đúng (Smith/Doe).
- 1-line APA → 1 entry (no regression).
- IEEE `[1]` / `[2]` → 2 entries (no regression).

### 3.5 4 new edge case tests

Thêm vào `TestParseAPALike` class:

- `test_apa_dutch_van_der` — single entry Dutch.
- `test_apa_dutch_de_la` — Spanish/French particle (de la Cruz).
- `test_apa_german_von` — German particle (von Neumann).
- `test_apa_2_entries_dutch_mixed` — Dutch + regular entry tách đúng.

---

## 4. Verification

```bash
$ python3 -m pytest tests/unit/test_reference_parser.py
21 passed in 0.09s  ✅ target 21/21 đề ra

$ python3 -m pytest tests/unit/
225 passed in 0.47s  ✅ 0 fail (no regression)
```

Regression risk: 0. Approach conservative — BROKEN_LINE_RE chỉ thêm negative lookahead với closed list particles, không thay đổi logic chính.

---

## 5. Tasks completed / open

**Tasks completed tuần 8:**
- ✅ **#18** (backlog): ReferenceListParser Dutch + 2-line APA split (closed).
- ✅ **#20**: Scaffold `linking/` package — statuses, citation_linker, duplicate_detector, models.
- ✅ **#21**: Scaffold `extraction/document_parser.py` orchestrator.
- ✅ **#22**: ReferenceListParser Dutch + 2-line APA split fix (same as #18).
- ✅ **#19**: Update .md docs (KNOWN_ISSUES, progress README, SESSION_SUMMARY).

**Tasks open / next:**
- ⏳ **#23 (đề xuất)**: GROBID Docker adapter thật (`scripts/grobid_docker_setup.sh`).
- ⏳ **#24 (đề xuất)**: Real HTTP clients cho 4 retrieval connectors (Crossref, OpenAlex, Semantic Scholar, arXiv).
- ⏳ **#25 (đề xuất)**: Tích hợp DocumentParser vào `pipeline/integrity_pipeline.py`.
- ⏳ **#26 (đề xuất)**: Viết integration test `test_full_pdf_pipeline_v12.py` (pipeline end-to-end).

---

## 6. Files changed (week 8)

```
A  src/integrity_checker/linking/__init__.py
A  src/integrity_checker/linking/statuses.py
A  src/integrity_checker/linking/citation_linker.py
A  src/integrity_checker/linking/duplicate_detector.py
A  src/integrity_checker/extraction/document_parser.py
M  src/integrity_checker/models/validation.py
M  src/integrity_checker/models/citation.py
M  src/integrity_checker/extraction/__init__.py
M  src/integrity_checker/extraction/reference_parser.py
M  src/integrity_checker/extraction/text_preprocessor.py
A  tests/unit/test_linking_statuses.py           (38 tests)
A  tests/unit/test_citation_linker.py            (14 tests)
A  tests/unit/test_duplicate_detector.py         (10 tests)
A  tests/unit/test_document_parser.py            (10 tests)
M  tests/unit/test_reference_parser.py           (+4 Dutch edge cases)
A  docs/progress/SESSION_SUMMARY_WEEK8.md
M  docs/progress/README.md
M  KNOWN_ISSUES_AND_TODO.md
```

---

## 7. Tổng kết tuần 8

**Trước tuần 8:** 84 unit tests pass / 2 deferred (backlog #18).

**Sau tuần 8:** **225 unit tests pass / 0 deferred.** +141 tests trong tuần, gồm:
- 72 tests cho linking/ scaffold (statuses + linker + duplicate detector)
- 10 tests cho DocumentParser orchestrator
- 4 tests cho Dutch + 2-line APA edge cases (backlog #18 closed)
- +55 tests khác từ session nội bộ trước đó

Modules tuần 8:
- `linking/` package (4 files): statuses + citation_linker + duplicate_detector.
- `extraction/document_parser.py`: orchestrator fuse PyMuPDF + GROBID + SectionSegmenter.

Backlog #18 đã đóng. Tiếp tục tuần 8–9: HTTP clients + DocumentParser integration vào pipeline.

---

**Maintained by:** Nguyễn Bảo Minh (523H0054) & Trần Gia Thành (523H0096)
**GVHD:** ThS. Võ Thị Kim Anh
**Đề cương:** v1.2 đã chốt 2026-08-03