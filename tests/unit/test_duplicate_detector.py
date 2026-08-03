"""Unit tests cho ``DuplicateDetector`` — DOI exact + title-author-year fuzzy (v1.2 §3.5).

Covers:
    - DOI exact match (priority)
    - arXiv ID exact match
    - title + first author + year similarity fallback (threshold từ config)
    - Edge cases: no DOI, no title, different year, different author

Tổng: ≥6 tests (task #20 yêu cầu).

Reference:
    v1.2 §3.5 (đối chiếu hai chiều, duplicate detection)
    config.linking.duplicate_detection.title_year_author_similarity
"""

from __future__ import annotations

import pytest

from integrity_checker.linking.citation_linker import CitationLinker
from integrity_checker.linking.duplicate_detector import DuplicateDetector
from integrity_checker.linking.statuses import ReferenceEntry


# ---------- Helpers ----------

def _mkref(raw: str, idx: int, rid: str) -> ReferenceEntry:
    """Helper tạo ReferenceEntry qua CitationLinker.parse_reference."""
    return CitationLinker.parse_reference(raw, order_index=idx, reference_id=rid)


def _mkref_full(
    rid: str,
    idx: int,
    *,
    authors: list[str] | None = None,
    year: str | None = None,
    title: str | None = None,
    title_normalized: str | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
) -> ReferenceEntry:
    """Tạo ReferenceEntry với fields tùy ý — dùng cho test fuzzy/title."""
    return ReferenceEntry(
        reference_id=rid,
        raw_text="...",
        order_index=idx,
        page=8,
        authors=authors or [],
        year=year,
        title=title,
        title_normalized=title_normalized,
        doi=doi,
        arxiv_id=arxiv_id,
    )


# ---------- Test 1: DOI exact match (priority) ----------


class TestDOIExact:
    def test_two_refs_same_doi(self):
        """2 ref cùng DOI → 1 group, method=doi_exact, similarity=1.0."""
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

    def test_three_refs_same_doi(self):
        """3 ref cùng DOI → 1 group với 2 duplicates."""
        refs = [
            _mkref(
                "Smith, J. (2020). A. DOI: 10.1234/abc.001",
                1, "ref-0001"
            ),
            _mkref(
                "Smith, J. (2020). A. DOI: 10.1234/abc.001",
                2, "ref-0002"
            ),
            _mkref(
                "Smith, J. (2020). A. DOI: 10.1234/abc.001",
                3, "ref-0003"
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert len(groups) == 1
        assert len(groups[0].duplicate_ids) == 2
        assert "ref-0002" in groups[0].duplicate_ids
        assert "ref-0003" in groups[0].duplicate_ids


# ---------- Test 2: DOI case-insensitive + URL normalization ----------


class TestDOINormalization:
    def test_doi_normalized_to_lowercase(self):
        """DOI khác case → vẫn group (normalized to lowercase)."""
        refs = [
            _mkref(
                "Smith, J. (2020). A. DOI: 10.1234/ABC.001",
                1, "ref-0001"
            ),
            _mkref(
                "Smith, J. (2020). A. DOI: 10.1234/abc.001",
                2, "ref-0002"
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert len(groups) == 1
        assert groups[0].match_method == "doi_exact"


# ---------- Test 3: arXiv ID exact match ----------


class TestArxivExact:
    def test_two_refs_same_arxiv_id(self):
        """2 ref cùng arXiv ID → 1 group, method=arxiv_exact."""
        refs = [
            _mkref_full("ref-0001", 1, authors=["Smith, J."], year="2020",
                        arxiv_id="arXiv:2005.12345"),
            _mkref_full("ref-0002", 2, authors=["Smith, J."], year="2020",
                        arxiv_id="arXiv:2005.12345"),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert len(groups) == 1
        assert groups[0].match_method == "arxiv_exact"
        assert groups[0].similarity == 1.0


# ---------- Test 4: Title + author + year fuzzy fallback ----------


class TestFuzzyFallback:
    def test_fuzzy_duplicate_no_doi(self):
        """Không có DOI, cùng author+year, title giống → fuzzy duplicate."""
        refs = [
            _mkref_full(
                "ref-0001", 1,
                authors=["Smith, J."], year="2020",
                title="A study of X in modern systems",
                title_normalized="a study of x in modern systems",
            ),
            _mkref_full(
                "ref-0002", 2,
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
        """Cùng author, khác year → không duplicate."""
        refs = [
            _mkref_full(
                "ref-0001", 1,
                authors=["Smith, J."], year="2020",
                title="A study of X",
                title_normalized="a study of x",
            ),
            _mkref_full(
                "ref-0002", 2,
                authors=["Smith, J."], year="2021",
                title="A study of X",
                title_normalized="a study of x",
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert groups == []

    def test_fuzzy_no_duplicate_when_different_author(self):
        """Khác author, cùng year → không duplicate."""
        refs = [
            _mkref_full(
                "ref-0001", 1,
                authors=["Smith, J."], year="2020",
                title="A study of X",
                title_normalized="a study of x",
            ),
            _mkref_full(
                "ref-0002", 2,
                authors=["Doe, A."], year="2020",
                title="A study of X",
                title_normalized="a study of x",
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert groups == []


# ---------- Test 5: Mix DOI + Title (priority) ----------


class TestPriority:
    def test_doi_priority_over_fuzzy(self):
        """2 ref cùng DOI nhưng title KHÁC → vẫn group (DOI priority)."""
        refs = [
            _mkref_full(
                "ref-0001", 1,
                authors=["Smith, J."], year="2020",
                title="Original Title",
                title_normalized="original title",
                doi="10.1234/abc.001",
            ),
            _mkref_full(
                "ref-0002", 2,
                authors=["Smith, J."], year="2020",
                title="Different Title",
                title_normalized="different title",
                doi="10.1234/abc.001",
            ),
        ]
        groups = DuplicateDetector().find_duplicates(refs)
        assert len(groups) == 1
        assert groups[0].match_method == "doi_exact"


# ---------- Test 6: No duplicates ----------


class TestNoDuplicates:
    def test_unique_refs_no_groups(self):
        """Refs khác DOI, khác author — không có group."""
        refs = [
            _mkref(
                "Smith, J. (2020). A study of X. Journal A. DOI: 10.1234/abc.001",
                1, "ref-0001"
            ),
            _mkref(
                "Doe, A. (2021). Other. Journal B. DOI: 10.5678/xyz.999",
                2, "ref-0002"
            ),
        ]
        assert DuplicateDetector().find_duplicates(refs) == []

    def test_empty_input(self):
        """Inputs rỗng → không groups."""
        assert DuplicateDetector().find_duplicates([]) == []
