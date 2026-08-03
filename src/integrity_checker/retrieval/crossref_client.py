"""Crossref API client — DOI exact + bibliographic search.

Rate limit: 50 req/s (polite pool nếu có email).
Docs: https://api.crossref.org/swagger-ui/index.html
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

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


class CrossrefClient(BaseScholarClient):
    """Crossref REST API client.

    Implements:
        - DOI exact lookup (GET /works/{doi}).
        - Bibliographic search fallback (GET /works?query.bibliographic=...).
        - Tenacity retry với exponential backoff (429, 5xx, network errors).
        - Polite pool headers (User-Agent có email) nếu CONTACT_EMAIL set.
    """

    BASE_URL = "https://api.crossref.org"
    name = "crossref"

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
        """Lookup bằng DOI exact; fallback bằng bibliographic query.

        Args:
            citation: Citation để tra cứu.

        Returns:
            SourceCandidate với found=True nếu tìm thấy, found=False + error nếu không.
        """
        # 1. DOI exact lookup (priority)
        if citation.doi:
            doi_norm = self._normalize_doi(citation.doi)
            result = await self._lookup_by_doi(doi_norm)
            if result and result.found:
                return result

        # 2. Bibliographic query fallback
        return await self._lookup_by_bibliographic(citation)

    async def _lookup_by_doi(self, doi: str) -> SourceCandidate | None:
        """GET /works/{doi}."""
        if not doi:
            return None
        path = f"/works/{quote(doi, safe='/')}"
        data = await self._fetch_json_with_retry(path)
        if not data:
            return None
        message = data.get("message")
        if not message:
            return None
        cand = self._message_to_candidate(message)
        cand.found = True
        cand.confidence = 1.0  # DOI exact = highest confidence
        return cand

    async def _lookup_by_bibliographic(self, citation: Citation) -> SourceCandidate:
        """GET /works?query.bibliographic=...&rows=1."""
        query = self._build_bibliographic_query(citation)
        if not query:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="Crossref: empty bibliographic query (no title/author/year)",
            )

        params = {"query.bibliographic": query, "rows": 1}
        data = await self._fetch_json_with_retry("/works", params=params)
        if not data:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"Crossref: no response for query '{query[:60]}'",
            )

        items = data.get("message", {}).get("items", [])
        if not items:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"Crossref: no results for '{query[:60]}'",
            )

        top = items[0]
        cand = self._message_to_candidate(top)
        cand.found = True
        # Confidence: heuristic — Crossref score là relevance, không phải similarity.
        # Score 0–∞, normalize về 0–1 với cap.
        score = float(top.get("score", 0) or 0)
        cand.score = score
        cand.confidence = min(score / 100.0, 1.0)
        return cand

    async def _fetch_json_with_retry(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict | None:
        """GET với tenacity retry + exponential backoff.

        Retry on:
            - httpx.HTTPError (network)
            - 429 Too Many Requests
            - 5xx server errors
        """
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
                            # 404 = not found, không retry
                            return None
                        if resp.status_code == 429 or resp.status_code >= 500:
                            # Retry-worthy
                            resp.raise_for_status()
                        if resp.status_code != 200:
                            logger.warning(
                                f"Crossref {resp.status_code}: {url}"
                            )
                            return None
                        return resp.json()
            return None
        except RetryError:
            logger.error(f"Crossref retry exhausted: {url}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"Crossref HTTP error: {e}")
            return None

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI: lowercase, strip 'doi:' prefix, strip trailing period."""
        d = doi.strip().lower()
        if d.startswith("doi:"):
            d = d[4:].strip()
        return d.rstrip(".")

    @staticmethod
    def _build_bibliographic_query(citation: Citation) -> str:
        """Build Crossref query.bibliographic từ citation fields."""
        parts: list[str] = []
        if citation.title:
            parts.append(citation.title)
        if citation.authors:
            # Chỉ lấy last name của author đầu
            last = citation.authors[0].last_name
            if last:
                parts.append(last)
        if citation.year:
            parts.append(citation.year)
        return " ".join(parts) if parts else ""

    @staticmethod
    def _message_to_candidate(message: dict) -> SourceCandidate:
        """Convert Crossref /works/{doi} message → SourceCandidate."""
        # DOI
        doi = message.get("DOI")

        # Title
        titles = message.get("title") or []
        title = titles[0] if titles else None

        # Authors
        authors: list[str] = []
        for a in message.get("author", []) or []:
            given = a.get("given", "")
            family = a.get("family", "")
            full = f"{given} {family}".strip()
            if full:
                authors.append(full)

        # Year — từ published print/online hoặc issued
        year: str | None = None
        for date_key in ("published-print", "published-online", "issued", "created"):
            date_parts = message.get(date_key, {}).get("date-parts", [[None]])
            if date_parts and date_parts[0] and date_parts[0][0]:
                year = str(date_parts[0][0])
                break

        # Venue
        venue: str | None = None
        container = message.get("container-title") or []
        if container:
            venue = container[0]
        elif message.get("short-container-title"):
            venue = message["short-container-title"][0]

        # URL
        url = message.get("URL")

        return SourceCandidate(
            source_name="crossref",
            doi=doi.lower() if doi else None,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            url=url,
            external_ids={"doi": doi.lower()} if doi else {},
        )