"""Active HTTP link liveness validator for citation URLs (Phase 3).

Distinguishes between:
- ALIVE (HTTP 200..399)
- RESTRICTED_ALIVE (HTTP 401, 403, 405, 429 — publisher paywall / anti-bot protection)
- DEAD_LINK (HTTP 404, 410, or DNS/connection failure)
- FAKE_DOMAIN (example.com, test.com, localhost, etc.)
- UNCHECKED (no URL provided, or transient timeout)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx

from integrity_checker.logic.rules import _is_fake_url
from integrity_checker.logging import get_logger

logger = get_logger(__name__)


class LinkStatus(str, Enum):
    """Normalized liveness status for a citation URL."""

    ALIVE = "alive"
    RESTRICTED_ALIVE = "restricted_alive"
    DEAD_LINK = "dead_link"
    FAKE_DOMAIN = "fake_domain"
    UNCHECKED = "unchecked"


@dataclass
class LinkCheckResult:
    """Result of validating a single URL."""

    url: str
    status: LinkStatus
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """True if the URL resolves to a live or paywall-protected scholarly page."""
        return self.status in (LinkStatus.ALIVE, LinkStatus.RESTRICTED_ALIVE)

    @property
    def is_broken(self) -> bool:
        """True if the URL is confirmed dead (404/410/DNS failure) or a fake domain."""
        return self.status in (LinkStatus.DEAD_LINK, LinkStatus.FAKE_DOMAIN)


class LinkValidator:
    """Asynchronous HTTP link validator with HEAD-then-GET fallback."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; EssayIntegrityChecker/1.0; "
            "+https://github.com/essay-integrity-checker)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    async def validate_url(self, url: str | None) -> LinkCheckResult:
        """Validate whether a citation URL is reachable and alive."""
        if not url or not str(url).strip():
            return LinkCheckResult(url="", status=LinkStatus.UNCHECKED)

        clean_url = str(url).strip().rstrip(".,;:)\"'")
        is_fake, matched_domain = _is_fake_url(clean_url)
        if is_fake:
            return LinkCheckResult(
                url=clean_url,
                status=LinkStatus.FAKE_DOMAIN,
                error=f"Fake/placeholder domain: {matched_domain}",
            )

        if not clean_url.lower().startswith(("http://", "https://")):
            return LinkCheckResult(url=clean_url, status=LinkStatus.UNCHECKED)

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=self.DEFAULT_HEADERS,
            ) as client:
                resp = await client.head(clean_url)
                status_code = resp.status_code
                final_url = str(resp.url)

                # Many academic publishers reject HEAD with 403/404/405; verify via lightweight GET
                if status_code in (403, 404, 405):
                    async with client.stream("GET", clean_url) as get_resp:
                        status_code = get_resp.status_code
                        final_url = str(get_resp.url)

                return self._classify_status_code(clean_url, status_code, final_url)

        except httpx.TimeoutException as exc:
            logger.debug(f"LinkValidator timeout for '{clean_url}': {exc}")
            return LinkCheckResult(
                url=clean_url,
                status=LinkStatus.UNCHECKED,
                error=f"Timeout: {exc}",
            )
        except httpx.ConnectError as exc:
            logger.debug(f"LinkValidator connect/DNS error for '{clean_url}': {exc}")
            return LinkCheckResult(
                url=clean_url,
                status=LinkStatus.DEAD_LINK,
                error=f"Connection/DNS failed: {exc}",
            )
        except httpx.HTTPError as exc:
            logger.debug(f"LinkValidator HTTP error for '{clean_url}': {exc}")
            return LinkCheckResult(
                url=clean_url,
                status=LinkStatus.UNCHECKED,
                error=f"HTTP error: {exc}",
            )

    @staticmethod
    def _classify_status_code(
        url: str,
        status_code: int,
        final_url: str | None = None,
    ) -> LinkCheckResult:
        if 200 <= status_code < 400:
            return LinkCheckResult(
                url=url,
                status=LinkStatus.ALIVE,
                status_code=status_code,
                final_url=final_url,
            )
        if status_code in (401, 403, 405, 429):
            return LinkCheckResult(
                url=url,
                status=LinkStatus.RESTRICTED_ALIVE,
                status_code=status_code,
                final_url=final_url,
            )
        if status_code in (404, 410):
            return LinkCheckResult(
                url=url,
                status=LinkStatus.DEAD_LINK,
                status_code=status_code,
                final_url=final_url,
                error=f"HTTP {status_code}",
            )
        return LinkCheckResult(
            url=url,
            status=LinkStatus.UNCHECKED,
            status_code=status_code,
            final_url=final_url,
        )
