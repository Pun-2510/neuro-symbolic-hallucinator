"""SerpApi Google Scholar client — fallback khi các API free thất bại.

Use case: Citation count verification, author lookup, venue ranking.
Không dùng làm nguồn chính vì có rate limits và chi phí.

Rate limit: Tùy gói subscription (100 searches/month free).
Docs: https://serpapi.com/google-scholar-api
"""

from __future__ import annotations

import os
import re

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


class SerpApiClient(BaseScholarClient):
    """SerpApi Google Scholar API client.

    Features:
        - Title search (primary)
        - Author search with author: prefix
        - Year range filtering (as_ylo, as_yhi)
        - Citation count extraction
        - Author profile links

    Usage: Fallback khi Crossref/OpenAlex/Semantic Scholar thất bại.
    """

    BASE_URL = "https://serpapi.com"
    name = "serpapi"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int | None = None,
    ) -> None:
        super().__init__(timeout=timeout)
        settings = get_settings()
        # Priority: explicit api_key > env var > settings
        env_key = os.getenv("SERPAPI_API_KEY", "")
        self.api_key = api_key or env_key or settings.serpapi_api_key
        self.max_retries = max_retries or settings.retrieval.retry.max_attempts
        self._backoff = settings.retrieval.retry.backoff

        if not self.api_key:
            logger.warning("SerpApi: No API key found. Set SERPAPI_API_KEY in .env")

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup paper trên Google Scholar qua SerpApi.

        Flow:
            1. Title search (primary)
            2. Extract citation count, authors, year

        Returns:
            SourceCandidate với found=True nếu tìm thấy kết quả.
        """
        if not self.api_key:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="SerpApi: No API key configured",
            )

        if not citation.title and not citation.authors:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="SerpApi: No title or author for search",
            )

        # Build search query
        query = self._build_search_query(citation)
        if not query:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="SerpApi: Empty search query",
            )

        # Execute search với retry
        result = await self._search_with_retry(query, citation)

        if not result:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"SerpApi: No results for '{query[:60]}'",
            )

        return self._result_to_candidate(result)

    def _build_search_query(self, citation: Citation) -> str:
        """Build Google Scholar search query từ citation.

        Priority: title > author + year > raw text
        """
        if citation.title:
            return citation.title[:300]  # SerpApi query limit

        # Fallback: author + year
        if citation.authors and citation.year:
            first_author = citation.authors[0]
            # Extract last name
            if hasattr(first_author, 'last_name'):
                author_name = first_author.last_name
            else:
                author_name = first_author.split()[-1] if isinstance(first_author, str) else str(first_author)
            return f"{author_name} {citation.year}"

        # Last resort: raw text
        return citation.raw_text[:300] if citation.raw_text else ""

    async def _search_with_retry(
        self,
        query: str,
        citation: Citation,
    ) -> dict | None:
        """Execute SerpApi search với tenacity retry.

        Retry on network errors và temporary failures.
        """
        import asyncio
        from serpapi import GoogleScholarSearch

        retry = AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=self._backoff.multiplier,
                min=self._backoff.initial_seconds,
                max=self._backoff.max_seconds,
            ),
            retry=retry_if_exception_type((Exception,)),
            reraise=False,
        )

        try:
            async for attempt in retry:
                with attempt:
                    # SerpApi client is sync, run in thread pool
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._sync_search,
                        query,
                        citation.year,
                    )
                    return result
            return None
        except RetryError:
            logger.error(f"SerpApi retry exhausted for query: {query[:60]}")
            return None
        except Exception as e:
            logger.error(f"SerpApi error: {e}")
            return None

    def _sync_search(
        self,
        query: str,
        year: str | None = None,
    ) -> dict | None:
        """Sync search wrapper cho asyncio executor.

        Returns:
            First organic_result dict hoặc None.
        """
        from serpapi import GoogleScholarSearch  # Local import

        params: dict = {
            "engine": "google_scholar",
            "q": query,
            "api_key": self.api_key,
        }

        # Add year filter if available
        if year:
            year_int = int(year) if year.isdigit() else None
            if year_int:
                params["as_ylo"] = str(max(1900, year_int - 1))
                params["as_yhi"] = str(min(2030, year_int + 1))

        try:
            search = GoogleScholarSearch(params)
            data = search.get_dict()

            # Check for API errors
            if "search_metadata" in data:
                status = data["search_metadata"].get("status")
                if status != "Success":
                    error_msg = data.get("error", "Unknown SerpApi error")
                    logger.warning(f"SerpApi status={status}: {error_msg}")
                    return None

            # Get first organic result
            organic = data.get("organic_results", [])
            if organic:
                return organic[0]

            return None

        except Exception as e:
            logger.error(f"SerpApi sync search failed: {e}")
            return None

    @staticmethod
    def _result_to_candidate(result: dict) -> SourceCandidate:
        """Convert SerpApi organic_result → SourceCandidate.

        Extracts:
            - Title, snippet
            - Authors (from publication_info)
            - Citation count (from cited_by)
            - Year (from snippet if present)
            - Result ID (for cite link)
        """
        # Title
        title = result.get("title")

        # Result ID - unique identifier from SerpApi
        result_id = result.get("result_id")

        # Publication info
        pub_info = result.get("publication_info", {})
        summary = pub_info.get("summary", "")

        # Authors
        authors: list[str] = []
        for a in pub_info.get("authors", []) or []:
            name = a.get("name")
            if name:
                authors.append(name)

        # Alternative: extract from summary
        # Summary format: "Author1, Author2 - Year - Venue" hoặc "Author1 - Year"
        if not authors and summary:
            author_part = summary.split(" - ")[0] if " - " in summary else summary
            # Split by comma or "and"
            for part in author_part.replace(" and ", ", ").split(","):
                part = part.strip()
                if part and len(part) < 50:  # Filter out venue info
                    authors.append(part)

        # Year - try to extract from snippet, title, or summary
        # Priority: snippet > summary > title
        year: str | None = None
        text_sources = [
            result.get("snippet", ""),
            summary,
            result.get("title", ""),
        ]

        for text in text_sources:
            if text:
                year_match = re.search(r"\b(19|20)\d{2}\b", text)
                if year_match:
                    year = year_match.group(0)
                    break

        # Citation count
        cited_by = result.get("cited_by", {})
        citation_count = 0
        if isinstance(cited_by, dict):
            citation_count = cited_by.get("total", 0)
        elif isinstance(cited_by, int):
            citation_count = cited_by

        # Links
        links = result.get("links", []) or []
        link = links[0].get("link") if links else None

        # SerpApi cite link
        serpapi_cite_link = result.get("serpapi_cite_link", "")

        return SourceCandidate(
            source_name="serpapi",
            found=True,
            title=title,
            authors=authors,
            year=year,
            url=link,
            external_ids={
                "serpapi_result_id": result_id or "",
                "serpapi_cite_link": serpapi_cite_link or "",
                "citation_count": str(citation_count) if citation_count else "",
            },
            # SerpApi không trả DOI/venue trực tiếp → confidence thấp
            confidence=0.5,
        )
