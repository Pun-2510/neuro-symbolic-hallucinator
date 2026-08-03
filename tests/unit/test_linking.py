"""Unit tests cho linking/ (v1.2 §3.5).

Test các flow:
- CitationMappingStatus enum (7 trạng thái, color, is_integrity_issue).
- CitationLinker.parse_occurrence 3 dạng: APA parenthetical / IEEE numeric / APA narrative.
- CitationLinker.link end-to-end: MATCHED / MISSING_REFERENCE / UNCITED_REFERENCE / AMBIGUOUS_MAPPING.
- DuplicateDetector: DOI exact + title fuzzy fallback.
"""

from __future__ import annotations

import pytest

from integrity_checker.linking import (
    CitationLinker,
    CitationMappingStatus,
    DuplicateDetector,
)
from integrity_checker.linking.statuses import (
    CitationOccurrence,
    LinkingResult,
    ReferenceEntry,
    StyleProfile,
)


# ---------- Statuses ----------


class TestCitationMappingStatus:
    def test_seven_statuses(self):
        assert len(CitationMappingStatus) == 7

    @pytest.mark.parametrize("status", [
        CitationMappingStatus.MATCHED,
        CitationMappingStatus.MISSING_REFERENCE,
        CitationMappingStatus.UNCITED_REFERENCE,
        CitationMappingStatus.IN_TEXT_MISMATCH,
        CitationMappingStatus.DUPLICATE_REFERENCE,
        CitationMappingStatus.AMBIGUOUS_MAPPING,
        CitationMappingStatus.STYLE_INCONSISTENT,
    ])
    def test_status_has_color(self, status):
        assert status.color.startswith("#")
        assert len(status.color) == 7

    def test_matched_is_not_integrity_issue(self):
        assert CitationMappingStatus.MATCHED.is_integrity_issue is False

    @pytest.mark.parametrize("status", [
        CitationMappingStatus.MISSING_REFERENCE,
        CitationMappingStatus.UNCITED_REFERENCE,
        CitationMappingStatus.IN_TEXT_MISMATCH,
        CitationMappingStatus.DUPLICATE_REFERENCE,
        CitationMappingStatus.AMBIGUOUS_MAPPING,
        CitationMappingStatus.STYLE_INCONSISTENT,
    ])
    def test_other_statuses_are_integrity_issues(self, status):
        assert status.is_integrity_issue is True


# ---------- Parser ----------


class TestParseOccurrence:
    def test_apa_parenthetical(self):
        occ = CitationLinker.parse_occurrence("(Smith, 2020)", page=1)
        assert occ.authors == ["Smith"]
        assert occ.year == "2020"
        assert occ.year_suffix is None
        assert occ.raw_style_hint == "APA"
        assert occ.numeric_indices == []

    def test_apa_with_suffix(self):
        occ = CitationLinker.parse_occurrence("(Smith, 2024a)", page=1)
        assert occ.authors == ["Smith"]
        assert occ.year == "2024"
        assert occ.year_suffix == "a"

    def test_apa_narrative(self):
        occ = CitationLinker.parse_occurrence("Smith et al. (2020)", page=1)
        assert occ.authors == ["Smith et al."]
        assert occ.year == "2020"
        assert occ.raw_style_hint == "APA"

    def test_ieee_numeric_single(self):
        occ = CitationLinker.parse_occurrence("[12]", page=1)
        assert occ.numeric_indices == [12]
        assert occ.numeric_index == 12
        assert occ.raw_style_hint == "IEEE"

    def test_ieee_numeric_multi(self):
        occ = CitationLinker.parse_occurrence("[1,2,3]", page=1)
        assert occ.numeric_indices == [1, 2, 3]

    def test_ieee_numeric_range(self):
        occ = CitationLinker.parse_occurrence("[1-5]", page=1)
        assert occ.numeric_indices == [1, 2, 3, 4, 5]

    def test_ieee_numeric_mixed(self):
        occ = CitationLinker.parse_occurrence("[1,3,5-7]", page=1)
        assert occ.numeric_indices == [1, 3, 5, 6, 7]

    def test_unparseable_returns_ambiguous(self):
        occ = CitationLinker.parse_occurrence("??", page=1)
        assert occ.authors == []
        assert occ.year is None
        assert occ.numeric_indices == []

    def test_doi_extracted(self):
        occ = CitationLinker.parse_occurrence(
            "see https://doi.org/10.1234/abc.001 for details", page=1
        )
        assert occ.doi == "10.1234/abc.001"


