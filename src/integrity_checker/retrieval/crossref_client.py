"""Crossref API client — DOI exact + bibliographic search.

Rate limit: 50 req/s (polite pool nếu có email).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient

logger = get_logger(__name__)


class CrossrefClient(BaseScholarClient):
    """Crossref REST API client.

    # TODO(user): tuần 9 — implement /works/{doi} cho DOI exact lookup
        và fallback /works?query.bibliographic=... cho title-based search.
    """

    BASE_URL = "https://api.crossref.org"
    name = "crossref"

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
        """Lookup bằng DOI exact; fallback bằng bibliographic query.

        Stub hiện tại — trả về SourceCandidate với found=False, không gọi API thật.
        """
        logger.debug(f"Crossref lookup: {citation.raw_text[:80]}")
        return SourceCandidate(
            source_name=self.name,
            found=False,
            error="CrossrefClient.lookup chưa implement — TODO tuần 9",
        )

    async def _fetch_json(self, path: str, params: dict[str, Any] | None = None) -> dict | None:
        """Helper chung cho mọi Crossref call."""
        url = f"{self.BASE_URL}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._headers, params=params or {})
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"Crossref {resp.status_code}: {url}")
                return None
        except httpx.HTTPError as e:
            logger.error(f"Crossref HTTP error: {e}")
            return None