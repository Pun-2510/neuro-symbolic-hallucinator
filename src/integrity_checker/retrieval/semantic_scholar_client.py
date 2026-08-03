"""Semantic Scholar API client — supplement với citation graph.

Rate limit: 1 req/s (anonymized), 100 req/s với API key.
Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient

logger = get_logger(__name__)


class SemanticScholarClient(BaseScholarClient):
    """Semantic Scholar Graph API client.

    Implements:
        - DOI lookup (GET /paper/DOI:{doi}).
        - arXiv lookup (GET /paper/ARXIV:{id}).
        - Title search (GET /paper/search?query=...).
        - Tenacity retry + exponential backoff.
        - Optional API key qua S2_API_KEY env (tăng rate limit).
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    name = "semantic_scholar"

    # Fields trả về từ /paper/search và /paper/{id}
    PAPER_FIELDS = "title,authors,year,externalIds,venue,url,abstract"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        super().__init__(timeout=timeout)
        self.api_key = api_key or os.getenv("S2_API_KEY", "")
        self.max_retries = max_retries
        self._headers = {"x-api-key": self.api_key} if self.api_key else {}

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup bằng DOI / arXiv ID exact; fallback bằng search."""
        # 1. DOI exact
        if citation.doi:
            doi_norm = self._normalize_doi(citation.doi)
            result = await self._lookup_by_id(f"DOI:{doi_norm}")
            if result and result.found:
                return result

        # 2. arXiv ID exact (nếu có)
        arxiv_id = self._extract_arxiv_id(citation)
        if arxiv_id:
            result = await self._lookup_by_id(f"ARXIV:{arxiv_id}")
            if result and result.found:
                return result

        # 3. Title search fallback
        return await self._lookup_by_search(citation)

    async def _lookup_by_id(self, paper_id: str) -> SourceCandidate | None:
        """GET /paper/{id}?fields=..."""
        path = f"/paper/{paper_id}"
        params = {"fields": self.PAPER_FIELDS}
        data = await self._fetch_json_with_retry(path, params=params)
        if not data or not data.get("paperId"):
            return None

        cand = self._paper_to_candidate(data)
        cand.found = True
        cand.confidence = 1.0  # ID exact = highest confidence
        return cand

    async def _lookup_by_search(self, citation: Citation) -> SourceCandidate:
        """GET /paper/search?query={title}&limit=1."""
        if not citation.title:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="S2: no title for search",
            )

        params = {
            "query": citation.title[:200],
            "limit": 1,
            "fields": self.PAPER_FIELDS,
        }
        # Optional year filter
        if citation.year:
            params["year"] = f"{citation.year}-{citation.year}"

        data = await self._fetch_json_with_retry("/paper/search", params=params)
        if not data:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"S2: no response for '{citation.title[:60]}'",
            )

        results = data.get("data") or []
        if not results:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"S2: no results for '{citation.title[:60]}'",
            )

        top = results[0]
        cand = self._paper_to_candidate(top)
        cand.found = True
        cand.confidence = 0.7  # Search match — không exact
        return cand

    async def _fetch_json_with_retry(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict | None:
        """GET với tenacity retry + exponential backoff."""
        url = f"{self.BASE_URL}{path}"
        retry = AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(
                (httpx.HTTPError, httpx.TimeoutException)
            ),
            reraise=False,
        )
        try:
            async for attempt in retry:
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        resp = await client.get(
                            url, headers=self._headers, params=params or {}
                        )
                        if resp.status_code == 404:
                            return None
                        if resp.status_code == 429 or resp.status_code >= 500:
                            resp.raise_for_status()
                        if resp.status_code != 200:
                            logger.warning(
                                f"S2 {resp.status_code}: {url}"
                            )
                            return None
                        return resp.json()
            return None
        except RetryError:
            logger.error(f"S2 retry exhausted: {url}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"S2 HTTP error: {e}")
            return None

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI: lowercase, strip 'doi:' prefix, strip trailing period."""
        d = doi.strip().lower()
        if d.startswith("doi:"):
            d = d[4:].strip()
        return d.rstrip(".")

    @staticmethod
    def _extract_arxiv_id(citation: Citation) -> str | None:
        """Extract arXiv ID từ URL hoặc external_ids nếu có."""
        # Check URL field
        if citation.url and "arxiv.org" in citation.url:
            # Format: https://arxiv.org/abs/2106.12345 hoặc /pdf/2106.12345
            for marker in ("/abs/", "/pdf/"):
                idx = citation.url.find(marker)
                if idx >= 0:
                    arxiv_id = citation.url[idx + len(marker):]
                    # Strip version suffix (v1, v2) and .pdf extension
                    arxiv_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
                    arxiv_id = arxiv_id.replace(".pdf", "")
                    return arxiv_id.rstrip("/")
        return None

    @staticmethod
    def _paper_to_candidate(paper: dict) -> SourceCandidate:
        """Convert S2 paper → SourceCandidate."""
        # External IDs
        ext_ids = paper.get("externalIds") or {}
        doi = ext_ids.get("DOI")
        arxiv_id = ext_ids.get("ArXiv")

        # Title
        title = paper.get("title")

        # Authors
        authors: list[str] = []
        for a in paper.get("authors") or []:
            name = a.get("name")
            if name:
                authors.append(name)

        # Year
        year = paper.get("year")
        year_str = str(year) if year else None

        # Venue
        venue = paper.get("venue")

        # URL
        url = paper.get("url")

        return SourceCandidate(
            source_name="semantic_scholar",
            doi=doi.lower() if doi else None,
            title=title,
            authors=authors,
            year=year_str,
            venue=venue,
            url=url,
            external_ids={
                k: v
                for k, v in ext_ids.items()
                if k in ("DOI", "ArXiv", "MAG", "PMID", "PMCID")
            },
        )