# ---------- Linker ----------


def _mkref(raw: str, idx: int, rid: str) -> ReferenceEntry:
    return CitationLinker.parse_reference(raw, order_index=idx, reference_id=rid, page=8)


class TestCitationLinker:
    def test_matched_apa(self):
        refs = [_mkref("Smith, J. (2020). A study of X. Journal A.", 1, "ref-0001")]
        occs = [CitationLinker.parse_occurrence("(Smith, 2020)", page=1, occurrence_id="occ-1")]
        style = StyleProfile(style="APA-like", confidence=0.9, apa_count=1)

        result = CitationLinker().link(occs, refs, style)

        assert len(result.links) == 1
        assert result.links[0].status == CitationMappingStatus.MATCHED
        assert result.links[0].reference_id == "ref-0001"
        assert result.links[0].method == "author_year"
        assert result.counts_by_status["matched"] == 1

    def test_missing_reference(self):
        refs = [_mkref("Smith, J. (2020). A study of X. Journal A.", 1, "ref-0001")]
        occs = [CitationLinker.parse_occurrence("(Unknown, 2099)", page=1, occurrence_id="occ-1")]
        style = StyleProfile(style="APA-like", confidence=0.9)

        result = CitationLinker().link(occs, refs, style)

        assert result.links[0].status == CitationMappingStatus.MISSING_REFERENCE
        assert result.links[0].reference_id is None

    def test_uncited_reference(self):
        refs = [
            _mkref("Smith, J. (2020). A study of X. Journal A.", 1, "ref-0001"),
            _mkref("Doe, A. (2021). Other. Journal B.", 2, "ref-0002"),
        ]
        occs = [CitationLinker.parse_occurrence("(Smith, 2020)", page=1, occurrence_id="occ-1")]
        style = StyleProfile(style="APA-like", confidence=0.9)

        result = CitationLinker().link(occs, refs, style)

        assert "ref-0002" in result.uncited_reference_ids
        assert "ref-0001" not in result.uncited_reference_ids

    def test_ambiguous_mapping_when_no_keys(self):
        refs = [_mkref("Smith, J. (2020). A study of X. Journal A.", 1, "ref-0001")]
        occs = [CitationOccurrence(occurrence_id="occ-1", raw_text="??", page=1)]
        style = StyleProfile(style="APA-like", confidence=0.9)

        result = CitationLinker().link(occs, refs, style)

        assert result.links[0].status == CitationMappingStatus.AMBIGUOUS_MAPPING
        assert "occ-1" in result.ambiguous_mapping_ids

    def test_matched_ieee_numeric(self):
        refs = [
            _mkref("Smith, J. (2020). A study of X. Journal A.", 1, "ref-0001"),
            _mkref("Doe, A. (2021). Other. Journal B.", 2, "ref-0002"),
        ]
        occs = [CitationLinker.parse_occurrence("[2]", page=1, occurrence_id="occ-1")]
        style = StyleProfile(style="IEEE-like", confidence=0.9, numeric_count=1)

        result = CitationLinker().link(occs, refs, style)

        assert result.links[0].status == CitationMappingStatus.MATCHED
        assert result.links[0].reference_id == "ref-0002"
        assert result.links[0].method == "numeric_index"

    def test_doi_exact_match(self):
        refs = [
            _mkref(
                "Smith, J. (2020). A study of X. Journal A, 10. DOI: 10.1234/abc.001",
                1, "ref-0001"
            ),
        ]
        # Occurrence có DOI trực tiếp
        occ = CitationLinker.parse_occurrence(
            "see https://doi.org/10.1234/abc.001", page=1, occurrence_id="occ-1"
        )
        style = StyleProfile(style="APA-like", confidence=0.9)

        result = CitationLinker().link([occ], refs, style)

        assert result.links[0].status == CitationMappingStatus.MATCHED
        assert result.links[0].reference_id == "ref-0001"
        assert result.links[0].method == "doi_exact"

    def test_in_text_mismatch_year_suffix(self):
        # Occurrence nói 2024a, ref chỉ có 2024
        refs = [_mkref("Smith, J. (2024). A study of X. Journal A.", 1, "ref-0001")]
        occs = [CitationLinker.parse_occurrence("(Smith, 2024a)", page=1, occurrence_id="occ-1")]
        style = StyleProfile(style="APA-like", confidence=0.9)

        result = CitationLinker().link(occs, refs, style)

        assert result.links[0].status == CitationMappingStatus.IN_TEXT_MISMATCH
        # evidence có author + year + suffix + expected_suffix
        ev = result.links[0].evidence
        assert ev.get("year") == "2024"
        assert ev.get("suffix") == "a"
        assert ev.get("expected_suffix") is None  # ref chỉ có 2024, không có suffix
        assert result.links[0].method == "author_year_suffix_mismatch"

    def test_result_counts(self):
        refs = [
            _mkref("Smith, J. (2020). A study of X. Journal A.", 1, "ref-0001"),
            _mkref("Doe, A. (2021). Other. Journal B.", 2, "ref-0002"),
        ]
        occs = [
            CitationLinker.parse_occurrence("(Smith, 2020)", page=1, occurrence_id="occ-1"),
            CitationLinker.parse_occurrence("(Unknown, 2099)", page=2, occurrence_id="occ-2"),
            CitationOccurrence(occurrence_id="occ-3", raw_text="??", page=3),
        ]
        style = StyleProfile(style="APA-like", confidence=0.9)

        result = CitationLinker().link(occs, refs, style)

        # occ-1: matched (Smith 2020 → ref-0001)
        # occ-2: missing_reference (Unknown 2099)
        # occ-3: ambiguous_mapping
        # ref-0002: uncited
        assert result.counts_by_status["matched"] == 1
        assert result.counts_by_status["missing_reference"] == 1
        assert result.counts_by_status["ambiguous_mapping"] == 1
        assert result.counts_by_status["uncited_reference"] == 1
        assert result.has_integrity_issues() is True


