"""arXiv API client — preprint CS/engineering.

Dùng SDK `arxiv` (sync) wrap trong executor để không block event loop.
Rate limit: 3 req/s theo guideline của arXiv.
Docs: https://arxiv.org/help/api
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

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


class ArxivClient(BaseScholarClient):
    """arXiv API client qua SDK `arxiv`.

    Implements:
        - arXiv ID exact lookup (nếu URL chứa arxiv.org/abs/{id}).
        - Title + first-author search (ti:{title} AND au:{last_name}).
        - Tenacity retry + exponential backoff cho sync SDK wrapped async.
        - Rate limit: 3 req/s (theo arXiv guideline).
    """

    name = "arxiv"

    # arXiv ID format: YYMM.NNNNN(vN)?
    ARXIV_ID_RE = re.compile(r"\b(\d{4}\.\d{4,5})(v\d+)?\b")

    def __init__(self, timeout: float = 15.0, max_retries: int = 3) -> None:
        super().__init__(timeout=timeout)
        self.max_retries = max_retries

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup arXiv bằng ID exact hoặc title+author search."""
        # 1. arXiv ID exact lookup
        arxiv_id = self._extract_arxiv_id(citation)
        if arxiv_id:
            result = await self._lookup_by_id(arxiv_id)
            if result and result.found:
                return result

        # 2. Title + author search
        return await self._lookup_by_search(citation)

    async def _lookup_by_id(self, arxiv_id: str) -> SourceCandidate | None:
        """Lookup bằng arXiv ID exact qua arxiv.Search với id_list."""
        try:
            import arxiv  # type: ignore
        except ImportError:
            logger.error("arxiv SDK chưa cài đặt")
            return None

        async def _do() -> list[dict]:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._do_id_search_sync, arxiv, arxiv_id
            )

        results = await self._with_retry(_do)
        if not results:
            return None
        cand = self._result_to_candidate(results[0])
        cand.found = True
        cand.confidence = 1.0  # ID exact
        return cand

    async def _lookup_by_search(self, citation: Citation) -> SourceCandidate:
        """Search bằng title + author first qua ti:/au:."""
        try:
            import arxiv  # type: ignore
        except ImportError:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="arxiv SDK chưa cài đặt",
            )

        query_parts: list[str] = []
        if citation.title:
            # Wrap title trong quotes nếu có spaces (arXiv supports quoted phrases)
            title = citation.title.strip()
            if title:
                query_parts.append(f'ti:"{title}"')
        if citation.authors and citation.authors[0].last_name:
            query_parts.append(f'au:"{citation.authors[0].last_name}"')

        if not query_parts:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="arXiv: no title/author for search",
            )

        query = " AND ".join(query_parts)

        async def _do() -> list[dict]:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._do_search_sync, arxiv, query
            )

        results = await self._with_retry(_do)
        if not results:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=f"arXiv: no results for '{query[:60]}'",
            )

        top = results[0]
        cand = self._result_to_candidate(top)
        cand.found = True
        cand.confidence = 0.7  # Search match, không exact
        return cand

    async def _with_retry(self, coro_factory) -> list[dict]:
        """Wrap sync SDK call với tenacity retry."""
        retry = AsyncRetrying(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(Exception),  # arxiv SDK raises broadly
            reraise=False,
        )
        try:
            async for attempt in retry:
                with attempt:
                    return await coro_factory()
            return []
        except RetryError as e:
            logger.error(f"arXiv retry exhausted: {e}")
            return []
        except Exception as e:
            logger.error(f"arXiv error: {type(e).__name__}: {e}")
            return []

    @staticmethod
    def _do_id_search_sync(arxiv_mod: Any, arxiv_id: str) -> list[dict]:
        """Sync search theo arXiv ID."""
        client = arxiv_mod.Client(page_size=1, delay_seconds=0.34, num_retries=0)
        search = arxiv_mod.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        return [ArxivClient._result_to_dict(r) for r in results]

    @staticmethod
    def _do_search_sync(arxiv_mod: Any, query: str) -> list[dict]:
        """Sync search theo query."""
        client = arxiv_mod.Client(page_size=5, delay_seconds=0.34, num_retries=0)
        search = arxiv_mod.Search(
            query=query,
            max_results=1,
            sort_by=arxiv_mod.SortCriterion.Relevance,
        )
        results = list(client.results(search))
        return [ArxivClient._result_to_dict(r) for r in results]

    @staticmethod
    def _result_to_dict(r: Any) -> dict:
        """Convert arxiv.Result → dict (for shared extraction)."""
        return {
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "year": str(r.published.year) if r.published else None,
            "doi": r.doi,
            "url": r.entry_id,
            "arxiv_id": r.entry_id.split("/")[-1] if r.entry_id else None,
        }

    @staticmethod
    def _result_to_candidate(d: dict) -> SourceCandidate:
        """Convert result dict → SourceCandidate."""
        # arXiv ID — strip version suffix
        arxiv_id_full = d.get("arxiv_id", "")
        arxiv_id = arxiv_id_full.split("v")[0] if "v" in arxiv_id_full else arxiv_id_full
        # Extract clean ID from entry_id (e.g. http://arxiv.org/abs/2106.12345v1)
        url = d.get("url", "")
        if "arxiv.org" in url and arxiv_id_full not in url:
            # Fallback: parse from URL
            m = re.search(r"(\d{4}\.\d{4,5})", url)
            if m:
                arxiv_id = m.group(1)

        doi = d.get("doi")
        return SourceCandidate(
            source_name="arxiv",
            doi=doi.lower() if doi else None,
            title=d.get("title"),
            authors=d.get("authors", []),
            year=d.get("year"),
            url=url,
            external_ids={"arxiv": arxiv_id} if arxiv_id else {},
        )

    @staticmethod
    def _extract_arxiv_id(citation: Citation) -> str | None:
        """Extract arXiv ID từ URL hoặc raw_text."""
        # 1. URL field — format: https://arxiv.org/abs/2106.12345
        if citation.url and "arxiv.org" in citation.url:
            for marker in ("/abs/", "/pdf/"):
                idx = citation.url.find(marker)
                if idx >= 0:
                    candidate = citation.url[idx + len(marker):]
                    m = ArxivClient.ARXIV_ID_RE.search(candidate)
                    if m:
                        return m.group(1)

        # 2. raw_text field — tìm pattern YYMM.NNNNN
        if citation.raw_text:
            m = ArxivClient.ARXIV_ID_RE.search(citation.raw_text)
            if m:
                return m.group(1)
        return None