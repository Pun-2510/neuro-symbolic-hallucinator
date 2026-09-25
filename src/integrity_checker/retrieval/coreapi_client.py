"""CORE API client — open access research paper metadata.

Docs: https://api.core.ac.uk/docs/v3
Rate limit: 100 req/s với API key.

CORE API cung cấp metadata cho:
- Preprints (arXiv, bioRxiv, etc.)
- Conference papers
- Journal articles
- Institutional repositories
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

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient

logger = get_logger(__name__)


class CoreAPIClient(BaseScholarClient):
    """CORE API v3 client.

    Implements:
        - DOI exact lookup (GET /works/search?doi={doi})
        - Title/author search (GET /works/search)
        - Tenacity retry + exponential backoff
        - API key authentication
    """

    BASE_URL = "https://api.core.ac.uk/api/v3"
    name = "coreapi"

    def __init__(
        self,
        api_key: str | None = None,
        contact_email: str | None = None,
        timeout: float = 10.0,
        max_retries: int | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        settings = get_settings()

        # Get API key from param, env, or settings
        self.api_key = api_key or os.getenv("COREAPI_API_KEY", "") or settings.coreapi_api_key

        self.contact_email = contact_email or settings.retrieval.contact_email
        self.max_retries = max_retries or settings.retrieval.retry.max_attempts
        self._backoff = settings.retrieval.retry.backoff

        self._headers: dict[str, str] = {
            "User-Agent": (
                f"EssayIntegrityChecker/1.0 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/1.0"
            ),
        }

        # Add Authorization header if API key is available
        # CORE API uses "CORE <api-key>" format
        if self.api_key:
            self._headers["Authorization"] = f"CORE {self.api_key}"

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup bằng DOI exact; fallback bằng title/author search."""
        # 1. DOI exact lookup
        if citation.doi:
            doi_norm = self._normalize_doi(citation.doi)
            result = await self._lookup_by_doi(doi_norm)
            if result and result.found:
                return result

        # 2. Title + author search
        return await self._lookup_by_search(citation)

    async def _lookup_by_doi(self, doi: str) -> SourceCandidate | None:
        """Search by DOI via CORE API.

        Uses the search endpoint with DOI filter.
        """
        params = {
            "q": f"doi:{doi}",
            "limit": 5,
        }

        data = await self._fetch_json("/works/search", params=params)
        if not data:
            return None

        results = data.get("results", [])
        if not results:
            return None

        # Filter to exact DOI match
        for work in results:
            work_doi = self._extract_doi(work)
            if work_doi and work_doi.lower() == doi.lower():
                cand = self._work_to_candidate(work)
                cand.found = True
                cand.confidence = 1.0
                return cand

        return None

    async def _lookup_by_search(self, citation: Citation) -> SourceCandidate:
        """Search by title and author via CORE API."""
        if not citation.title:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="CoreAPI: no title for search",
            )

        # Build search query
        query_parts = []

        # Title search
        title = citation.title.strip()[:200]
        query_parts.append(title)

        # Add first author last name if available
        if citation.authors and citation.authors[0].last_name:
            query_parts.append(citation.authors[0].last_name)

        # Add year if available
        if citation.year:
            query_parts.append(str(citation.year))

        search_query = " ".join(query_parts)

        params = {
            "q": search_query,
            "limit": 5,  # Get a few results to find best match
        }

        data = await self._fetch_json("/works/search", params=params)
        if not data:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"CoreAPI: no response for '{title[:60]}'",
            )

        results = data.get("results", [])
        if not results:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"CoreAPI: no results for '{title[:60]}'",
            )

        # Return best match (first result with high similarity)
        top = results[0]
        cand = self._work_to_candidate(top)
        cand.found = True
        cand.confidence = 0.7  # Search match, not exact
        return cand

    async def _fetch_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict | None:
        """GET với tenacity retry + exponential backoff."""
        url = f"{self.BASE_URL}{path}"

        retry = AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self._backoff.multiplier,
                min=self._backoff.initial_seconds,
                max=self._backoff.max_seconds,
            ),
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
                            url,
                            headers=self._headers,
                            params=params or {},
                        )

                        if resp.status_code == 401:
                            logger.error("CoreAPI: Invalid API key")
                            return None
                        if resp.status_code == 403:
                            logger.error("CoreAPI: Forbidden - check API key permissions")
                            return None
                        if resp.status_code == 404:
                            return None
                        if resp.status_code == 429:
                            logger.warning("CoreAPI: Rate limited (429)")
                            raise httpx.HTTPError("Rate limited")
                        if resp.status_code >= 500:
                            logger.warning(f"CoreAPI {resp.status_code}: {url}")
                            resp.raise_for_status()

                        if resp.status_code != 200:
                            logger.warning(f"CoreAPI {resp.status_code}: {url}")
                            return None

                        return resp.json()
            return None

        except RetryError:
            logger.error(f"CoreAPI retry exhausted: {url}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"CoreAPI HTTP error: {e}")
            return None

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI: lowercase, strip 'doi:' prefix, strip trailing period."""
        d = doi.strip().lower()
        if d.startswith("doi:"):
            d = d[4:].strip()
        if d.startswith("https://doi.org/"):
            d = d[16:].strip()
        return d.rstrip(".")

    @staticmethod
    def _extract_doi(work: dict) -> str | None:
        """Extract DOI from work record."""
        # Check doi field
        doi = work.get("doi")
        if doi:
            return doi.lower()

        # Check downloadUrl if it contains doi.org
        download_url = work.get("downloadUrl") or work.get("url")
        if download_url and "doi.org/" in download_url:
            return download_url.split("doi.org/")[-1].lower()

        return None

    @staticmethod
    def _work_to_candidate(work: dict) -> SourceCandidate:
        """Convert CORE API work response → SourceCandidate."""
        # DOI
        doi = CoreAPIClient._extract_doi(work)

        # Title
        title = work.get("title") or work.get("name")

        # Authors
        authors: list[str] = []
        for auth in work.get("authors", []) or []:
            name = auth.get("name") or auth.get("raw_name")
            if name:
                authors.append(name)

        # Year
        year = work.get("year") or work.get("published_date")
        if year:
            if isinstance(year, str):
                # Extract year from date string
                import re
                m = re.search(r"\b(19|20)\d{2}\b", year)
                year = m.group(0) if m else None
        year_str = str(year) if year else None

        # Venue
        venue = work.get("venue") or work.get("container_title")

        # URL
        url = work.get("downloadUrl") or work.get("url") or work.get("id")

        # External IDs
        external_ids: dict[str, str] = {}
        if doi:
            external_ids["doi"] = doi

        arxiv_id = work.get("arxivId") or work.get("arxiv_id")
        if arxiv_id:
            external_ids["arxiv"] = arxiv_id

        return SourceCandidate(
            source_name="coreapi",
            doi=doi,
            title=title,
            authors=authors,
            year=year_str,
            venue=venue,
            url=url,
            external_ids=external_ids,
        )
