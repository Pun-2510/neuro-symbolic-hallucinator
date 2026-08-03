"""OpenAlex API client — wide coverage, title/author/year search.

Rate limit: 10 req/s (polite pool nếu có email).
Docs: https://docs.openalex.org/
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


class OpenAlexClient(BaseScholarClient):
    """OpenAlex REST API client.

    Implements:
        - DOI exact lookup (GET /works/doi:{doi}).
        - Title/author/year search (GET /works?search=...).
        - Tenacity retry + exponential backoff.
        - Polite pool headers với CONTACT_EMAIL.
    """

    BASE_URL = "https://api.openalex.org"
    name = "openalex"

    def __init__(
        self,
        contact_email: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        super().__init__(timeout=timeout)
        self.contact_email = contact_email or os.getenv("CONTACT_EMAIL", "")
        self.max_retries = max_retries
        self._headers = {
            "User-Agent": (
                f"EssayIntegrityChecker/0.1 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/0.1"
            ),
        }

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup bằng DOI exact; fallback bằng search.

        OpenAlex DOI URL convention: https://api.openalex.org/works/doi:{doi}
        Falls back to /works?search={title} nếu không có DOI.
        """
        # 1. DOI exact lookup
        if citation.doi:
            doi_norm = self._normalize_doi(citation.doi)
            result = await self._lookup_by_doi(doi_norm)
            if result and result.found:
                return result

        # 2. Title-based search
        return await self._lookup_by_search(citation)

    async def _lookup_by_doi(self, doi: str) -> SourceCandidate | None:
        """GET /works/doi:{doi}."""
        path = f"/works/doi:{doi}"
        data = await self._fetch_json_with_retry(path)
        if not data:
            return None
        cand = self._work_to_candidate(data)
        if not cand.doi and not cand.title:
            return None
        cand.found = True
        cand.confidence = 1.0
        return cand

    async def _lookup_by_search(self, citation: Citation) -> SourceCandidate:
        """GET /works?search={title}&per_page=1."""
        if not citation.title:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="OpenAlex: no title for search",
            )

        # Truncate title để URL không quá dài
        title = citation.title[:200]
        params = {"search": title, "per_page": 1}

        # Thêm filter nếu có author/year
        filters: list[str] = []
        if citation.year:
            filters.append(f"publication_year:{citation.year}")
        if filters:
            params["filter"] = ",".join(filters)

        data = await self._fetch_json_with_retry("/works", params=params)
        if not data:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"OpenAlex: no response for '{title[:60]}'",
            )

        results = data.get("results") or []
        if not results:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"OpenAlex: no results for '{title[:60]}'",
            )

        top = results[0]
        cand = self._work_to_candidate(top)
        cand.found = True
        # Confidence: relevance_score 0–∞, normalize về 0–1
        relevance = float(top.get("relevance_score", 0) or 0)
        cand.score = relevance
        cand.confidence = min(relevance, 1.0)
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
                                f"OpenAlex {resp.status_code}: {url}"
                            )
                            return None
                        return resp.json()
            return None
        except RetryError:
            logger.error(f"OpenAlex retry exhausted: {url}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"OpenAlex HTTP error: {e}")
            return None

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI: lowercase, strip 'doi:' prefix, strip trailing period."""
        d = doi.strip().lower()
        if d.startswith("doi:"):
            d = d[4:].strip()
        return d.rstrip(".")

    @staticmethod
    def _work_to_candidate(work: dict) -> SourceCandidate:
        """Convert OpenAlex /works response → SourceCandidate."""
        # DOI — strip https://doi.org/ prefix
        doi_raw = work.get("doi") or ""
        doi = doi_raw.replace("https://doi.org/", "").lower() if doi_raw else None

        # Title (OpenAlex dùng 'display_name' hoặc 'title')
        title = work.get("title") or work.get("display_name")

        # Authors — từ 'authorships'
        authors: list[str] = []
        for auth in work.get("authorships") or []:
            author = auth.get("author") or {}
            name = author.get("display_name")
            if name:
                authors.append(name)

        # Year — từ 'publication_year'
        year = work.get("publication_year")
        year_str = str(year) if year else None

        # Venue — từ 'primary_location.source.display_name'
        venue: str | None = None
        loc = work.get("primary_location") or {}
        src = loc.get("source") or {}
        if src:
            venue = src.get("display_name")

        # URL
        url = work.get("id")  # OpenAlex ID URL

        return SourceCandidate(
            source_name="openalex",
            doi=doi,
            title=title,
            authors=authors,
            year=year_str,
            venue=venue,
            url=url,
            external_ids={"doi": doi} if doi else {},
        )