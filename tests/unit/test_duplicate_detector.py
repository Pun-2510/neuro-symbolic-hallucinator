"""Unit tests cho linking/duplicate_detector.py — DuplicateDetector (v1.2 §3.5)."""

from __future__ import annotations

import pytest

from integrity_checker.linking import DuplicateDetector, DuplicateGroup
from integrity_checker.models.citation import Citation, CitationType


def cit(raw, doi=None, title_norm=None, year=None, authors=None):
    return Citation(
        raw_text=raw,
        citation_type=CitationType.REFERENCE_LIST,
        authors=authors or [],
        year=year,
        title_normalized=title_norm,
        doi=doi,
    )


class TestDOIExactDuplicate:
    def test_same_doi_is_duplicate(self):
        c1 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        c2 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 1
        assert len(groups[0].citations) == 2
        assert groups[0].score == 1.0
        assert "doi" in groups[0].reason.lower()

    def test_different_doi_not_duplicate(self):
        c1 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        c2 = cit("Doe (2021). Title B.", doi="10.9999/xyz")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 0

    def test_doi_case_insensitive(self):
        c1 = cit("Smith (2020). Title A.", doi="10.1234/ABC")
        c2 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 1

    def test_three_same_doi(self):
        c1 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        c2 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        c3 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        groups = DuplicateDetector().detect([c1, c2, c3])
        assert len(groups) == 1
        assert len(groups[0].citations) == 3


class TestArxivExactDuplicate:
    def test_same_arxiv_id(self):
        c1 = cit("Smith. arXiv:2103.12345", doi="arXiv:2103.12345")
        c2 = cit("Smith. arXiv:2103.12345", doi="arXiv:2103.12345")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 1

    def test_different_arxiv_not_duplicate(self):
        c1 = cit("Smith. arXiv:2103.12345", doi="arXiv:2103.12345")
        c2 = cit("Doe. arXiv:2104.54321", doi="arXiv:2104.54321")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 0


class TestTitleAuthorYearFallback:
    def test_same_title_and_year(self):
        c1 = cit("Smith (2020). Deep learning applications.",
                 title_norm="deep learning applications", year="2020")
        c2 = cit("Smith (2020). Deep learning applications.",
                 title_norm="deep learning applications", year="2020")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 1

    def test_different_title_not_duplicate(self):
        c1 = cit("Smith (2020). Deep learning applications.",
                 title_norm="deep learning applications", year="2020")
        c2 = cit("Smith (2020). Machine learning overview.",
                 title_norm="machine learning overview", year="2020")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 0

    def test_threshold_boundary(self):
        """At threshold exactly, should be included."""
        c1 = cit("Smith (2020). A study of X in Y.",
                 title_norm="a study of x in y", year="2020",
                 authors=["Smith"])
        c2 = cit("Smith (2020). A study of X in Y.",
                 title_norm="a study of x in y", year="2020",
                 authors=["Smith"])
        detector = DuplicateDetector(title_year_author_similarity=0.92)
        groups = detector.detect([c1, c2])
        assert len(groups) == 1


class TestDuplicateGroupProperties:
    def test_representative_is_first(self):
        c1 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        c2 = cit("Smith (2020). Title A.", doi="10.1234/abc")
        groups = DuplicateDetector().detect([c1, c2])
        assert groups[0].representative is c1

    def test_duplicate_count(self):
        c1 = cit("A.", doi="10.1/a")
        c2 = cit("A.", doi="10.1/a")
        c3 = cit("A.", doi="10.1/a")
        groups = DuplicateDetector().detect([c1, c2, c3])
        assert groups[0].duplicate_count == 2


class TestEdgeCases:
    def test_single_entry(self):
        groups = DuplicateDetector().detect([cit("Smith (2020). Title A.", doi="10.1234/abc")])
        assert len(groups) == 0

    def test_empty_list(self):
        groups = DuplicateDetector().detect([])
        assert len(groups) == 0

    def test_no_doi_no_arxiv_no_title(self):
        c1 = cit("Smith (2020). Title A.")
        c2 = cit("Smith (2020). Title A.")
        groups = DuplicateDetector().detect([c1, c2])
        # Without title_normalized or identifiers, similarity = 0
        assert len(groups) == 0

    def test_doi_priority_over_title(self):
        """Exact DOI takes priority over title similarity."""
        c1 = cit("Smith (2020). Title A.", doi="10.1234/abc",
                 title_norm="deep learning")
        c2 = cit("Smith (2020). Deep learning.", doi="10.1234/abc",
                 title_norm="deep learning")
        groups = DuplicateDetector().detect([c1, c2])
        assert len(groups) == 1
        assert groups[0].score == 1.0  # DOI exact = 1.0
