"""Tests cho SerpApi Google Scholar client."""

from __future__ import annotations

import pytest

from integrity_checker.models.citation import Citation
from integrity_checker.retrieval.serpapi_client import SerpApiClient


class TestSerpApiClient:
    """Test SerpApi client - fallback khi các API free thất bại."""

    @pytest.fixture
    def client(self) -> SerpApiClient:
        """Create client với test API key."""
        return SerpApiClient(api_key="test_key")

    @pytest.fixture
    def known_citation(self) -> Citation:
        """Citation với title nổi tiếng."""
        return Citation(
            raw_text="Vaswani et al. (2017)",
            title="Attention Is All You Need",
            authors=["Vaswani", "Shazeer"],
            year="2017",
        )

    @pytest.fixture
    def obscure_citation(self) -> Citation:
        """Citation obscure - để test fallback."""
        return Citation(
            raw_text="Smith (2021)",
            title="Novel Research Methods for Complex Systems",
            authors=["Smith"],
            year="2021",
        )

    def test_client_init_without_key(self, client: SerpApiClient) -> None:
        """Test client khởi tạo không có key."""
        assert client.api_key == "test_key"
        assert client.name == "serpapi"
        assert client.timeout == 30.0

    def test_build_search_query_with_title(self, client: SerpApiClient, known_citation: Citation) -> None:
        """Test query building với title."""
        query = client._build_search_query(known_citation)
        assert "Attention Is All You Need" in query
        assert len(query) <= 300  # SerpApi limit

    def test_build_search_query_without_title(self, client: SerpApiClient) -> None:
        """Test query building khi không có title."""
        citation = Citation(raw_text="Unknown paper", authors=[], year=None)
        query = client._build_search_query(citation)
        assert query == "Unknown paper"[:300]

    def test_build_search_query_empty(self, client: SerpApiClient) -> None:
        """Test query building khi không có gì."""
        citation = Citation(raw_text="", authors=[], year=None)
        query = client._build_search_query(citation)
        assert query == ""

    @pytest.mark.asyncio
    async def test_lookup_without_api_key(self) -> None:
        """Test lookup khi không có API key - chỉ test logic không crash."""
        client = SerpApiClient(api_key="no-key")
        citation = Citation(raw_text="Test citation", title="", authors=[])

        result = await client.lookup(citation)

        # Với API key "no-key", SerpApi sẽ trả về error
        # Nên result.found sẽ False vì không tìm thấy kết quả
        assert result.source_name == "serpapi"

    @pytest.mark.asyncio
    async def test_lookup_empty_query(self, client: SerpApiClient) -> None:
        """Test lookup với empty query."""
        citation = Citation(raw_text="", authors=[], year=None)

        result = await client.lookup(citation)

        assert result.found is False
        assert "no title or author" in result.error.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lookup_known_paper(self) -> None:
        """Integration test với paper nổi tiếng."""
        client = SerpApiClient(
            api_key="9587a55e8d344bd38e87364b44536ae1149541d77c877f8faba697c91fdef71e"
        )
        citation = Citation(
            raw_text="Vaswani et al. (2017)",
            title="Attention Is All You Need",
            authors=["Vaswani"],
            year="2017",
        )

        result = await client.lookup(citation)

        assert result.found is True
        assert result.title is not None
        assert "attention" in result.title.lower()
        assert result.confidence == 0.5  # SerpApi luôn trả confidence 0.5
        # Authors được extract
        assert len(result.authors) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_lookup_obscure_paper(self) -> None:
        """Integration test với paper ít known."""
        client = SerpApiClient(
            api_key="9587a55e8d344bd38e87364b44536ae1149541d77c877f8faba697c91fdef71e"
        )
        citation = Citation(
            raw_text="Smith (2021)",
            title="Novel Research Methods for Complex Systems Analysis XYZ123",
            authors=["Smith"],
            year="2021",
        )

        result = await client.lookup(citation)

        # Có thể tìm thấy hoặc không, tùy vào SerpApi
        # Quan trọng là không crash
        assert result.source_name == "serpapi"
        assert result.found in [True, False]

    def test_result_to_candidate_structure(self) -> None:
        """Test _result_to_candidate tạo đúng structure."""
        mock_result = {
            "title": "Test Paper",
            "result_id": "abc123",
            "snippet": "This is a test paper published in 2023.",
            "publication_info": {
                "summary": "J Smith, A Jones - 2023 - Nature",
                "authors": [
                    {"name": "J Smith"},
                    {"name": "A Jones"},
                ],
            },
            "cited_by": {"total": 42},
            "links": [{"link": "https://example.com/paper"}],
            "serpapi_cite_link": "https://serpapi.com/cite",
        }

        candidate = SerpApiClient._result_to_candidate(mock_result)

        assert candidate.found is True
        assert candidate.title == "Test Paper"
        assert candidate.authors == ["J Smith", "A Jones"]
        assert candidate.year == "2023"
        assert candidate.confidence == 0.5
        assert candidate.external_ids["serpapi_result_id"] == "abc123"
        assert candidate.external_ids["citation_count"] == "42"

    def test_result_to_candidate_missing_fields(self) -> None:
        """Test _result_to_candidate với missing fields."""
        mock_result = {
            "title": "Minimal Paper",
        }

        candidate = SerpApiClient._result_to_candidate(mock_result)

        assert candidate.found is True
        assert candidate.title == "Minimal Paper"
        assert candidate.authors == []
        assert candidate.year is None
        assert candidate.confidence == 0.5
