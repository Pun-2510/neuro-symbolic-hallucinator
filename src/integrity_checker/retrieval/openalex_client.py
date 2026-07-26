"""OpenAlex API client — wide coverage, title/author/year search."""

from __future__ import annotations

import os

import httpx

from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient

logger = get_logger(__name__)


class OpenAlexClient(BaseScholarClient):
    """OpenAlex REST API client.

    # TODO(user): tuần 9 — implement GET /works?search=... cho title-based lookup.
        Endpoint hỗ trợ filter: title.search, authorships.author.id, publication_year.
    """

    BASE_URL = "https://api.openalex.org"
    name = "openalex"

    def __init__(self, contact_email: str | None = None, timeout: float = 10.0) -> None:
        super().__init__(timeout=timeout)
        self.contact_email = contact_email or os.getenv("CONTACT_EMAIL", "")
        self._headers = {
            "User-Agent": (
                f"EssayIntegrityChecker/0.1 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/0.1"
            ),
        }

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Stub hiện tại — trả SourceCandidate(found=False)."""
        logger.debug(f"OpenAlex lookup: {citation.raw_text[:80]}")
        return SourceCandidate(
            source_name=self.name,
            found=False,
            error="OpenAlexClient.lookup chưa implement — TODO tuần 9",
        )