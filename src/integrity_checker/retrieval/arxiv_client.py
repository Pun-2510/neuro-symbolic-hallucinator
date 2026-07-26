"""arXiv API client — preprint CS/engineering.

Dùng SDK `arxiv` (sync) wrap trong executor để không block event loop.
Rate limit: 3 req/s theo guideline của arXiv.
"""

from __future__ import annotations

import asyncio

from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient

logger = get_logger(__name__)


class ArxivClient(BaseScholarClient):
    """arXiv API client qua SDK `arxiv`.

    # TODO(user): tuần 10 — implement search với:
        - query = f'ti:{title} AND au:{last_name}'
        - max_results = 5
        - sort_by = arxiv.SortCriterion.Relevance
    """

    name = "arxiv"

    def __init__(self, timeout: float = 15.0) -> None:
        super().__init__(timeout=timeout)

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Stub hiện tại — trả SourceCandidate(found=False)."""
        logger.debug(f"arXiv lookup: {citation.raw_text[:80]}")
        return SourceCandidate(
            source_name=self.name,
            found=False,
            error="ArxivClient.lookup chưa implement — TODO tuần 10",
        )

    async def _search_sync(self, query: str, max_results: int = 5) -> list[dict]:
        """Wrap sync arxiv search trong executor."""
        try:
            import arxiv  # type: ignore
        except ImportError as e:
            logger.error(f"arxiv SDK chưa cài: {e}")
            return []

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._do_sync_search,
            arxiv,
            query,
            max_results,
        )

    def _do_sync_search(self, arxiv_mod: Any, query: str, max_results: int) -> list[dict]:
        client = arxiv_mod.Client()
        search = arxiv_mod.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv_mod.SortCriterion.Relevance,
        )
        return [
            {
                "title": r.title,
                "authors": [a.name for a in r.authors],
                "year": str(r.published.year) if r.published else None,
                "doi": r.doi,
                "url": r.entry_id,
            }
            for r in client.results(search)
        ]


# Avoid unused-import warning for Any
from typing import Any  # noqa: E402