"""CitationLinker — bidirectional linker in-text ↔ reference entry (v1.2 §3.5).

Mục tiêu:
    Với danh sách body citations (in-text occurrences) và bibliography entries,
    tạo citation graph bằng cách match mỗi in-text occurrence với ≥0 reference
    entry, và mỗi reference entry với ≥0 in-text occurrence.

Match logic (theo priority):
    1. **DOI exact** — cả 2 đều có DOI trích dẫn trong raw_text → chắc chắn nhất.
    2. **NUMERIC_INDEX** (IEEE) — in-text `[N]` ↔ bib `numeric_index == N`.
    3. **AUTHOR_YEAR** (APA) — `(Author, Year)` ↔ bib `author.last_name` + `year`.
    4. **FUZZY** — normalized title similarity fallback.

Outputs:
    - list[CitationLink] (1 per in-text occurrence)
    - list of unmatched in-text (→ MISSING_REFERENCE)
    - list of unmatched reference entries (→ UNCITED_REFERENCE)
    - duplicate groups (→ DUPLICATE_REFERENCE)

References:
    v1.2 §3.5 (bidirectional linking)
    v1.2 §3.7 (linking styles — style consistency)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from integrity_checker.linking.statuses import (
    CitationMappingStatus,
    LinkingResult,
)
from integrity_checker.models.citation import Citation, CitationStyle, CitationType
from integrity_checker.models.validation import CitationLink, MappingMethod

logger = logging.getLogger(__name__)

# Regex cho in-text APA pattern: (Author, Year)
_APA_YEAR_RE = re.compile(r"\(([A-Za-zÀ-ÿ'.\s-]+),\s*((?:19|20)\d{2}[a-z]?)\)")
# Regex cho in-text IEEE numeric: [N] or [N, M] or [N-M]
_IEEE_NUM_RE = re.compile(r"\[(\d+(?:\s*[-–,]\s*\d+)*)\]")
# Regex cho year extraction từ bib entry
_BIB_YEAR_RE = re.compile(r"\((?:19|20)\d{2}[a-z]?\)|(?:19|20)\d{2}[a-z]?")


class CitationLinker:
    """Bidirectional linker in-text ↔ reference entry."""

    def __init__(
        self,
        fuzzy_threshold: float = 0.80,
        author_year_confidence: float = 0.90,
        numeric_confidence: float = 0.90,
        doi_confidence: float = 0.95,
        fuzzy_confidence: float = 0.65,
    ) -> None:
        """
        Args:
            fuzzy_threshold: ngưỡng similarity cho fuzzy match.
            author_year_confidence: confidence khi match by author+year.
            numeric_confidence: confidence khi match by numeric index.
            doi_confidence: confidence khi match by DOI.
            fuzzy_confidence: confidence khi fuzzy fallback.
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.author_year_confidence = author_year_confidence
        self.numeric_confidence = numeric_confidence
        self.doi_confidence = doi_confidence
        self.fuzzy_confidence = fuzzy_confidence

    def link(
        self,
        body_citations: list[Citation],
        bib_citations: list[Citation],
    ) -> LinkingResult:
        """Link in-text occurrences ↔ reference entries.

        Args:
            body_citations: Citation[] từ body (IN_TEXT / NUMERIC type).
            bib_citations: Citation[] từ bibliography (REFERENCE_LIST type).

        Returns:
            LinkingResult với:
            - links: list[CitationLink] (1 per body_citations)
            - unmatched_in_text: IDs của in-text không match bib nào
            - unmatched_reference_ids: IDs của bib không match in-text nào
            - status_counts: summary
        """
        result = LinkingResult(
            total_citations=len(body_citations),
            total_references=len(bib_citations),
        )

        # Index bib citations by different keys
        bib_by_doi = self._index_by_doi(bib_citations)
        bib_by_index = self._index_by_numeric(bib_citations)
        bib_by_author_year = self._index_by_author_year(bib_citations)
        bib_by_author_year_suffix = self._index_by_author_year_suffix(bib_citations)

        # Track which bib entries are matched (by index)
        # NOTE: same bib can be matched by multiple in-text occurrences
        bib_matched: set[int] = set()

        for i, cit in enumerate(body_citations):
            occ_id = cit.reference_id or f"occ-{i:04d}"

            # Try match methods in priority order
            link = self._try_match(
                cit, occ_id, bib_by_doi, bib_by_index,
                bib_by_author_year, bib_by_author_year_suffix,
                bib_citations
            )

            if link is not None:
                result.add_link(link)
                # Track matched bibs (without blocking reuse)
                if link.reference_id:
                    for idx, bib in enumerate(bib_citations):
                        if (bib.reference_id or f"ref-{idx:04d}") == link.reference_id:
                            bib_matched.add(idx)
                            break
            else:
                # No match → MISSING_REFERENCE
                result.add_link(
                    CitationLink(
                        occurrence_id=occ_id,
                        reference_id=None,
                        status=CitationMappingStatus.MISSING_REFERENCE,
                        confidence=0.0,
                        method=MappingMethod.NO_KEYS,
                    )
                )

        # Find unmatched bib entries → UNCITED_REFERENCE
        for i, bib in enumerate(bib_citations):
            if i not in bib_matched:
                result.unmatched_reference_ids.append(bib.reference_id or f"ref-{i:04d}")

        return result

    # -- internal helpers --

    def _try_match(
        self,
        cit: Citation,
        occ_id: str,
        bib_by_doi: dict[str, Citation],
        bib_by_index: dict[int, Citation],
        bib_by_author_year: dict[tuple[str, str], list[Citation]],
        bib_by_author_year_suffix: dict[tuple[str, str, str], list[Citation]],
        bib_citations: list[Citation],
    ) -> Optional[CitationLink]:
        """Try matching in priority: DOI → NUMERIC → AUTHOR_YEAR → FUZZY.

        NOTE: No blocking — same reference entry can match multiple in-text
        occurrences. This is valid: the same source may be cited multiple times.
        Unmatched references (uncited entries) are detected after all linking.
        """

        # 1. DOI exact
        doi = self._extract_doi(cit.raw_text)
        if doi and doi in bib_by_doi:
            bib_match = bib_by_doi[doi]
            bib_idx = self._find_bib_index(bib_match, bib_citations)
            return CitationLink(
                occurrence_id=occ_id,
                reference_id=bib_match.reference_id or f"ref-{bib_idx:04d}",
                status=CitationMappingStatus.MATCHED,
                confidence=self.doi_confidence,
                method=MappingMethod.DOI_EXACT,
            )

        # 2. NUMERIC_INDEX (IEEE)
        if cit.citation_type == CitationType.NUMERIC:
            indices = self._extract_numeric_indices(cit.raw_text)
            for idx in indices:
                if idx in bib_by_index:
                    bib_ref = bib_by_index[idx]
                    bib_idx = self._find_bib_index(bib_ref, bib_citations)
                    return CitationLink(
                        occurrence_id=occ_id,
                        reference_id=bib_ref.reference_id or f"ref-{bib_idx:04d}",
                        status=CitationMappingStatus.MATCHED,
                        confidence=self.numeric_confidence,
                        method=MappingMethod.NUMERIC_INDEX,
                    )

        # 3. AUTHOR_YEAR (APA-like)
        author, year, year_suffix = self._extract_author_year(cit.raw_text)
        if author and year:
            # Try exact match first (author + year + suffix)
            if year_suffix:
                key_suffix = (author.lower().strip(), year, year_suffix)
                candidates_suffix = bib_by_author_year_suffix.get(key_suffix, [])
                if candidates_suffix:
                    candidate = candidates_suffix[0]
                    bib_idx = self._find_bib_index(candidate, bib_citations)
                    return CitationLink(
                        occurrence_id=occ_id,
                        reference_id=candidate.reference_id or f"ref-{bib_idx:04d}",
                        status=CitationMappingStatus.MATCHED,
                        confidence=self.author_year_confidence,
                        method=MappingMethod.AUTHOR_YEAR,
                    )
            # Fallback: author + year only
            key = (author.lower().strip(), year)
            candidates = bib_by_author_year.get(key, [])
            if candidates:
                candidate = candidates[0]
                bib_idx = self._find_bib_index(candidate, bib_citations)
                return CitationLink(
                    occurrence_id=occ_id,
                    reference_id=candidate.reference_id or f"ref-{bib_idx:04d}",
                    status=CitationMappingStatus.MATCHED,
                    confidence=self.author_year_confidence,
                    method=MappingMethod.AUTHOR_YEAR,
                )

        # 4. FUZZY — title similarity (if bib entries have title_normalized)
        best = self._try_fuzzy(cit, occ_id, bib_by_doi, bib_citations)
        if best is not None:
            return best

        # No match
        return None

    def _try_fuzzy(
        self,
        cit: Citation,
        occ_id: str,
        bib_by_doi: dict[str, Citation],
        bib_citations: list[Citation],
    ) -> Optional[CitationLink]:
        """Fuzzy match: normalized title similarity."""
        if not cit.title_normalized:
            return None

        best_bib_idx = None
        best_score = 0.0

        for doi, bib in bib_by_doi.items():
            bib_idx = self._find_bib_index(bib, bib_citations)
            if bib_idx in bib_used:
                continue
            if bib.title_normalized:
                score = self._title_similarity(cit.title_normalized, bib.title_normalized)
                if score > best_score:
                    best_score = score
                    best_bib_idx = bib_idx

        if best_bib_idx is not None and best_score >= self.fuzzy_threshold:
            bib = bib_citations[best_bib_idx]
            return CitationLink(
                occurrence_id=occ_id,
                reference_id=bib.reference_id or f"ref-{best_bib_idx:04d}",
                status=CitationMappingStatus.MATCHED,
                confidence=best_score * self.fuzzy_confidence,
                method=MappingMethod.FUZZY,
            )
        return None

    def _find_bib_index(self, bib: Citation, bib_citations: list[Citation]) -> int:
        """Tìm index của bib trong bib_citations."""
        for i, b in enumerate(bib_citations):
            if b is bib:
                return i
        return 0

    # -- index builders --

    def _index_by_doi(self, bibs: list[Citation]) -> dict[str, Citation]:
        out: dict[str, Citation] = {}
        for bib in bibs:
            doi = (bib.doi or "").strip()
            if doi:
                out[doi.lower()] = bib
        return out

    def _index_by_numeric(self, bibs: list[Citation]) -> dict[int, Citation]:
        out: dict[int, Citation] = {}
        for bib in bibs:
            if bib.numeric_index is not None:
                out[bib.numeric_index] = bib
        return out

    def _index_by_author_year(
        self, bibs: list[Citation]
    ) -> dict[tuple[str, str], list[Citation]]:
        out: dict[tuple[str, str], list[Citation]] = {}
        for bib in bibs:
            if bib.authors and bib.year:
                last_name = self._normalize_last_name(bib.authors[0])
                if last_name:
                    key = (last_name.lower(), bib.year)
                    out.setdefault(key, []).append(bib)
        return out

    def _index_by_author_year_suffix(
        self, bibs: list[Citation]
    ) -> dict[tuple[str, str, str], list[Citation]]:
        """Index bibs by (last_name, year, year_suffix) for 2020a/2020b matching."""
        out: dict[tuple[str, str, str], list[Citation]] = {}
        for bib in bibs:
            if bib.authors and bib.year:
                last_name = self._normalize_last_name(bib.authors[0])
                year_suffix = bib.year_suffix or ""
                if last_name:
                    key = (last_name.lower(), bib.year, year_suffix)
                    out.setdefault(key, []).append(bib)
        return out

    def _normalize_last_name(self, raw: str | object) -> str:
        """Extract last name from author data.

        Handles:
            - str "Smith, J." → "Smith"
            - str "Smith J." → "Smith"
            - Author object → .last_name attribute
        """
        # Handle Author object from author_parser.py
        if not isinstance(raw, str):
            return getattr(raw, "last_name", "") or ""

        # String: "Smith, J." → "Smith"
        if "," in raw:
            last = raw.split(",")[0].strip()
        else:
            tokens = raw.split()
            last = tokens[0] if tokens else ""
        return last.strip()

    # -- extractors --

    def _extract_doi(self, text: str) -> Optional[str]:
        """Trích DOI từ raw text."""
        doi_match = re.search(
            r"10\.\d{4,}/[^\s\])\"'>]+", text, re.IGNORECASE
        )
        if doi_match:
            return doi_match.group(0).rstrip(".,;:").lower()
        return None

    def _extract_numeric_indices(self, text: str) -> list[int]:
        """Trích numeric indices từ IEEE-style [N] hoặc [N, M] hoặc [N-M]."""
        m = _IEEE_NUM_RE.search(text)
        if not m:
            return []
        parts = re.split(r"[\s,\-–]+", m.group(1))
        indices = []
        for p in parts:
            try:
                indices.append(int(p.strip()))
            except ValueError:
                pass
        return indices

    def _extract_author_year(self, text: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Trích (author, year, year_suffix) từ APA-style (Author, Year).

        Handles: (Smith, 2020) → ("smith", "2020", None)
                 (Smith, 2020a) → ("smith", "2020", "a")
                 (Smith, 2020b) → ("smith", "2020", "b")

        Returns:
            (normalized_last_name, year, year_suffix) — author đã được normalize
            để khớp với _index_by_author_year.
        """
        m = _APA_YEAR_RE.search(text)
        if m:
            raw_author = m.group(1).strip()
            year = m.group(2).strip()
            # Check for suffix letter after year: 2020a, 2020b
            year_suffix = None
            if len(year) == 5 and year[4] in "abcdfgh":
                year_suffix = year[4]
                year = year[:4]
            normalized = self._normalize_last_name(raw_author)
            return normalized, year, year_suffix
        return None, None, None

    def _title_similarity(self, a: str, b: str) -> float:
        """Normalized title similarity (0.0–1.0) dùng character overlap."""
        if not a or not b:
            return 0.0
        a_words = set(a.split())
        b_words = set(b.split())
        if not a_words or not b_words:
            return 0.0
        # Jaccard similarity
        intersection = len(a_words & b_words)
        union = len(a_words | b_words)
        return intersection / union if union > 0 else 0.0
