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
import re
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
from integrity_checker.retrieval.normalization import title_similarity

logger = get_logger(__name__)

MIN_TITLE_SIMILARITY = 0.55


class CoreAPIClient(BaseScholarClient):
    """CORE API v3 client.

    Implements:
        - DOI exact lookup (GET /search/works/?q=doi:"{doi}")
        - Title/author search (GET /search/works/)
        - Tenacity retry + exponential backoff
        - API key authentication
    """

    BASE_URL = "https://api.core.ac.uk/v3"
    name = "coreapi"

    def __init__(
        self,
        api_key: str | None = None,
        contact_email: str | None = None,
        timeout: float = 15.0,
        max_retries: int | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        settings = get_settings()

        # Get API key from param, env, or settings
        self.api_key = api_key or os.getenv("COREAPI_API_KEY", "") or settings.coreapi_api_key

        self.contact_email = (
            contact_email
            or os.getenv("CONTACT_EMAIL", "")
            or settings.contact_email
            or settings.retrieval.contact_email
        )
        self.max_retries = max_retries or settings.retrieval.retry.max_attempts
        self._backoff = settings.retrieval.retry.backoff
        self._last_status_code: int | None = None

        self._headers: dict[str, str] = {
            "User-Agent": (
                f"EssayIntegrityChecker/1.0 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/1.0"
            ),
        }

        # Add Authorization header if API key is available
        # CORE API v3 uses Bearer <api-key>
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup bằng DOI exact; fallback bằng title/author search."""
        self._last_status_code = None

        # 1. DOI exact lookup
        if citation.doi:
            doi_norm = self._normalize_doi(citation.doi)
            result = await self._lookup_by_doi(doi_norm, citation=citation)
            if result and result.found:
                return result
            if self._last_status_code == 429:
                return SourceCandidate(
                    source_name=self.name,
                    found=False,
                    error=f"CoreAPI: rate limited (429) for DOI '{doi_norm}'",
                )

        # 2. Title + author search
        return await self._lookup_by_search(citation)

    async def _lookup_by_doi(
        self,
        doi: str,
        citation: Citation | None = None,
    ) -> SourceCandidate | None:
        """Search by DOI via CORE API.

        Uses the search endpoint with DOI filter.
        """
        params = {
            "q": f"doi:{doi}",
            "limit": 5,
        }

        data = await self._fetch_json("/search/works/", params=params)
        if not data:
            return None

        results = data.get("results", [])
        if not results:
            return None

        # Filter to exact DOI match; if multiple records share the DOI, pick best title match
        matching_candidates: list[SourceCandidate] = []
        for work in results:
            work_doi = self._extract_doi(work)
            if work_doi and work_doi.lower() == doi.lower():
                cand = self._work_to_candidate(work)
                cand.found = True
                cand.confidence = 1.0
                matching_candidates.append(cand)

        if not matching_candidates:
            return None

        if citation and citation.title and len(matching_candidates) > 1:
            matching_candidates.sort(
                key=lambda c: title_similarity(citation.title, c.title),
                reverse=True,
            )

        return matching_candidates[0]

    @staticmethod
    def _sanitize_query(text: str) -> str:
        """Sanitize Lucene/Elasticsearch special characters that trigger CORE API 500 errors."""
        cleaned = re.sub(r'[:\-\"/\(\)\[\]\{\}\?\*\~\^\\!+&|<>]+', " ", text)
        return " ".join(cleaned.split())

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

        # Title search (sanitized to avoid CORE API 500 on ':' or '-')
        title = citation.title.strip()[:200]
        sanitized_title = self._sanitize_query(title)
        if sanitized_title:
            query_parts.append(sanitized_title)

        # Only append author/year to query string when title is short (< 4 words);
        # for full titles, adding author/year into raw BM25 query dilutes exact title ranking.
        if len(sanitized_title.split()) < 4:
            if citation.authors:
                first_author = citation.authors[0]
                last_name = getattr(first_author, "last_name", None)
                if not last_name and isinstance(first_author, str):
                    last_name = first_author.split(",")[0].strip().split()[-1] if first_author.strip() else None
                if last_name:
                    sanitized_author = self._sanitize_query(str(last_name))
                    if sanitized_author:
                        query_parts.append(sanitized_author)

            if citation.year:
                query_parts.append(str(citation.year))

        search_query = " ".join(query_parts)

        params = {
            "q": search_query,
            "limit": 5,  # Get a few results to find best match
        }

        data = await self._fetch_json("/search/works/", params=params)
        if not data:
            if self._last_status_code == 429:
                return SourceCandidate(
                    source_name=self.name,
                    found=False,
                    error=f"CoreAPI: rate limited (429) for '{title[:60]}'",
                )
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

        # Pick result with highest title similarity
        best_cand: SourceCandidate | None = None
        best_sim = -1.0
        for work in results:
            cand = self._work_to_candidate(work)
            sim = title_similarity(citation.title, cand.title) if cand.title else 0.0
            if sim > best_sim:
                best_sim = sim
                best_cand = cand

        if best_cand is None or best_sim < MIN_TITLE_SIMILARITY:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"CoreAPI: no title match ({best_sim:.2f}) for '{title[:60]}'",
            )

        best_cand.found = True
        best_cand.confidence = 0.7 if best_sim >= 0.85 else round(0.7 * best_sim, 4)
        return best_cand

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
                    async with httpx.AsyncClient(
                        timeout=self.timeout,
                        follow_redirects=True,
                    ) as client:
                        resp = await client.get(
                            url,
                            headers=self._headers,
                            params=params or {},
                        )
                        self._last_status_code = resp.status_code

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
                            return None
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
            return CoreAPIClient._normalize_doi(str(doi))

        # Check identifiers list in CORE v3
        for ident in work.get("identifiers") or []:
            if isinstance(ident, dict) and str(ident.get("type", "")).upper() == "DOI":
                val = ident.get("identifier")
                if val:
                    return CoreAPIClient._normalize_doi(str(val))
            elif isinstance(ident, str) and ident.lower().startswith("doi:"):
                return CoreAPIClient._normalize_doi(ident)

        # Check downloadUrl if it contains doi.org
        download_url = work.get("downloadUrl") or work.get("url")
        if download_url and "doi.org/" in str(download_url):
            return CoreAPIClient._normalize_doi(str(download_url).split("doi.org/")[-1])

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
            if isinstance(auth, dict):
                name = auth.get("name") or auth.get("raw_name")
                if name:
                    authors.append(name)
            elif isinstance(auth, str) and auth.strip():
                authors.append(auth.strip())

        # Year (CORE API v3 uses yearPublished / publishedDate)
        year = (
            work.get("yearPublished")
            or work.get("year")
            or work.get("publishedDate")
            or work.get("published_date")
        )
        if year:
            if isinstance(year, str):
                m = re.search(r"\b(19|20)\d{2}\b", year)
                year = m.group(0) if m else None
        year_str = str(year) if year else None

        # Venue (CORE API v3 uses journals[].title or publisher)
        venue = work.get("venue") or work.get("container_title")
        if not venue:
            journals = work.get("journals") or []
            if journals and isinstance(journals[0], dict):
                venue = journals[0].get("title")
        if not venue:
            venue = work.get("publisher")

        # URL
        raw_url = (
            work.get("downloadUrl")
            or (work.get("sourceFulltextUrls") or [None])[0]
            or work.get("url")
        )
        if not raw_url and work.get("id") is not None:
            work_id = work.get("id")
            raw_url = f"https://core.ac.uk/works/{work_id}" if isinstance(work_id, int) else str(work_id)
        url = str(raw_url) if raw_url else None

        # External IDs
        external_ids: dict[str, str] = {}
        if doi:
            external_ids["doi"] = doi

        arxiv_id = work.get("arxivId") or work.get("arxiv_id")
        if not arxiv_id:
            for ident in work.get("identifiers") or []:
                if isinstance(ident, dict) and str(ident.get("type", "")).upper() == "ARXIV":
                    arxiv_id = ident.get("identifier")
                    break
                elif isinstance(ident, str) and ident.lower().startswith("oai:arxiv.org:"):
                    arxiv_id = ident.split(":")[-1]
                    break
        if arxiv_id:
            external_ids["arxiv"] = str(arxiv_id)

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
