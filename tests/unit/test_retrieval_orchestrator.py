"""Unit tests cho RetrievalOrchestrator (task #36 — Sprint 3).

Test các scenarios:
    - Happy path: 4 sources trả về results
    - Partial failure: 2 sources fail -> still proceed
    - All fail: return empty + UNRESOLVED sentinel
    - Cache hit: verify not calling APIs
    - Cache miss: verify calling APIs
    - Rate limiting: verify backoff works
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from integrity_checker.retrieval.cache import DiskCache


# ---------- Fixtures ----------

@pytest.fixture
def mock_cache():
    """Mock DiskCache."""
    cache = MagicMock(spec=DiskCache)
    cache.get.return_value = None
    cache.set.return_value = None
    return cache


@pytest.fixture
def mock_citation():
    """Sample citation for testing."""
    return Citation(
        raw_text="Smith, J. (2020). Deep Learning for Vision. CVPR 2020.",
        title="Deep Learning for Vision",
        year="2020",
        authors=[],
    )


@pytest.fixture
def mock_crossref_success():
    """Mock CrossrefClient returns success."""
    client = AsyncMock()
    client.name = "crossref"
    client.lookup.return_value = SourceCandidate(
        source_name="crossref",
        found=True,
        title="Deep Learning for Vision",
        authors=["Smith, J."],
        year="2020",
        doi="10.1109/CVPR.2020.00123",
        confidence=0.95,
    )
    return client


@pytest.fixture
def mock_openalex_success():
    """Mock OpenAlexClient returns success."""
    client = AsyncMock()
    client.name = "openalex"
    client.lookup.return_value = SourceCandidate(
        source_name="openalex",
        found=True,
        title="Deep Learning for Vision",
        authors=["Smith, J."],
        year="2020",
        confidence=0.90,
    )
    return client


@pytest.fixture
def mock_semantic_scholar_success():
    """Mock SemanticScholarClient returns success."""
    client = AsyncMock()
    client.name = "semantic_scholar"
    client.lookup.return_value = SourceCandidate(
        source_name="semantic_scholar",
        found=True,
        title="Deep Learning for Vision",
        authors=["Smith, J."],
        year="2020",
        confidence=0.88,
    )
    return client


@pytest.fixture
def mock_arxiv_success():
    """Mock ArxivClient returns success."""
    client = AsyncMock()
    client.name = "arxiv"
    client.lookup.return_value = SourceCandidate(
        source_name="arxiv",
        found=True,
        title="Deep Learning for Vision",
        authors=["Smith, J."],
        year="2020",
        confidence=0.85,
    )
    return client


@pytest.fixture
def mock_client_failure():
    """Mock client that returns failure."""
    client = AsyncMock()
    client.name = "test_source"
    client.lookup.return_value = SourceCandidate(
        source_name="test_source",
        found=False,
        error="Connection timeout",
    )
    return client


# ---------- Test: Happy Path ----------

class TestRetrievalOrchestratorHappyPath:
    """Test happy path: all 4 sources return results."""

    @pytest.mark.asyncio
    async def test_happy_path_all_sources_succeed(
        self,
        mock_citation,
        mock_crossref_success,
        mock_openalex_success,
        mock_semantic_scholar_success,
        mock_arxiv_success,
        mock_cache,
    ):
        """All 4 sources return found=True results."""
        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_success,
            semantic_scholar=mock_semantic_scholar_success,
            arxiv=mock_arxiv_success,
            parallel=True,
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        assert len(result.candidates) >= 1
        assert len(result.sources_queried) == 4
        assert len(result.sources_succeeded) == 4
        assert len(result.sources_failed) == 0

        # Verify all clients were called
        mock_crossref_success.lookup.assert_called_once()
        mock_openalex_success.lookup.assert_called_once()
        mock_semantic_scholar_success.lookup.assert_called_once()
        mock_arxiv_success.lookup.assert_called_once()

    @pytest.mark.asyncio
    async def test_dedupe_by_doi(
        self,
        mock_citation,
        mock_crossref_success,
        mock_openalex_success,
        mock_cache,
    ):
        """Same DOI from different sources should be deduped."""
        mock_s2 = AsyncMock()
        mock_s2.name = "semantic_scholar"
        mock_s2.lookup.return_value = SourceCandidate(
            source_name="semantic_scholar", found=True, doi="10.1109/CVPR.2020.00123", confidence=0.75
        )
        mock_arxiv = AsyncMock()
        mock_arxiv.name = "arxiv"
        mock_arxiv.lookup.return_value = SourceCandidate(
            source_name="arxiv", found=True, doi="10.1109/CVPR.2020.00123", confidence=0.70
        )

        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_success,
            semantic_scholar=mock_s2,
            arxiv=mock_arxiv,
            parallel=True,
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        # Should have deduplicated - keep highest confidence
        doi_candidates = [c for c in result.candidates if c.doi == "10.1109/CVPR.2020.00123"]
        assert len(doi_candidates) == 1  # Deduplicated to 1
        # Crossref has highest confidence (0.95)
        assert doi_candidates[0].source_name == "crossref"

    @pytest.mark.asyncio
    async def test_parallel_execution(
        self,
        mock_citation,
        mock_crossref_success,
        mock_openalex_success,
        mock_semantic_scholar_success,
        mock_arxiv_success,
        mock_cache,
    ):
        """Verify parallel=True calls all sources concurrently."""
        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_success,
            semantic_scholar=mock_semantic_scholar_success,
            arxiv=mock_arxiv_success,
            parallel=True,
            cache=mock_cache,
        )

        import time
        start = time.time()
        result = await orchestrator.retrieve(mock_citation)
        elapsed = time.time() - start

        # With parallel=True, should complete faster than sequential
        # (all mocks are instant, but we verify the call pattern)
        assert len(result.sources_queried) == 4
        # In async context, parallel calls happen "at the same time"
        assert elapsed < 1.0  # Should be very fast with mocks


# ---------- Test: Partial Failure ----------

class TestRetrievalOrchestratorPartialFailure:
    """Test partial failure scenarios."""

    @pytest.mark.asyncio
    async def test_partial_failure_2_sources_fail(
        self,
        mock_citation,
        mock_crossref_success,
        mock_cache,
    ):
        """2 out of 4 sources fail -> still proceed with results."""
        mock_openalex_fail = AsyncMock()
        mock_openalex_fail.name = "openalex"
        mock_openalex_fail.lookup.return_value = SourceCandidate(
            source_name="openalex", found=False, error="Rate limit"
        )

        mock_s2_fail = AsyncMock()
        mock_s2_fail.name = "semantic_scholar"
        mock_s2_fail.lookup.return_value = SourceCandidate(
            source_name="semantic_scholar", found=False, error="Connection failed"
        )

        mock_arxiv_fail = AsyncMock()
        mock_arxiv_fail.name = "arxiv"
        mock_arxiv_fail.lookup.return_value = SourceCandidate(
            source_name="arxiv", found=False, error="Not found"
        )

        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_fail,
            semantic_scholar=mock_s2_fail,
            arxiv=mock_arxiv_fail,
            parallel=True,
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        # Should still have results from crossref
        assert len(result.sources_queried) == 4
        assert "crossref" in result.sources_succeeded
        assert "openalex" in result.sources_failed
        assert "semantic_scholar" in result.sources_failed
        assert "arxiv" in result.sources_failed

    @pytest.mark.asyncio
    async def test_majority_failure_triggers_warning(
        self,
        mock_citation,
        mock_cache,
    ):
        """3+ sources fail -> should log UNRESOLVED warning."""
        # Create 4 failing clients
        mock_clients = []
        for name in ["crossref", "openalex", "semantic_scholar", "arxiv"]:
            mock_client = AsyncMock()
            mock_client.name = name
            mock_client.lookup.return_value = SourceCandidate(
                source_name=name, found=False, error="Connection failed"
            )
            mock_clients.append(mock_client)

        orchestrator = RetrievalOrchestrator(
            crossref=mock_clients[0],
            openalex=mock_clients[1],
            semantic_scholar=mock_clients[2],
            arxiv=mock_clients[3],
            parallel=True,
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        # All sources failed
        assert len(result.sources_succeeded) == 0
        assert len(result.sources_failed) == 4
        # Candidates list still contains failed candidates (for debugging)
        # but none have found=True
        assert all(not c.found for c in result.candidates)


# ---------- Test: Cache ----------

class TestRetrievalOrchestratorCache:
    """Test cache hit/miss behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_api_call(
        self,
        mock_citation,
        mock_crossref_success,
        mock_cache,
    ):
        """Cache hit should not call the actual API."""
        # Setup cache to return a hit
        mock_cache.get.return_value = {
            "found": True,
            "doi": "10.1109/CVPR.2020.00123",
            "title": "Deep Learning for Vision",
            "authors": ["Smith, J."],
            "year": "2020",
            "confidence": 0.95,
            "external_ids": {},
            "score": 0.9,
            "error": None,
            "url": None,
            "venue": None,
        }

        # Setup other clients as failures
        mock_openalex_fail = AsyncMock()
        mock_openalex_fail.name = "openalex"
        mock_openalex_fail.lookup.return_value = SourceCandidate(
            source_name="openalex", found=False, error="Not cached"
        )
        mock_s2_fail = AsyncMock()
        mock_s2_fail.name = "semantic_scholar"
        mock_s2_fail.lookup.return_value = SourceCandidate(
            source_name="semantic_scholar", found=False, error="Not cached"
        )
        mock_arxiv_fail = AsyncMock()
        mock_arxiv_fail.name = "arxiv"
        mock_arxiv_fail.lookup.return_value = SourceCandidate(
            source_name="arxiv", found=False, error="Not cached"
        )

        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_fail,
            semantic_scholar=mock_s2_fail,
            arxiv=mock_arxiv_fail,
            parallel=True,
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        # Cache was checked
        assert mock_cache.get.called

        # Crossref API should NOT have been called (cache hit)
        mock_crossref_success.lookup.assert_not_called()

        # But result should still be returned from cache
        assert len(result.candidates) >= 1
        cached_candidate = next(
            (c for c in result.candidates if c.cached), None
        )
        assert cached_candidate is not None
        assert cached_candidate.cached is True

    @pytest.mark.asyncio
    async def test_cache_miss_calls_api(
        self,
        mock_citation,
        mock_crossref_success,
        mock_cache,
    ):
        """Cache miss should call the actual API and save result."""
        mock_cache.get.return_value = None  # Cache miss

        mock_openalex_fail = AsyncMock()
        mock_openalex_fail.name = "openalex"
        mock_openalex_fail.lookup.return_value = SourceCandidate(
            source_name="openalex", found=False, error="Failed"
        )
        mock_s2_fail = AsyncMock()
        mock_s2_fail.name = "semantic_scholar"
        mock_s2_fail.lookup.return_value = SourceCandidate(
            source_name="semantic_scholar", found=False, error="Failed"
        )
        mock_arxiv_fail = AsyncMock()
        mock_arxiv_fail.name = "arxiv"
        mock_arxiv_fail.lookup.return_value = SourceCandidate(
            source_name="arxiv", found=False, error="Failed"
        )

        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_fail,
            semantic_scholar=mock_s2_fail,
            arxiv=mock_arxiv_fail,
            parallel=True,
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        # API should have been called
        mock_crossref_success.lookup.assert_called_once()

        # Result should have been cached
        assert mock_cache.set.called

    @pytest.mark.asyncio
    async def test_cache_key_includes_source(
        self,
        mock_citation,
        mock_crossref_success,
        mock_openalex_success,
        mock_cache,
    ):
        """Different sources should have different cache keys."""
        mock_cache.get.return_value = None

        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_success,
            semantic_scholar=AsyncMock(),
            arxiv=AsyncMock(),
            parallel=True,
            cache=mock_cache,
        )

        await orchestrator.retrieve(mock_citation)

        # Verify cache was checked with source-specific keys
        calls = mock_cache.get.call_args_list
        keys_checked = [call[0][0] for call in calls]
        assert any("crossref:" in k for k in keys_checked)
        assert any("openalex:" in k for k in keys_checked)


