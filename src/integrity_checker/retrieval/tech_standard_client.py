"""IETF Datatracker RFC & PyPI Package Registry Verification Client.

Verifies technical standards and open-source software packages commonly cited
in Computer Science, Networking, Cybersecurity, and Software Engineering theses:
1. IETF RFC Standards (`RFC 2616`, `RFC 6749`, `RFC 9110`, `10.17487/RFC*`) via
   RFC Editor JSON API & IETF Datatracker REST API v1.
2. Python Package Index (`pypi.org/project/{pkg}`) via PyPI JSON API.

Rate limit: 5 req/s (free public REST APIs, no API key required).
Docs:
- https://www.rfc-editor.org/
- https://datatracker.ietf.org/api/v1/
- https://warehouse.pypa.io/api-reference/json.html
"""

from __future__ import annotations

import html
import os
import re
from typing import Any
from urllib.parse import quote

import httpx

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate
from integrity_checker.retrieval.base import BaseScholarClient
from integrity_checker.retrieval.normalization import normalize_doi

logger = get_logger(__name__)

_RFC_PATTERN = re.compile(
    r"(?:\bRFC\s*[-#:]?\s*(?P<num>\d{3,5})\b|10\.17487/RFC(?P<doi_num>\d{3,5})\b|rfc-editor\.org/rfc/rfc(?P<url_num>\d{3,5})\b|datatracker\.ietf\.org/doc/(?:html/)?rfc(?P<dt_num>\d{3,5})\b)",
    re.IGNORECASE,
)

_PYPI_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?pypi\.org/project/(?P<pkg>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)


