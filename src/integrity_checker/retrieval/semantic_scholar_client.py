"""Semantic Scholar API client — supplement với citation graph."""

from __future__ import annotations

import os

import httpx

from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient

logger = get_logger(__name__)


class SemanticScholarClient(BaseScholarClient):
    """Semantic Scholar Graph API client.

    # TODO(user): tuần 10 — implement:
        - GET /paper/search?query=...&fields=title,authors,year,externalIds
        - Optional API key qua S2_API_KEY env (tăng rate limit).
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    name = "semantic_scholar"

    def __init__(self, api_key: str | None = None, timeout: float = 10.0) -> None:
        super().__init__(timeout=timeout)
        self.api_key = api_key or os.getenv("S2_API_KEY", "")
        self._headers = {"x-api-key": self.api_key} if self.api_key else {}

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Stub hiện tại."""
        logger.debug(f"Semantic Scholar lookup: {citation.raw_text[:80]}")
        return SourceCandidate(
            source_name=self.name,
            found=False,
            error="SemanticScholarClient.lookup chưa implement — TODO tuần 10",
        )