"""Unit tests cho ``linking/statuses.py`` — CitationMappingStatus enum + CitationLink.

Mapping chuẩn (v1.2 §3.2.2): 7 trạng thái tách khỏi ValidationLabel.

Reference:
    v1.2 §3.2.2 (Hai lớp nhãn — Integrity vs Source)
    v1.2 §3.5 (Bidirectional linking — 7 trạng thái)
    task #20 tuần 8 (scaffold linking/ package)
"""

from __future__ import annotations

import pytest

from integrity_checker.linking.statuses import (
    CitationLink,
    CitationMappingStatus,
    CitationOccurrence,
    LinkingResult,
    ReferenceEntry,
    StyleProfile,
)


# ---------- Test CitationMappingStatus enum ----------


class TestEnumStructure:
    """Test enum có đúng 7 trạng thái + enum identity."""

    def test_seven_distinct_statuses(self):
        """BẮT BUỘC đúng 7 status theo v1.2 §3.2.2."""
        assert len(CitationMappingStatus) == 7

    def test_required_statuses_present(self):
        required = {
            "matched",
            "missing_reference",
            "uncited_reference",
            "in_text_mismatch",
            "duplicate_reference",
            "ambiguous_mapping",
            "style_inconsistent",
        }
        actual = {s.value for s in CitationMappingStatus}
        assert required == actual

    def test_status_string_values_lowercase(self):
        """Bắt buộc lowercase để serialize/UI (xem docstring enum)."""
        for status in CitationMappingStatus:
            assert status.value == status.value.lower()


# ---------- Test mapping chuẩn (color + is_integrity_issue) ----------


class TestColorMapping:
    """Mỗi status phải có màu badge (hex 7-char) theo bảng màu riêng."""

    def test_matched_green(self):
        assert CitationMappingStatus.MATCHED.color == "#16a34a"

    def test_missing_reference_red(self):
        assert CitationMappingStatus.MISSING_REFERENCE.color == "#dc2626"

    def test_uncited_reference_orange(self):
        assert CitationMappingStatus.UNCITED_REFERENCE.color == "#ea580c"

    def test_in_text_mismatch_yellow(self):
        assert CitationMappingStatus.IN_TEXT_MISMATCH.color == "#ca8a04"

    def test_duplicate_reference_purple(self):
        assert CitationMappingStatus.DUPLICATE_REFERENCE.color == "#9333ea"

    def test_ambiguous_mapping_grey(self):
        assert CitationMappingStatus.AMBIGUOUS_MAPPING.color == "#6b7280"

    def test_style_inconsistent_cyan(self):
        assert CitationMappingStatus.STYLE_INCONSISTENT.color == "#0891b2"

    @pytest.mark.parametrize("status", list(CitationMappingStatus))
    def test_color_format_valid_hex(self, status):
        """Mọi status color phải là hex 7-char bắt đầu #."""
        assert status.color.startswith("#")
        assert len(status.color) == 7


class TestIntegrityIssueFlag:
    """is_integrity_issue: True nếu status BIỂU THỊ vấn đề integrity."""

    def test_matched_is_not_issue(self):
        assert CitationMappingStatus.MATCHED.is_integrity_issue is False

    @pytest.mark.parametrize("status", [
        CitationMappingStatus.MISSING_REFERENCE,
        CitationMappingStatus.UNCITED_REFERENCE,
        CitationMappingStatus.IN_TEXT_MISMATCH,
        CitationMappingStatus.DUPLICATE_REFERENCE,
        CitationMappingStatus.AMBIGUOUS_MAPPING,
        CitationMappingStatus.STYLE_INCONSISTENT,
    ])
    def test_other_statuses_are_issues(self, status):
        assert status.is_integrity_issue is True


# ---------- Test CitationLink dataclass ----------


