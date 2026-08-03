"""CitationLinker — bidirectional in-text ↔ reference entry (v1.2 §3.5).

Thuật toán tổng quan (sẽ chi tiết hoá ở tuần 6–7):

    1. Occurrence parsing: chuyển Citation (IN_TEXT) → CitationOccurrence.
    2. Reference entry parsing: chuyển Citation (REFERENCE_LIST) → ReferenceEntry.
    3. Chiều in-text → reference (forward):
        a. APA-like: (Author, Year) → match author + year + optional suffix.
        b. IEEE-like: [N] / [N-M] → match numeric_index.
        c. Có DOI → exact match.
        d. Fallback: normalized title + author + year fuzzy.
    4. Chiều reference → in-text (backward): tập reference_id đã match
        → UNCITED_REFERENCE = tập reference_entries - matched.
    5. Phát hiện IN_TEXT_MISMATCH: tìm candidate link, nhưng author/year
        hoặc số thứ tự KHÁC nhau.
    6. Phát hiện AMBIGUOUS_MAPPING: ≥2 candidate hợp lý ngang nhau.
    7. Phát hiện STYLE_INCONSISTENT: marker ở occurrence lệch khỏi style chủ đạo.

Skip occurrences nằm trong exclude_sections (config.linking.exclude_sections).

Reference:
    v1.2 §3.5 (Nhận diện kiểu trích dẫn và đối chiếu hai chiều)
    v1.2 §3.2.2 (mapping statuses)
    v1.2 Bảng 15 (trạng thái mapping + định nghĩa thao tác)
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Iterable, Optional

from integrity_checker.config import get_settings
from integrity_checker.linking.statuses import (
    CitationLink,
    CitationMappingStatus,
    CitationOccurrence,
    LinkingResult,
    ReferenceEntry,
    StyleProfile,
)

logger = logging.getLogger(__name__)


# --- Regex patterns (v1.2 Bảng 16) ---
# Lấy từ config.linking.* patterns. Mặc định cho APA-like author-year + IEEE-like numeric.

_APA_AUTHOR_YEAR_RE = re.compile(
    r"\(\s*"
    r"(?P<author>[A-ZÀ-Ỹ][\wÀ-Ỹ\.\-]+(?:\s+(?:et\s+al\.|and\s+[A-ZÀ-Ỹ][\wÀ-Ỹ\.\-]+))?)"
    r",\s*"
    r"(?P<year>(?:19|20)\d{2})(?P<suffix>[a-z])?"
    r"\)"
)
_APA_NARRATIVE_RE = re.compile(
    r"(?P<author>[A-ZÀ-Ỹ][\wÀ-Ỹ\.\-]+(?:\s+(?:et\s+al\.|and\s+[A-ZÀ-Ỹ][\wÀ-Ỹ\.\-]+))?)"
    r"\s*\(\s*(?P<year>(?:19|20)\d{2})(?P<suffix>[a-z])?\s*\)"
)
_IEEE_NUMERIC_RE = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\]\)\,;]+")


class CitationLinker:
    """Bidirectional linker — APA-like + IEEE-like + ambiguous."""

    def __init__(self) -> None:
        s = get_settings()
        self.exclude_sections = set(s.linking.exclude_sections)
        self._duplicate_threshold = s.linking.duplicate_detection.title_year_author_similarity

    # -- public entry --

    def link(
        self,
        occurrences: list[CitationOccurrence],
        references: list[ReferenceEntry],
        style_profile: StyleProfile,
    ) -> LinkingResult:
        """Link occurrences ↔ references, trả LinkingResult.

        Args:
            occurrences: in-text citations đã parse (đã loại trừ references section).
            references: reference entries đã parse.
            style_profile: document-level style, dùng để chọn strategy
                + phát hiện STYLE_INCONSISTENT.

        Returns:
            LinkingResult với links, uncited, ambiguous, counts.
        """
        # 1. Index references cho lookup nhanh
        ref_by_author_year: dict[tuple[str, str], ReferenceEntry] = {}
        ref_by_year_suffix: dict[tuple[str, Optional[str]], list[ReferenceEntry]] = defaultdict(list)
        ref_by_numeric: dict[int, ReferenceEntry] = {}
        ref_by_doi: dict[str, ReferenceEntry] = {}
        refs_by_id: dict[str, ReferenceEntry] = {}

        for ref in references:
            refs_by_id[ref.reference_id] = ref
            if ref.doi:
                ref_by_doi[ref.doi.lower()] = ref
            if ref.year:
                key = (ref.year, ref.year_suffix)
                ref_by_year_suffix[key].append(ref)
            if ref.authors:
                last_name = self._canonical_author(ref.authors[0])
                if last_name:
                    ref_by_author_year[(last_name, ref.year or "")] = ref
            if 1 <= ref.order_index <= 9999:
                ref_by_numeric[ref.order_index] = ref

        # 2. Forward pass: in-text → reference
        links: list[CitationLink] = []
        matched_ref_ids: set[str] = set()
        ambiguous_occurrence_ids: list[str] = []

        for occ in occurrences:
            link = self._link_one(occ, refs_by_id, ref_by_author_year,
                                  ref_by_year_suffix, ref_by_numeric, ref_by_doi, style_profile)
            links.append(link)
            if link.status == CitationMappingStatus.AMBIGUOUS_MAPPING:
                ambiguous_occurrence_ids.append(occ.occurrence_id)
            elif link.reference_id is not None and link.status in (
                CitationMappingStatus.MATCHED,
                CitationMappingStatus.IN_TEXT_MISMATCH,
            ):
                matched_ref_ids.add(link.reference_id)

        # 3. Backward pass: reference → in-text
        uncited: list[str] = []
        for ref in references:
            if ref.reference_id not in matched_ref_ids:
                uncited.append(ref.reference_id)

        # 4. Counts by status
        counts: dict[str, int] = defaultdict(int)
        for link in links:
            counts[link.status.value] += 1
        # Uncited count = len(uncited), theo định nghĩa không phải link
        if uncited:
            counts[CitationMappingStatus.UNCITED_REFERENCE.value] = len(uncited)

        return LinkingResult(
            links=links,
            uncited_reference_ids=uncited,
            ambiguous_mapping_ids=ambiguous_occurrence_ids,
            counts_by_status=dict(counts),
        )

    # -- internals --

    def _link_one(
        self,
        occ: CitationOccurrence,
        refs_by_id: dict[str, ReferenceEntry],
        ref_by_author_year: dict[tuple[str, str], ReferenceEntry],
        ref_by_year_suffix: dict[tuple[str, Optional[str]], list[ReferenceEntry]],
        ref_by_numeric: dict[int, ReferenceEntry],
        ref_by_doi: dict[str, ReferenceEntry],
        style: StyleProfile,
    ) -> CitationLink:
        """Link 1 occurrence. Trả CitationLink với status phù hợp.

        Quyết định theo thứ tự ưu tiên:
        1. DOI exact → MATCHED (nếu tìm thấy) hoặc MISSING_REFERENCE.
        2. APA-like (nếu style chủ đạo cho phép hoặc không ambiguous).
        3. IEEE-like.
        4. AMBIGUOUS_MAPPING nếu ≥2 candidate ngang nhau.
        """
        # --- 1. DOI exact (ưu tiên cao nhất) ---
        if occ.doi:
            ref = ref_by_doi.get(occ.doi.lower())
            if ref:
                return CitationLink(
                    occurrence_id=occ.occurrence_id,
                    reference_id=ref.reference_id,
                    status=CitationMappingStatus.MATCHED,
                    confidence=0.95,
                    method="doi_exact",
                    evidence={"doi": occ.doi, "raw": occ.raw_text},
                    page=occ.page,
                    section=occ.section,
                )
            # DOI nằm trong occurrence nhưng không có ref khớp
            return CitationLink(
                occurrence_id=occ.occurrence_id,
                reference_id=None,
                status=CitationMappingStatus.MISSING_REFERENCE,
                confidence=0.85,
                method="doi_not_found",
                evidence={"doi": occ.doi, "raw": occ.raw_text},
                page=occ.page,
                section=occ.section,
            )

        # --- 2. APA-like author-year ---
        # Nếu style là IEEE-like thuần, có thể bỏ qua; nhưng để an toàn vẫn thử
        # trước (fallback). Logic STYLE_INCONSISTENT đánh dấu ở dưới.
        if occ.authors and occ.year:
            last_name = self._canonical_author(occ.authors[0])
            key = (last_name, occ.year)
            ref = ref_by_author_year.get(key)
            if ref:
                # Có thể có nhiều ref cùng (last_name, year) — kiểm tra suffix
                if occ.year_suffix and ref.year_suffix != occ.year_suffix:
                    # Suffix mismatch — có thể là 2024a vs 2024b
                    candidates = ref_by_year_suffix.get((occ.year, occ.year_suffix), [])
                    if candidates:
                        return CitationLink(
                            occurrence_id=occ.occurrence_id,
                            reference_id=candidates[0].reference_id,
                            status=CitationMappingStatus.MATCHED,
                            confidence=0.85,
                            method="author_year_suffix",
                            evidence={"author": occ.authors[0], "year": occ.year,
                                      "suffix": occ.year_suffix, "raw": occ.raw_text},
                            page=occ.page,
                            section=occ.section,
                        )
                    # Không tìm ref với suffix phù hợp → IN_TEXT_MISMATCH
                    return CitationLink(
                        occurrence_id=occ.occurrence_id,
                        reference_id=ref.reference_id,
                        status=CitationMappingStatus.IN_TEXT_MISMATCH,
                        confidence=0.7,
                        method="author_year_suffix_mismatch",
                        evidence={"author": occ.authors[0], "year": occ.year,
                                  "suffix": occ.year_suffix, "expected_suffix": ref.year_suffix},
                        page=occ.page,
                        section=occ.section,
                    )
                return CitationLink(
                    occurrence_id=occ.occurrence_id,
                    reference_id=ref.reference_id,
                    status=CitationMappingStatus.MATCHED,
                    confidence=0.9,
                    method="author_year",
                    evidence={"author": occ.authors[0], "year": occ.year, "raw": occ.raw_text},
                    page=occ.page,
                    section=occ.section,
                )
            # Không tìm ref cùng (author, year) → MISSING_REFERENCE
            return CitationLink(
                occurrence_id=occ.occurrence_id,
                reference_id=None,
                status=CitationMappingStatus.MISSING_REFERENCE,
                confidence=0.75,
                method="author_year_not_found",
                evidence={"author": occ.authors[0], "year": occ.year, "raw": occ.raw_text},
                page=occ.page,
                section=occ.section,
            )

        # --- 3. IEEE-like numeric ---
        if occ.numeric_indices:
            # Range [1-5] đã được expand thành [1,2,3,4,5] ở parse_occurrence
            if len(occ.numeric_indices) == 1:
                idx = occ.numeric_indices[0]
                ref = ref_by_numeric.get(idx)
                if ref:
                    return CitationLink(
                        occurrence_id=occ.occurrence_id,
                        reference_id=ref.reference_id,
                        status=CitationMappingStatus.MATCHED,
                        confidence=0.9,
                        method="numeric_index",
                        evidence={"index": idx, "raw": occ.raw_text},
                        page=occ.page,
                        section=occ.section,
                    )
                return CitationLink(
                    occurrence_id=occ.occurrence_id,
                    reference_id=None,
                    status=CitationMappingStatus.MISSING_REFERENCE,
                    confidence=0.8,
                    method="numeric_index_not_found",
                    evidence={"index": idx, "raw": occ.raw_text},
                    page=occ.page,
                    section=occ.section,
                )
            # Multi-index [1,3,5] hoặc [1-5] — tách thành nhiều link
            # TODO: CitationLinker hiện 1 occurrence → 1 link
            # → multi-index cần Link OCCURRENCE_COLLECTION; sẽ làm ở tuần 6–7
            found = [ref_by_numeric.get(i) for i in occ.numeric_indices]
            if all(found):
                # Tất cả matched → dùng candidate đầu làm canonical, evidence có list
                primary = next(r for r in found if r is not None)
                return CitationLink(
                    occurrence_id=occ.occurrence_id,
                    reference_id=primary.reference_id,
                    status=CitationMappingStatus.MATCHED,
                    confidence=0.85,
                    method="numeric_index_multi",
                    evidence={"indices": occ.numeric_indices, "raw": occ.raw_text},
                    page=occ.page,
                    section=occ.section,
                )
            missing = [i for i, r in zip(occ.numeric_indices, found) if r is None]
            return CitationLink(
                occurrence_id=occ.occurrence_id,
                reference_id=None,
                status=CitationMappingStatus.MISSING_REFERENCE,
                confidence=0.7,
                method="numeric_index_multi_partial",
                evidence={"missing_indices": missing, "raw": occ.raw_text},
                page=occ.page,
                section=occ.section,
            )

        # --- 4. Không parse được keys → AMBIGUOUS_MAPPING ---
        return CitationLink(
            occurrence_id=occ.occurrence_id,
            reference_id=None,
            status=CitationMappingStatus.AMBIGUOUS_MAPPING,
            confidence=0.3,
            method="no_keys",
            evidence={"raw": occ.raw_text},
            page=occ.page,
            section=occ.section,
        )

    # -- helpers --

    @staticmethod
    def _canonical_author(raw: str) -> str:
        """Chuẩn hoá last name để so khớp.

        "Smith, J." → "Smith"
        "Smith J." → "Smith"
        "van der Berg, J." → "van der Berg" (chỉ lấy phần trước dấu phẩy; sẽ
            cải thiện ở tuần 4–5 khi author parser có NER đầy đủ)
        """
        if not raw:
            return ""
        if "," in raw:
            return raw.split(",")[0].strip().lower()
        # Không có dấu phẩy → token cuối
        parts = raw.split()
        return parts[-1].strip().lower() if parts else ""

    # -- parsing helpers (entry points cho tuần 6–7) --

    @staticmethod
    def parse_occurrence(
        raw_text: str,
        page: int = 0,
        section: str = "",
        occurrence_id: str = "",
        context: str = "",
    ) -> CitationOccurrence:
        """Parse 1 in-text citation thành CitationOccurrence.

        Đây là scaffold — sẽ thay thế bằng CitationExtractor integration
        ở tuần 6–7. Hiện tại nhận diện 3 dạng:
        - APA-like parenthetical: (Smith, 2020) / (Smith et al., 2020a)
        - APA-like narrative: Smith (2020) / Smith et al. (2020)
        - IEEE-like numeric: [12] / [1,2,3] / [1-5]
        """
        occ = CitationOccurrence(
            occurrence_id=occurrence_id or f"occ-{hash(raw_text) & 0xFFFF:04x}",
            raw_text=raw_text,
            page=page,
            section=section,
            context=context,
        )

        # DOI (ưu tiên parse đầu vì dễ nhất)
        doi_m = _DOI_RE.search(raw_text)
        if doi_m:
            occ.doi = doi_m.group(0).rstrip(".")

        # Numeric IEEE
        num_m = _IEEE_NUMERIC_RE.search(raw_text)
        if num_m:
            indices = CitationLinker._expand_numeric(num_m.group(1))
            occ.numeric_indices = indices
            if len(indices) == 1:
                occ.numeric_index = indices[0]
            occ.raw_style_hint = "IEEE"
            return occ

        # APA parenthetical
        apa_p = _APA_AUTHOR_YEAR_RE.search(raw_text)
        if apa_p:
            occ.authors = [apa_p.group("author").strip()]
            occ.year = apa_p.group("year")
            occ.year_suffix = apa_p.group("suffix") or None
            occ.raw_style_hint = "APA"
            return occ

        # APA narrative
        apa_n = _APA_NARRATIVE_RE.search(raw_text)
        if apa_n:
            occ.authors = [apa_n.group("author").strip()]
            occ.year = apa_n.group("year")
            occ.year_suffix = apa_n.group("suffix") or None
            occ.raw_style_hint = "APA"
            return occ

        # Không parse được
        logger.debug("Could not parse occurrence: %s", raw_text)
        return occ

    @staticmethod
    def _expand_numeric(spec: str) -> list[int]:
        """Mở rộng '1,2,3' hoặc '1-5' thành [1,2,3,4,5]."""
        indices: list[int] = []
        for part in spec.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start_s, end_s = part.split("-", 1)
                    start, end = int(start_s.strip()), int(end_s.strip())
                    if start <= end:
                        indices.extend(range(start, end + 1))
                    else:
                        indices.extend(range(end, start + 1))
                except ValueError:
                    continue
            else:
                try:
                    indices.append(int(part))
                except ValueError:
                    continue
        return sorted(set(indices))

    @staticmethod
    def parse_reference(
        raw_text: str,
        order_index: int,
        page: int = 0,
        reference_id: str = "",
    ) -> ReferenceEntry:
        """Scaffold parser — sẽ thay bằng ReferenceListParser integration ở tuần 6.

        Hiện tại chỉ trích DOI + year + author heuristic (split dấu phẩy).
        Stub này đủ để test link logic.
        """
        ref = ReferenceEntry(
            reference_id=reference_id or f"ref-{order_index:04d}",
            raw_text=raw_text,
            order_index=order_index,
            page=page,
        )

        doi_m = _DOI_RE.search(raw_text)
        if doi_m:
            ref.doi = doi_m.group(0).rstrip(".")

        # Year + suffix (4 chu số + optional a/b)
        year_m = re.search(r"\b((?:19|20)\d{2})([a-z])\b", raw_text)
        if year_m:
            ref.year = year_m.group(1)
            ref.year_suffix = year_m.group(2)
        else:
            year_m = re.search(r"\b((?:19|20)\d{2})\b", raw_text)
            if year_m:
                ref.year = year_m.group(1)

        # Author block: lấy phần trước năm đầu tiên (APA pattern)
        if ref.year:
            m = re.match(r"^(?P<auth>.+?)\s*\(\s*" + re.escape(ref.year), raw_text)
            if m:
                ref.authors = [m.group("auth").strip()]

        return ref
