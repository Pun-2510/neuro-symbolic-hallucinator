"""Unit tests cho 4 retrieval HTTP clients (Crossref, OpenAlex, S2, arXiv).

Mock HTTP responses via httpx.MockTransport để tránh gọi API thật.
Reference: v1.2 §3.6 — tuần 8.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest

from integrity_checker.matching.author_parser import Author
from integrity_checker.models.citation import Citation
from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient


# ---------- Mock helpers ----------

def _patch_httpx(handler):
    """Patch httpx.AsyncClient.get để trả mock response.

    Strategy: patch `httpx.AsyncClient.get` thay vì patch AsyncClient constructor
    (patching constructor gây infinite recursion trong venv). Handler nhận URL,
    trả httpx.Response.

    Handler signature: handler(request: httpx.Request, **kwargs) -> httpx.Response
    Headers và params từ kwargs được set trên Request trước khi gọi handler.
    """
    async def mock_get(self, url, **kwargs):
        # Build Request với headers từ kwargs
        headers = kwargs.get("headers") or {}
        params = kwargs.get("params") or {}
        req = httpx.Request("GET", url, headers=headers, params=params)
        return handler(req)
    return patch.object(httpx.AsyncClient, "get", mock_get)


def _make_citation(**kwargs) -> Citation:
    """Helper build Citation cho test."""
    defaults = dict(
        raw_text="Smith, J. (2020). A study of X. Journal A, 10, 1-10.",
        title="A study of X",
        year="2020",
        doi=None,
        url=None,
    )
    defaults.update(kwargs)
    return Citation(**defaults)


# ============================================================
# Crossref tests
# ============================================================

class TestCrossrefClient:
    """Test CrossrefClient với mocked HTTP."""

    @pytest.fixture
    def client(self):
        return CrossrefClient(contact_email="test@example.com")

    @pytest.mark.asyncio
    async def test_lookup_by_doi_success(self, client):
        """DOI exact lookup trả về candidate với confidence=1.0."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/works/" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "message": {
                        "DOI": "10.1234/abc",
                        "title": ["A study of X"],
                        "author": [
                            {"given": "John", "family": "Smith"}
                        ],
                        "published-print": {"date-parts": [[2020]]},
                        "container-title": ["Journal A"],
                        "URL": "https://example.com/paper",
                    },
                },
            )

        with _patch_httpx(handler):
            cit = _make_citation(doi="10.1234/abc")
            result = await client.lookup(cit)

        assert result.found is True
        assert result.confidence == 1.0
        assert result.doi == "10.1234/abc"
        assert result.title == "A study of X"
        assert result.authors == ["John Smith"]
        assert result.year == "2020"
        assert result.venue == "Journal A"

    @pytest.mark.asyncio
    async def test_lookup_doi_not_found_falls_back_to_bibliographic(self, client):
        """DOI 404 → fallback bibliographic search."""
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            url = str(request.url)
            if "/works/10.1234" in url:
                return httpx.Response(404, json={"status": "not_found"})
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "message": {
                        "items": [
                            {
                                "DOI": "10.1234/abc",
                                "title": ["A study of X"],
                                "author": [{"given": "J.", "family": "Smith"}],
                                "published-print": {"date-parts": [[2020]]},
                                "container-title": ["Journal A"],
                                "score": 95.0,
                            }
                        ]
                    },
                },
            )

        with _patch_httpx(handler):
            cit = _make_citation(doi="10.1234/abc")
            cit.authors = [
                Author(last_name="Smith", initials=["j"],
                       full_first_names=[], normalized="smith|j", raw="Smith, J.")
            ]
            result = await client.lookup(cit)

        assert result.found is True
        # 95 score → 0.95 confidence
        assert 0.9 < result.confidence <= 1.0
        assert call_count["n"] >= 2  # DOI 404 + fallback

    def test_normalize_doi(self, client):
        """_normalize_doi lowercase + strip 'doi:' + strip trailing period."""
        assert client._normalize_doi("DOI:10.1234/ABC.") == "10.1234/abc"
        assert client._normalize_doi("10.1234/abc") == "10.1234/abc"

    def test_message_to_candidate_minimal(self, client):
        """_message_to_candidate handles missing fields gracefully."""
        cand = client._message_to_candidate({})
        assert cand.doi is None
        assert cand.title is None
        assert cand.authors == []


# ============================================================
# OpenAlex tests
# ============================================================

