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

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient
from integrity_checker.retrieval.normalization import title_similarity

logger = get_logger(__name__)

MIN_TITLE_SIMILARITY = 0.55


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
        max_retries: int | None = None,
        api_key: str | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        settings = get_settings()
        self.contact_email = (
            contact_email
            or os.getenv("CONTACT_EMAIL", "")
            or settings.contact_email
            or settings.retrieval.contact_email
        )
        self.max_retries = max_retries or settings.retrieval.retry.max_attempts
        self._backoff = settings.retrieval.retry.backoff
        self._last_status_code: int | None = None

        # Get API key from env or settings
        self.api_key = api_key or os.environ.get("OPENALEX_API_KEY", "")

        self._headers = {
            "User-Agent": (
                f"EssayIntegrityChecker/0.1 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/0.1"
            ),
        }

        # Add Authorization header if API key is available
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup bằng DOI exact; fallback bằng search.

        OpenAlex DOI URL convention: https://api.openalex.org/works/doi:{doi}
        Falls back to /works?search={title} nếu không có DOI.
        """
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
                    error=f"OpenAlex: rate limited (429) for DOI '{doi_norm}'",
                )

        # 2. Title-based search
        return await self._lookup_by_search(citation)

    async def _lookup_by_doi(
        self,
        doi: str,
        citation: Citation | None = None,
    ) -> SourceCandidate | None:
        """GET /works/doi:{doi}."""
        path = f"/works/doi:{doi}"
        data = await self._fetch_json_with_retry(path)
        if not data:
            return None
        cand = self._work_to_candidate(data)
        if not cand.doi and not cand.title:
            return None
        # Guard against OpenAlex resolving an arXiv/external DOI to an unrelated work DOI
        if cand.doi and cand.doi.lower() != doi.lower():
            if citation and citation.title and cand.title:
                if title_similarity(citation.title, cand.title) < 0.75:
                    return None
            else:
                return None
        cand.found = True
        cand.confidence = 1.0
        return cand

    def _pick_best_search_result(
        self,
        results: list[dict],
        query_title: str,
    ) -> tuple[SourceCandidate | None, dict | None, float]:
        """Select the result from OpenAlex /works list with the highest title similarity."""
        best_cand: SourceCandidate | None = None
        best_raw: dict | None = None
        best_sim = -1.0
        for item in results:
            cand = self._work_to_candidate(item)
            sim = title_similarity(query_title, cand.title) if cand.title else 0.0
            if sim > best_sim:
                best_sim = sim
                best_cand = cand
                best_raw = item
        return best_cand, best_raw, best_sim

    async def _lookup_by_search(self, citation: Citation) -> SourceCandidate:
        """GET /works?search={title}&per_page=5."""
        if not citation.title:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="OpenAlex: no title for search",
            )

        # Truncate title để URL không quá dài
        title = citation.title[:200]
        params: dict[str, Any] = {"search": title, "per_page": 5}

        # Thêm filter nếu có year
        filters: list[str] = []
        if citation.year:
            filters.append(f"publication_year:{citation.year}")
        if filters:
            params["filter"] = ",".join(filters)

        data = await self._fetch_json_with_retry("/works", params=params)
        if not data:
            if self._last_status_code == 429:
                return SourceCandidate(
                    source_name=self.name,
                    found=False,
                    error=f"OpenAlex: rate limited (429) for '{title[:60]}'",
                )
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"OpenAlex: no response for '{title[:60]}'",
            )

        results = data.get("results") or []
        best_cand, best_raw, best_sim = self._pick_best_search_result(results, citation.title)

        # Fallback without year filter if strict publication_year filter missed or returned wrong/derivative paper
        if "filter" in params and (best_cand is None or best_sim < 0.90):
            unfiltered_data = await self._fetch_json_with_retry(
                "/works",
                params={"search": title, "per_page": 5},
            )
            if unfiltered_data:
                unfiltered_results = unfiltered_data.get("results") or []
                alt_cand, alt_raw, alt_sim = self._pick_best_search_result(
                    unfiltered_results, citation.title
                )
                if alt_cand is not None and alt_sim > best_sim:
                    results = unfiltered_results
                    best_cand, best_raw, best_sim = alt_cand, alt_raw, alt_sim

        if not results or best_cand is None or best_raw is None:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"OpenAlex: no results for '{title[:60]}'",
            )

        if best_sim < MIN_TITLE_SIMILARITY:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"OpenAlex: no title match ({best_sim:.2f}) for '{title[:60]}'",
            )

        best_cand.found = True
        # Confidence: relevance_score 0–∞, normalize về 0–1 (kèm kiểm tra title_similarity)
        relevance = float(best_raw.get("relevance_score", 0) or 0)
        best_cand.score = relevance
        base_conf = min(relevance, 1.0) if relevance > 0 else 0.75
        if best_sim < 0.85:
            best_cand.confidence = round(base_conf * best_sim, 4)
        else:
            best_cand.confidence = base_conf
        return best_cand

    async def _fetch_json_with_retry(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict | None:
        """GET với tenacity retry + exponential backoff.

        Backoff config: initial=5s, max=60s, multiplier=2.0 (từ settings)
        """
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
                            url, headers=self._headers, params=params or {}
                        )
                        self._last_status_code = resp.status_code
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
        if d.startswith("https://doi.org/"):
            d = d[16:].strip()
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