class TechStandardClient(BaseScholarClient):
    """IETF RFC & PyPI JSON metadata client for CS / Networking / Software citations."""

    RFC_EDITOR_BASE = "https://www.rfc-editor.org/rfc"
    IETF_API_BASE = "https://datatracker.ietf.org/api/v1/doc/document"
    PYPI_BASE = "https://pypi.org/pypi"
    name = "tech_standard"

    def __init__(
        self,
        contact_email: str | None = None,
        timeout: float = 8.0,
    ) -> None:
        super().__init__(timeout=timeout)
        settings = get_settings()
        self.contact_email = (
            contact_email
            or os.getenv("CONTACT_EMAIL", "")
            or settings.contact_email
            or settings.retrieval.contact_email
        )
        self._headers = {
            "User-Agent": (
                f"EssayIntegrityChecker/1.0 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/1.0"
            ),
            "Accept": "application/json",
        }

    @classmethod
    def extract_rfc_number(cls, citation: Citation) -> int | None:
        """Extract integer RFC number if citation references an IETF RFC standard."""
        combined = " ".join(
            part
            for part in (
                citation.doi or "",
                citation.url or "",
                citation.title or "",
                citation.venue or "",
                citation.raw_text or "",
            )
            if part
        )
        m = _RFC_PATTERN.search(combined)
        if not m:
            return None
        raw_num = m.group("num") or m.group("doi_num") or m.group("url_num") or m.group("dt_num")
        if raw_num and raw_num.isdigit():
            return int(raw_num)
        return None

    @classmethod
    def extract_pypi_package(cls, citation: Citation) -> str | None:
        """Extract PyPI package name if citation references pypi.org."""
        combined = " ".join(
            part
            for part in (citation.url or "", citation.raw_text or "", citation.venue or "")
            if part
        )
        m = _PYPI_URL_PATTERN.search(combined)
        if m:
            return m.group("pkg").strip().rstrip(".,;:)\"'/")
        return None

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Lookup IETF RFC standard or PyPI software package."""
        rfc_num = self.extract_rfc_number(citation)
        if rfc_num is not None:
            rfc_cand = await self._lookup_rfc(rfc_num)
            if rfc_cand and rfc_cand.found:
                return rfc_cand

        pypi_pkg = self.extract_pypi_package(citation)
        if pypi_pkg:
            pypi_cand = await self._lookup_pypi(pypi_pkg)
            if pypi_cand and pypi_cand.found:
                return pypi_cand

        return SourceCandidate(
            source_name=self.name,
            found=False,
            error=f"TechStandard: no results for '{(citation.title or citation.raw_text)[:60]}'",
        )

    async def _lookup_rfc(self, rfc_num: int) -> SourceCandidate | None:
        """Lookup RFC via RFC Editor JSON API first, then IETF Datatracker API."""
        url = f"{self.RFC_EDITOR_BASE}/rfc{rfc_num}.json"
        data = await self._fetch_json(url)
        if isinstance(data, dict) and (data.get("title") or data.get("doc_id")):
            title = self._clean_text(data.get("title"))
            authors = [
                str(a).strip()
                for a in (data.get("authors") or [])
                if str(a).strip()
            ] or ["IETF"]
            pub_date = str(data.get("pub_date") or "")
            yr_m = re.search(r"\b(19|20)\d{2}\b", pub_date)
            year = yr_m.group(0) if yr_m else None
            abstract = self._clean_text(data.get("abstract"))
            doi = normalize_doi(str(data.get("doi") or f"10.17487/rfc{rfc_num}"))

            ext_ids: dict[str, str] = {
                "rfc_number": str(rfc_num),
                "doi": doi or f"10.17487/rfc{rfc_num}",
            }
            obsoleted = data.get("obsoleted_by") or []
            if isinstance(obsoleted, list) and obsoleted:
                ext_ids["obsoleted_by"] = ", ".join(str(x).strip() for x in obsoleted if x)

            return SourceCandidate(
                source_name=self.name,
                found=True,
                doi=doi,
                title=title,
                authors=authors,
                year=year,
                venue=f"IETF RFC {rfc_num}",
                url=f"https://www.rfc-editor.org/rfc/rfc{rfc_num}",
                abstract=abstract,
                external_ids=ext_ids,
                confidence=0.98,
            )

        # Fallback: IETF Datatracker REST API v1
        dt_url = f"{self.IETF_API_BASE}/rfc{rfc_num}/?format=json"
        dt_data = await self._fetch_json(dt_url)
        if isinstance(dt_data, dict) and dt_data.get("title"):
            title = self._clean_text(dt_data.get("title"))
            time_str = str(dt_data.get("time") or "")
            year = time_str[:4] if len(time_str) >= 4 and time_str[:4].isdigit() else None
            abstract = self._clean_text(dt_data.get("abstract"))
            doi = f"10.17487/rfc{rfc_num}"
            return SourceCandidate(
                source_name=self.name,
                found=True,
                doi=doi,
                title=title,
                authors=["IETF"],
                year=year,
                venue=f"IETF RFC {rfc_num}",
                url=f"https://datatracker.ietf.org/doc/html/rfc{rfc_num}",
                abstract=abstract,
                external_ids={"rfc_number": str(rfc_num), "doi": doi},
                confidence=0.95,
            )
        return None

    async def _lookup_pypi(self, pkg_name: str) -> SourceCandidate | None:
        url = f"{self.PYPI_BASE}/{quote(pkg_name, safe='')}/json"
        data = await self._fetch_json(url)
        if not isinstance(data, dict) or not isinstance(data.get("info"), dict):
            return None

        info = data["info"]
        name = str(info.get("name") or pkg_name).strip()
        summary = self._clean_text(info.get("summary"))
        title = f"{name}: {summary}" if summary else name

        authors: list[str] = []
        for field_name in ("author", "maintainer"):
            val = str(info.get(field_name) or "").strip()
            if val and val not in authors:
                authors.append(val)
        if not authors:
            authors = ["PyPI Contributors"]

        # Determine latest release year
        year: str | None = None
        urls_list = data.get("urls") or []
        if isinstance(urls_list, list) and urls_list:
            upload_time = str(urls_list[0].get("upload_time_iso_8601") or urls_list[0].get("upload_time") or "")
            if len(upload_time) >= 4 and upload_time[:4].isdigit():
                year = upload_time[:4]

        pkg_url = str(info.get("package_url") or info.get("project_url") or f"https://pypi.org/project/{name}/")
        return SourceCandidate(
            source_name=self.name,
            found=True,
            doi=None,
            title=title,
            authors=authors,
            year=year,
            venue="Python Package Index (PyPI)",
            url=pkg_url,
            abstract=summary,
            external_ids={"pypi_package": name},
            confidence=0.95,
        )

    @staticmethod
    def _clean_text(text: Any) -> str | None:
        if not text:
            return None
        cleaned = html.unescape(str(text))
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned or None

    async def _fetch_json(self, url: str) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._headers,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"TechStandard request failed for {url}: {exc}")
            return None