# ---------- DuplicateDetector ----------


class TestDuplicateDetector:
    def test_doi_exact_duplicate(self):
        refs = [
            _mkref(
                "Smith, J. (2020). A study of X. Journal A. DOI: 10.1234/abc.001",
                1, "ref-0001"
            ),
            _mkref(
                "Smith, J. (2020). A study of X. Journal A. DOI: 10.1234/abc.001",
                2, "ref-0006"
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert len(groups) == 1
        assert groups[0].match_method == "doi_exact"
        assert groups[0].canonical_id == "ref-0001"
        assert groups[0].duplicate_ids == ["ref-0006"]
        assert groups[0].similarity == 1.0

    def test_no_duplicates_unique_doi(self):
        refs = [
            _mkref("Smith, J. (2020). A study of X. Journal A. DOI: 10.1234/abc.001", 1, "ref-0001"),
            _mkref("Doe, A. (2021). Other. Journal B. DOI: 10.5678/xyz.999", 2, "ref-0002"),
        ]
        assert DuplicateDetector().find_duplicates(refs) == []

    def test_fuzzy_duplicate_no_doi(self):
        # Cùng (author, year), title gần giống — không có DOI.
        # Note: parse_reference scaffold chưa trích title; dùng ReferenceEntry
        # constructor trực tiếp để có title cho fuzzy matching.
        refs = [
            ReferenceEntry(
                reference_id="ref-0001", raw_text="...", order_index=1,
                page=8,
                authors=["Smith, J."], year="2020",
                title="A study of X in modern systems",
                title_normalized="a study of x in modern systems",
            ),
            ReferenceEntry(
                reference_id="ref-0002", raw_text="...", order_index=2,
                page=8,
                authors=["Smith, J."], year="2020",
                title="A study of X in modern systems",
                title_normalized="a study of x in modern systems",
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert len(groups) == 1
        assert groups[0].match_method == "title_author_year_fuzzy"
        assert groups[0].similarity >= 0.92

    def test_fuzzy_no_duplicate_when_different_year(self):
        # Cùng author nhưng khác year — không phải duplicate
        refs = [
            _mkref("Smith, J. (2020). Same title. Journal A.", 1, "ref-0001"),
            _mkref("Smith, J. (2021). Same title. Journal B.", 2, "ref-0002"),
        ]
        assert DuplicateDetector().find_duplicates(refs) == []