class TestCitationLinkDataclass:
    """CitationLink: 1 quan hệ occurrence ↔ reference."""

    def test_default_construction(self):
        link = CitationLink(
            occurrence_id="occ-0001",
            reference_id="ref-0007",
            status=CitationMappingStatus.MATCHED,
            confidence=0.95,
        )
        assert link.occurrence_id == "occ-0001"
        assert link.reference_id == "ref-0007"
        assert link.status == CitationMappingStatus.MATCHED
        assert link.confidence == 0.95
        assert link.method == "unknown"
        assert link.evidence == {}
        assert link.page == 0
        assert link.section == ""

    def test_missing_reference_has_none_reference_id(self):
        """MISSING_REFERENCE phải có reference_id = None."""
        link = CitationLink(
            occurrence_id="occ-x",
            reference_id=None,
            status=CitationMappingStatus.MISSING_REFERENCE,
            confidence=0.7,
        )
        assert link.reference_id is None
        assert link.status.is_integrity_issue is True

    def test_evidence_dict_mutable(self):
        """Evidence dict phải mutable để gắn bằng chứng."""
        link = CitationLink(
            occurrence_id="occ-1",
            reference_id="ref-1",
            status=CitationMappingStatus.MATCHED,
            confidence=0.9,
        )
        link.evidence["author"] = "Smith"
        link.evidence["year"] = "2020"
        assert link.evidence["author"] == "Smith"
        assert link.evidence["year"] == "2020"

    def test_method_field_stored(self):
        """method là free-form str để dùng cho evidence/audit."""
        link = CitationLink(
            occurrence_id="occ-1",
            reference_id="ref-1",
            status=CitationMappingStatus.MATCHED,
            confidence=0.95,
            method="doi_exact",
        )
        assert link.method == "doi_exact"

    def test_section_and_page_defaults(self):
        link = CitationLink(
            occurrence_id="occ-1",
            reference_id="ref-1",
            status=CitationMappingStatus.MATCHED,
            confidence=0.9,
            page=5,
            section="introduction",
        )
        assert link.page == 5
        assert link.section == "introduction"


# ---------- Test CitationOccurrence & ReferenceEntry wrappers ----------


class TestWrappers:
    """CitationOccurrence & ReferenceEntry wrappers cho extractor output."""

    def test_occurrence_defaults(self):
        occ = CitationOccurrence(
            occurrence_id="occ-1",
            raw_text="(Smith, 2020)",
            page=1,
        )
        assert occ.authors == []
        assert occ.year is None
        assert occ.numeric_indices == []
        assert occ.doi is None

    def test_reference_entry_defaults(self):
        ref = ReferenceEntry(
            reference_id="ref-1",
            raw_text="...",
            order_index=1,
        )
        assert ref.year is None
        assert ref.title is None
        assert ref.doi is None


# ---------- Test LinkingResult aggregate ----------


class TestLinkingResult:
    """LinkingResult aggregate output của CitationLinker.link()."""

    def test_empty_construction(self):
        result = LinkingResult()
        assert result.links == []
        assert result.uncited_reference_ids == []
        assert result.duplicate_reference_ids == []
        assert result.ambiguous_mapping_ids == []
        assert result.counts_by_status == {}

    def test_has_integrity_issues_true(self):
        """Có link non-MATCHED non-STYLE_INCONSISTENT → True."""
        result = LinkingResult(
            links=[
                CitationLink(
                    occurrence_id="occ-1",
                    reference_id=None,
                    status=CitationMappingStatus.MISSING_REFERENCE,
                    confidence=0.7,
                )
            ]
        )
        assert result.has_integrity_issues() is True

    def test_has_integrity_issues_false_for_matched_only(self):
        """Có link MATCHED only → False."""
        result = LinkingResult(
            links=[
                CitationLink(
                    occurrence_id="occ-1",
                    reference_id="ref-1",
                    status=CitationMappingStatus.MATCHED,
                    confidence=0.9,
                )
            ]
        )
        assert result.has_integrity_issues() is False
