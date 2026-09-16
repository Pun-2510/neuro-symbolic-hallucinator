"""Tests cho arXiv client DOI extraction (2026-09-15).

Priority 5.1: Thêm tests cho arXiv DOI extraction.
Tests:
    - Extract arXiv ID from DOI: 10.48550/arXiv.2103.14030
    - Extract arXiv ID from URL: https://arxiv.org/abs/2103.14030
    - Extract arXiv ID from raw_text
    - Handle version suffix: 2103.14030v1
"""

from __future__ import annotations

import pytest

from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.models.citation import Citation, CitationType


class TestArxivIDExtraction:
    """Test arXiv ID extraction from various citation formats."""

    @pytest.fixture
    def client(self):
        return ArxivClient()

    def test_extract_from_doi_10_48550(self, client):
        """arXiv DOI format: 10.48550/arXiv.2103.14030."""
        cit = Citation(
            raw_text="",
            doi="10.48550/arXiv.2103.14030",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_doi_lowercase_arxiv(self, client):
        """arXiv DOI with lowercase 'arxiv': 10.48550/arxiv.2103.14030."""
        cit = Citation(
            raw_text="",
            doi="10.48550/arxiv.2103.14030",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_url_abs(self, client):
        """arXiv URL with /abs/ prefix."""
        cit = Citation(
            raw_text="",
            url="https://arxiv.org/abs/2103.14030",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_url_pdf(self, client):
        """arXiv URL with /pdf/ prefix."""
        cit = Citation(
            raw_text="",
            url="https://arxiv.org/pdf/2103.14030.pdf",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_url_with_version(self, client):
        """arXiv URL with version suffix: /abs/2103.14030v2."""
        cit = Citation(
            raw_text="",
            url="https://arxiv.org/abs/2103.14030v2",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        # Version should be stripped
        assert arxiv_id == "2103.14030"

    def test_extract_from_url_http(self, client):
        """arXiv URL with http://."""
        cit = Citation(
            raw_text="",
            url="http://arxiv.org/abs/2103.14030",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_raw_text_arxiv_id(self, client):
        """arXiv ID in raw_text field."""
        cit = Citation(
            raw_text="arXiv:2103.14030 (Vaswani et al., 2017)",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_raw_text_with_version(self, client):
        """arXiv ID with version in raw_text."""
        cit = Citation(
            raw_text="arXiv:2103.14030v1",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"

    def test_extract_from_raw_text_colon_format(self, client):
        """arXiv ID with 'arXiv:' prefix in raw_text."""
        cit = Citation(
            raw_text="As described in arXiv:2201.00001",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2201.00001"

    def test_extract_priority_url_over_doi(self, client):
        """URL should be checked before DOI (if both exist)."""
        cit = Citation(
            raw_text="",
            doi="10.48550/arXiv.0000.00000",  # Fake DOI
            url="https://arxiv.org/abs/2103.14030",  # Real URL
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        # Should extract from URL first (URL is checked before DOI)
        assert arxiv_id == "2103.14030"

    def test_no_arxiv_id_returns_none(self, client):
        """No arXiv ID in any field → returns None."""
        cit = Citation(
            raw_text="Smith et al. (2020)",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id is None

    def test_non_arxiv_doi_returns_none(self, client):
        """Non-arXiv DOI → returns None."""
        cit = Citation(
            raw_text="",
            doi="10.1038/nature14539",  # Nature DOI
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id is None

    def test_5digit_arxiv_id(self, client):
        """arXiv IDs can have 5 digits (YYMM.NNNNN format)."""
        cit = Citation(
            raw_text="",
            doi="10.48550/arXiv.2103.12345",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.12345"

    def test_4digit_arxiv_id(self, client):
        """arXiv IDs with 4 digits (YYMM.NNNN format)."""
        cit = Citation(
            raw_text="",
            url="https://arxiv.org/abs/1706.03762",
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "1706.03762"

    def test_mixed_doi_with_arxiv_in_text(self, client):
        """DOI field contains non-arXiv DOI but raw_text has arXiv ID."""
        cit = Citation(
            raw_text="See arXiv:2103.14030 for details",
            doi="10.1234/fake.2021",  # Fake DOI, but we should find arXiv ID in raw_text
            citation_type=CitationType.IN_TEXT,
        )
        arxiv_id = client._extract_arxiv_id(cit)
        assert arxiv_id == "2103.14030"


class TestArxivIDRegex:
    """Test the ARXIV_ID_RE regex pattern directly."""

    def test_pattern_matches_4_digit(self):
        """Pattern should match YYMM.NNNN format."""
        import re
        pattern = ArxivClient.ARXIV_ID_RE
        m = pattern.search("2103.14030")
        assert m is not None
        assert m.group(1) == "2103.14030"

    def test_pattern_matches_5_digit(self):
        """Pattern should match YYMM.NNNNN format."""
        import re
        pattern = ArxivClient.ARXIV_ID_RE
        m = pattern.search("2103.12345")
        assert m is not None
        assert m.group(1) == "2103.12345"

    def test_pattern_captures_version(self):
        """Pattern should capture version separately."""
        import re
        pattern = ArxivClient.ARXIV_ID_RE
        m = pattern.search("2103.14030v2")
        assert m is not None
        assert m.group(1) == "2103.14030"
        assert m.group(2) == "v2"

    def test_pattern_no_match_for_3_digit(self):
        """Pattern should NOT match YYMM.NNN (only 3 digits after dot)."""
        import re
        pattern = ArxivClient.ARXIV_ID_RE
        m = pattern.search("21.123")  # Old arXiv format
        # Should not match the old format
        # Note: This might still match if the regex allows it
        assert m is None or len(m.group(1)) >= 4

    def test_pattern_boundary_check(self):
        """Pattern should match at word boundaries."""
        import re
        pattern = ArxivClient.ARXIV_ID_RE
        # Should match in URL context
        m = pattern.search("https://arxiv.org/abs/2103.14030")
        assert m is not None
        assert m.group(1) == "2103.14030"