class TestOpenAlexClient:
    """Test OpenAlexClient với mocked HTTP."""

    @pytest.fixture
    def client(self):
        return OpenAlexClient(contact_email="test@example.com")

    @pytest.mark.asyncio
    async def test_lookup_by_doi_success(self, client):
        """DOI lookup qua /works/doi:{doi}."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/works/doi:10.1234/abc" in str(request.url)
            return httpx.Response(
                200,
                json={
                    "id": "https://openalex.org/W123",
                    "doi": "https://doi.org/10.1234/abc",
                    "title": "A study of X",
                    "authorships": [
                        {"author": {"display_name": "John Smith"}}
                    ],
                    "publication_year": 2020,
                    "primary_location": {
                        "source": {"display_name": "Journal A"}
                    },
                },
            )

        with _patch_httpx(handler):
            cit = _make_citation(doi="10.1234/abc")
            result = await client.lookup(cit)

        assert result.found is True
        assert result.doi == "10.1234/abc"  # stripped https://doi.org/
        assert result.title == "A study of X"
        assert result.authors == ["John Smith"]
        assert result.year == "2020"
        assert result.venue == "Journal A"

    @pytest.mark.asyncio
    async def test_lookup_by_search_with_year_filter(self, client):
        """Search fallback với publication_year filter."""
        captured_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_params.update(dict(request.url.params))
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "https://openalex.org/W123",
                            "title": "A study of X",
                            "authorships": [],
                            "publication_year": 2020,
                            "relevance_score": 150.0,
                        }
                    ]
                },
            )

        with _patch_httpx(handler):
            cit = _make_citation(doi=None, title="A study of X", year="2020")
            result = await client.lookup(cit)

        assert result.found is True
        # 150 relevance → cap at 1.0
        assert result.confidence == 1.0
        assert captured_params.get("filter") == "publication_year:2020"

    @pytest.mark.asyncio
    async def test_no_title_no_doi(self, client):
        """Citation không có title + DOI → trả found=False với error message."""
        cit = _make_citation(title=None, doi=None)
        result = await client.lookup(cit)
        assert result.found is False
        assert "no title" in result.error


# ============================================================
# Semantic Scholar tests
# ============================================================

class TestSemanticScholarClient:
    """Test SemanticScholarClient với mocked HTTP."""

    @pytest.fixture
    def client(self):
        return SemanticScholarClient(api_key="test-key")

    @pytest.mark.asyncio
    async def test_lookup_by_doi(self, client):
        """DOI exact lookup qua /paper/DOI:{doi}."""
        def handler(request: httpx.Request) -> httpx.Response:
            assert "/paper/DOI:10.1234/abc" in str(request.url)
            assert request.headers.get("x-api-key") == "test-key"
            return httpx.Response(
                200,
                json={
                    "paperId": "abc123",
                    "title": "A study of X",
                    "authors": [{"name": "John Smith"}],
                    "year": 2020,
                    "venue": "Journal A",
                    "externalIds": {"DOI": "10.1234/abc"},
                    "url": "https://semanticscholar.org/paper/abc123",
                },
            )

        with _patch_httpx(handler):
            cit = _make_citation(doi="10.1234/abc")
            result = await client.lookup(cit)

        assert result.found is True
        assert result.confidence == 1.0
        assert result.doi == "10.1234/abc"
        assert result.external_ids.get("DOI") == "10.1234/abc"

    def test_extract_arxiv_id_from_url(self, client):
        """arXiv ID extraction từ URL."""
        assert client._extract_arxiv_id(_make_citation(
            url="https://arxiv.org/abs/2106.12345"
        )) == "2106.12345"
        # Version suffix stripped
        assert client._extract_arxiv_id(_make_citation(
            url="https://arxiv.org/abs/2106.12345v2"
        )) == "2106.12345"
        # pdf URL
        assert client._extract_arxiv_id(_make_citation(
            url="https://arxiv.org/pdf/2106.12345.pdf"
        )) == "2106.12345"
        # No arXiv
        assert client._extract_arxiv_id(_make_citation(
            url="https://example.com/paper"
        )) is None


# ============================================================
# arXiv tests (sync SDK wrapped async)
# ============================================================

class TestArxivClient:
    """Test ArxivClient với mocked arxiv SDK."""

    @pytest.fixture
    def client(self):
        return ArxivClient()

    def test_extract_arxiv_id(self, client):
        """arXiv ID extraction regex."""
        assert client._extract_arxiv_id(_make_citation(
            url="https://arxiv.org/abs/2106.12345"
        )) == "2106.12345"
        assert client._extract_arxiv_id(_make_citation(
            raw_text="See arxiv:2106.12345 for details"
        )) == "2106.12345"
        assert client._extract_arxiv_id(_make_citation()) is None

    def test_result_to_candidate_strips_version(self, client):
        """_result_to_candidate strips version suffix từ arxiv_id."""
        d = {
            "title": "Test",
            "authors": ["Alice"],
            "year": "2021",
            "doi": None,
            "url": "http://arxiv.org/abs/2106.12345v2",
            "arxiv_id": "2106.12345v2",
        }
        cand = client._result_to_candidate(d)
        assert cand.external_ids.get("arxiv") == "2106.12345"


# ============================================================
# Integration: error handling
# ============================================================

class TestRetryBehavior:
    """Test retry + exponential backoff behavior."""

    @pytest.mark.asyncio
    async def test_crossref_404_returns_none(self):
        """404 → trả None (không retry)."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404)

        client = CrossrefClient()
        with _patch_httpx(handler):
            cit = _make_citation(doi="10.1234/missing")
            result = await client.lookup(cit)

        assert result.found is False
        # Có error message
        assert result.error is not None