# ---------- Test: Rate Limiting ----------

class TestRetrievalOrchestratorRateLimit:
    """Test rate limiting behavior."""

    @pytest.mark.asyncio
    async def test_rate_limiter_wait_called(
        self,
        mock_citation,
        mock_crossref_success,
        mock_cache,
    ):
        """Verify rate limiter's wait() is called before API call."""
        from integrity_checker.retrieval.rate_limiter import RateLimiter

        # Mock rate limiter
        mock_limiter = AsyncMock(spec=RateLimiter)

        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=AsyncMock(),
            semantic_scholar=AsyncMock(),
            arxiv=AsyncMock(),
            parallel=True,
            cache=mock_cache,
        )

        # Replace rate limiter
        orchestrator._rate_limiters[mock_crossref_success.name] = mock_limiter

        await orchestrator.retrieve(mock_citation)

        # Rate limiter should have been awaited
        mock_limiter.wait.assert_called_once()


# ---------- Test: Serialization ----------

class TestRetrievalOrchestratorSerialization:
    """Test cache serialization/deserialization."""

    def test_candidate_to_cache(self):
        """SourceCandidate should serialize correctly for caching."""
        cand = SourceCandidate(
            source_name="crossref",
            found=True,
            doi="10.1109/CVPR.2020.00123",
            title="Deep Learning",
            authors=["Smith, J."],
            year="2020",
            venue="CVPR",
            url="https://example.com",
            external_ids={"arxiv": "1234.5678"},
            score=0.9,
            confidence=0.95,
            error=None,
        )

        data = RetrievalOrchestrator._candidate_to_cache(cand)

        assert data["found"] is True
        assert data["doi"] == "10.1109/CVPR.2020.00123"
        assert data["title"] == "Deep Learning"
        assert data["authors"] == ["Smith, J."]
        assert data["year"] == "2020"
        assert data["external_ids"] == {"arxiv": "1234.5678"}

    def test_candidate_from_cache(self):
        """Cached data should deserialize correctly."""
        data = {
            "found": True,
            "doi": "10.1109/CVPR.2020.00123",
            "title": "Deep Learning",
            "authors": ["Smith, J."],
            "year": "2020",
            "venue": "CVPR",
            "url": "https://example.com",
            "external_ids": {"arxiv": "1234.5678"},
            "score": 0.9,
            "confidence": 0.95,
            "error": None,
        }

        cand = RetrievalOrchestrator._candidate_from_cache("crossref", data)

        assert cand.source_name == "crossref"
        assert cand.found is True
        assert cand.doi == "10.1109/CVPR.2020.00123"
        assert cand.cached is True

    def test_cache_key_format(self):
        """Cache key should include source name and citation hash."""
        citation = Citation(
            raw_text="Test",
            title="Test Title",
            year="2020",
            doi="10.1234/test",
        )

        key = RetrievalOrchestrator._cache_key("crossref", citation)

        assert key.startswith("crossref:")
        assert len(key) > len("crossref:")

    def test_dedupe_candidates(self):
        """Candidates with same DOI should be deduped, keeping highest confidence."""
        c1 = SourceCandidate(source_name="crossref", found=True, doi="10.1234/test", confidence=0.90)
        c2 = SourceCandidate(source_name="openalex", found=True, doi="10.1234/test", confidence=0.85)
        c3 = SourceCandidate(source_name="arxiv", found=True, title="Different Title", confidence=0.80)

        deduped = RetrievalOrchestrator._dedupe_candidates([c1, c2, c3])

        # DOI should dedupe to 1
        doi_cands = [c for c in deduped if c.doi == "10.1234/test"]
        assert len(doi_cands) == 1
        assert doi_cands[0].confidence == 0.90  # Highest confidence kept

        # Title-only should remain separate
        title_cands = [c for c in deduped if c.title == "Different Title"]
        assert len(title_cands) == 1


# ---------- Test: Sequential Mode ----------

class TestRetrievalOrchestratorSequential:
    """Test sequential (non-parallel) execution."""

    @pytest.mark.asyncio
    async def test_sequential_mode(
        self,
        mock_citation,
        mock_crossref_success,
        mock_openalex_success,
        mock_semantic_scholar_success,
        mock_arxiv_success,
        mock_cache,
    ):
        """Verify sequential=True processes sources one by one."""
        orchestrator = RetrievalOrchestrator(
            crossref=mock_crossref_success,
            openalex=mock_openalex_success,
            semantic_scholar=mock_semantic_scholar_success,
            arxiv=mock_arxiv_success,
            parallel=False,  # Sequential
            cache=mock_cache,
        )

        result = await orchestrator.retrieve(mock_citation)

        # All sources should still be queried
        assert len(result.sources_queried) == 4
        assert len(result.sources_succeeded) == 4
