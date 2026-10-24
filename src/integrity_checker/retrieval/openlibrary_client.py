"""OpenLibrary + Google Books API client — Academic books, textbooks, O'Reilly/monographs.

Docs:
    - OpenLibrary: https://openlibrary.org/dev/docs/api/search
    - Google Books: https://developers.google.com/books/docs/v1/using
No API key required. Resolves ISBNs, multi-edition textbooks (e.g., O'Reilly,
Pearson, Wiley, Springer, Cambridge/MIT/Oxford Press), and edition publication years.
"""

from __future__ import annotations

import asyncio
import os
import re
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
from integrity_checker.retrieval.normalization import (
    author_key,
    title_similarity,
)

logger = get_logger(__name__)

MIN_TITLE_SIMILARITY = 0.60

_EDITION_SUFFIX_RE = re.compile(
    r"(?:[,\s—–-]+|\s*\()?(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|revised|updated|international)\s+(?:ed\.?|edition)\)?\.?$",
    re.IGNORECASE,
)
_ISBN_RE = re.compile(
    r"\b(?:ISBN(?:-1[03])?\s*[:\s]?\s*)?(97[89][-\s]?(?:\d[-\s]?){9}\d|(?:\d[-\s]?){9}[\dXx])\b",
    re.IGNORECASE,
)

_OPENLIB_LOOP_SEMS: dict[int, asyncio.Semaphore] = {}


def _get_openlib_sem() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    loop_id = id(loop)
    if loop_id not in _OPENLIB_LOOP_SEMS:
        _OPENLIB_LOOP_SEMS[loop_id] = asyncio.Semaphore(2)
    return _OPENLIB_LOOP_SEMS[loop_id]


class OpenLibraryClient(BaseScholarClient):
    """OpenLibrary + Google Books fallback client for books and multi-edition textbooks."""

    BASE_URL = "https://openlibrary.org/search.json"
    GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
    name = "openlibrary"

    def __init__(
        self,
        contact_email: str | None = None,
        timeout: float = 12.0,
        max_retries: int | None = None,
        enable_google_books_fallback: bool = True,
    ) -> None:
        super().__init__(timeout=timeout)
        settings = get_settings()
        self.contact_email = (
            contact_email
            or os.getenv("CONTACT_EMAIL", "")
            or settings.contact_email
            or settings.retrieval.contact_email
        )
        self.max_retries = max_retries or min(settings.retrieval.retry.max_attempts, 3)
        self._backoff = settings.retrieval.retry.backoff
        self.enable_google_books_fallback = enable_google_books_fallback
        self._last_status_code: int | None = None
        self._headers = {
            "User-Agent": (
                f"EssayIntegrityChecker/0.2 (mailto:{self.contact_email})"
                if self.contact_email
                else "EssayIntegrityChecker/0.2"
            ),
            "Accept": "application/json",
        }

    @classmethod
    def strip_edition_suffix(cls, title: str) -> str:
        """Strip trailing ', 5th Edition' / '(7th ed.)' from a book title."""
        cleaned = (title or "").strip()
        cleaned = _EDITION_SUFFIX_RE.sub("", cleaned).strip(" ,.;:-–—()")
        return cleaned or (title or "").strip()

    @classmethod
    def extract_isbn(cls, citation: Citation) -> str | None:
        """Extract normalized 10 or 13 digit ISBN from citation raw_text or venue."""
        for text in (citation.raw_text or "", citation.venue or "", citation.url or ""):
            if not text or ("isbn" not in text.lower() and not re.search(r"\b97[89][-\s\d]{10,16}\b", text)):
                continue
            m = _ISBN_RE.search(text)
            if m:
                isbn_clean = re.sub(r"[-\s]", "", m.group(1)).upper()
                if len(isbn_clean) in (10, 13):
                    return isbn_clean
        return None

    async def lookup(self, citation: Citation) -> SourceCandidate:
        """Search OpenLibrary (and Google Books fallback) for book/monograph citations."""
        self._last_status_code = None

        raw_title = (citation.title or "").strip()
        clean_title = self.strip_edition_suffix(raw_title)
        isbn = self.extract_isbn(citation)

        if not clean_title and not isbn:
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error="OpenLibrary: no title or ISBN for book lookup",
            )

        candidates: list[SourceCandidate] = []

        # 1. OpenLibrary lookup (use `q` so books with colon-split title + subtitle are matched)
        ol_params: dict[str, Any] = {
            "limit": 5,
            "fields": "key,title,subtitle,author_name,first_publish_year,publish_year,isbn,publisher",
        }
        if isbn:
            ol_params["isbn"] = isbn
        else:
            surname = author_key(citation.authors[0]) if citation.authors else ""
            ol_params["q"] = f"{clean_title} {surname}".strip() if surname else clean_title

        ol_data = await self._fetch_json_with_retry(self.BASE_URL, params=ol_params)
        if ol_data and isinstance(ol_data.get("docs"), list):
            docs = ol_data["docs"]
            # If title+author was too strict, retry with title only
            if not docs and not isbn and citation.authors and clean_title:
                ol_params_no_author = {**ol_params, "q": clean_title}
                ol_data_retry = await self._fetch_json_with_retry(
                    self.BASE_URL, params=ol_params_no_author
                )
                if ol_data_retry and isinstance(ol_data_retry.get("docs"), list):
                    docs = ol_data_retry["docs"]

            for doc in docs:
                if isinstance(doc, dict):
                    cand = self._doc_to_candidate(doc, citation=citation)
                    if cand.title:
                        candidates.append(cand)

        # Check best OpenLibrary similarity before deciding whether to call Google Books
        best_cand, best_sim = self._select_best_candidate(candidates, citation)

        # 2. Google Books fallback when OpenLibrary missed (< MIN_TITLE_SIMILARITY)
        if (
            self.enable_google_books_fallback
            and best_sim < MIN_TITLE_SIMILARITY
            and (clean_title or isbn)
        ):
            gb_cands = await self._search_google_books(clean_title, isbn, citation)
            if gb_cands:
                candidates.extend(gb_cands)
                best_cand, best_sim = self._select_best_candidate(candidates, citation)

        if best_cand is None or best_sim < MIN_TITLE_SIMILARITY:
            if self._last_status_code == 429:
                return SourceCandidate(
                    source_name=self.name,
                    found=False,
                    error=f"OpenLibrary: rate limited (429) for '{clean_title[:50]}'",
                )
            return SourceCandidate(
                source_name=self.name,
                found=False,
                error=(
                    f"OpenLibrary: no results above {MIN_TITLE_SIMILARITY:.2f} "
                    f"(best={best_sim:.2f}) for '{clean_title[:60]}'"
                ),
            )

        best_cand.found = True
        best_cand.score = best_sim
        best_cand.confidence = min(0.95, max(0.65, best_sim))
        return best_cand

    @classmethod
    def _select_best_candidate(
        cls,
        candidates: list[SourceCandidate],
        citation: Citation,
    ) -> tuple[SourceCandidate | None, float]:
        if not candidates:
            return None, -1.0

        raw_query_title = citation.title or ""
        clean_query_title = cls.strip_edition_suffix(raw_query_title)
        cit_year = str(citation.year)[:4] if citation.year else None
        cit_first_author = author_key(citation.authors[0]) if citation.authors else None

        best_cand: SourceCandidate | None = None
        best_sim = -1.0
        best_rank = -1.0

        for cand in candidates:
            if not cand.title:
                continue
            cand_clean_title = cls.strip_edition_suffix(cand.title)
            sim_raw = title_similarity(raw_query_title, cand.title) if raw_query_title else 0.0
            sim_clean = (
                title_similarity(clean_query_title, cand_clean_title)
                if clean_query_title
                else 0.0
            )
            # Also check base title before colon if candidate or query has a long subtitle
            sim_base = 0.0
            if ":" in cand_clean_title or ":" in clean_query_title:
                cand_base = cand_clean_title.split(":", 1)[0].strip()
                query_base = clean_query_title.split(":", 1)[0].strip()
                if len(cand_base) >= 8 and len(query_base) >= 8:
                    sim_base = title_similarity(query_base, cand_base) * 0.96

            sim = max(sim_raw, sim_clean, sim_base)
            rank = sim

            if cit_year and cand.year == cit_year:
                rank += 0.04
            if cit_first_author and cand.authors:
                cand_authors = {author_key(a) for a in cand.authors if a}
                if cit_first_author in cand_authors:
                    rank += 0.08
                else:
                    rank -= 0.25

            if rank > best_rank:
                best_rank = rank
                best_sim = sim
                best_cand = cand

        return best_cand, best_sim

    @classmethod
    def _doc_to_candidate(
        cls,
        doc: dict[str, Any],
        citation: Citation | None = None,
    ) -> SourceCandidate:
        base_title = str(doc.get("title") or "").strip()
        subtitle = str(doc.get("subtitle") or "").strip()
        full_title = f"{base_title}: {subtitle}" if base_title and subtitle else base_title

        # Choose title representation that best aligns with citation title
        chosen_title = base_title
        if citation and citation.title and full_title != base_title:
            clean_cit = cls.strip_edition_suffix(citation.title)
            if title_similarity(clean_cit, full_title) > title_similarity(clean_cit, base_title):
                chosen_title = full_title

        raw_authors = doc.get("author_name") or []
        authors = [str(a).strip() for a in raw_authors if a and str(a).strip()]

        # Edition-aware year resolution: OpenLibrary provides `publish_year` for all editions!
        cit_year_int: int | None = None
        if citation and citation.year and str(citation.year)[:4].isdigit():
            cit_year_int = int(str(citation.year)[:4])

        pub_years_raw = doc.get("publish_year") or []
        pub_years = sorted(
            {
                int(y)
                for y in pub_years_raw
                if isinstance(y, (int, str)) and str(y).isdigit() and 1800 <= int(y) <= 2030
            }
        )
        first_year = doc.get("first_publish_year")
        if isinstance(first_year, (int, str)) and str(first_year).isdigit():
            fy = int(first_year)
            if fy not in pub_years:
                pub_years.insert(0, fy)

        resolved_year: str | None = None
        if cit_year_int is not None and pub_years:
            # Check exact edition year match first, then ±1 year tolerance
            if cit_year_int in pub_years:
                resolved_year = str(cit_year_int)
            else:
                closest = min(pub_years, key=lambda y: abs(y - cit_year_int))
                if abs(closest - cit_year_int) <= 1:
                    resolved_year = str(closest)

        if resolved_year is None:
            if first_year:
                resolved_year = str(first_year)[:4]
            elif pub_years:
                resolved_year = str(pub_years[-1])

        publishers = doc.get("publisher") or []
        venue = str(publishers[0]).strip() if isinstance(publishers, list) and publishers else None

        key = str(doc.get("key") or "").strip()
        url = f"https://openlibrary.org{key}" if key.startswith("/") else None

        external_ids: dict[str, str] = {}
        if key:
            external_ids["openlibrary"] = key
        isbns = doc.get("isbn") or []
        if isinstance(isbns, list) and isbns:
            external_ids["isbn"] = str(isbns[0])

        return SourceCandidate(
            source_name=cls.name,
            found=False,
            doi=None,
            title=chosen_title or None,
            authors=authors,
            year=resolved_year,
            venue=venue,
            url=url,
            external_ids=external_ids,
        )

    async def _search_google_books(
        self,
        clean_title: str,
        isbn: str | None,
        citation: Citation,
    ) -> list[SourceCandidate]:
        if isbn:
            q = f"isbn:{isbn}"
        else:
            q = f'intitle:"{clean_title}"'
            if citation.authors:
                surname = author_key(citation.authors[0])
                if surname:
                    q += f"+inauthor:{surname}"

        data = await self._fetch_json_with_retry(
            self.GOOGLE_BOOKS_URL,
            params={"q": q, "maxResults": 5},
        )
        items = data.get("items") if isinstance(data, dict) else None
        if not items and not isbn and citation.authors:
            # Retry without strict intitle quotes
            surname = author_key(citation.authors[0]) or ""
            q_fallback = f"{clean_title} {surname}".strip()
            data = await self._fetch_json_with_retry(
                self.GOOGLE_BOOKS_URL,
                params={"q": q_fallback, "maxResults": 5},
            )
            items = data.get("items") if isinstance(data, dict) else None

        if not isinstance(items, list):
            return []

        results: list[SourceCandidate] = []
        for item in items:
            vol = item.get("volumeInfo") if isinstance(item, dict) else None
            if not isinstance(vol, dict):
                continue
            base_title = str(vol.get("title") or "").strip()
            subtitle = str(vol.get("subtitle") or "").strip()
            full_title = f"{base_title}: {subtitle}" if base_title and subtitle else base_title

            chosen_title = base_title
            if citation.title and full_title != base_title:
                clean_cit = self.strip_edition_suffix(citation.title)
                if title_similarity(clean_cit, full_title) > title_similarity(clean_cit, base_title):
                    chosen_title = full_title

            authors = [str(a).strip() for a in (vol.get("authors") or []) if a]
            pub_date = str(vol.get("publishedDate") or "").strip()
            year = pub_date[:4] if len(pub_date) >= 4 and pub_date[:4].isdigit() else None
            publisher = str(vol.get("publisher") or "").strip() or None
            info_link = str(vol.get("infoLink") or "").strip() or None

            ext_ids: dict[str, str] = {}
            if item.get("id"):
                ext_ids["google_books"] = str(item["id"])
            for ident in vol.get("industryIdentifiers") or []:
                if isinstance(ident, dict) and ident.get("identifier"):
                    ext_ids["isbn"] = str(ident["identifier"])
                    break

            if chosen_title:
                results.append(
                    SourceCandidate(
                        source_name=self.name,
                        found=False,
                        doi=None,
                        title=chosen_title,
                        authors=authors,
                        year=year,
                        venue=publisher,
                        url=info_link,
                        external_ids=ext_ids,
                    )
                )
        return results

    async def _fetch_json_with_retry(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        sem = _get_openlib_sem()
        is_google_books = url == self.GOOGLE_BOOKS_URL
        retryer = AsyncRetrying(
            stop=stop_after_attempt(1 if is_google_books else self.max_retries),
            wait=wait_exponential(
                multiplier=self._backoff.multiplier,
                min=min(self._backoff.initial_seconds, 2.0),
                max=min(self._backoff.max_seconds, 15.0),
            ),
            retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
            reraise=False,
        )
        try:
            async with sem:
                async for attempt in retryer:
                    with attempt:
                        async with httpx.AsyncClient(
                            timeout=self.timeout, follow_redirects=True
                        ) as client:
                            resp = await client.get(url, params=params, headers=self._headers)
                        if not is_google_books or self._last_status_code is None:
                            self._last_status_code = resp.status_code
                        if resp.status_code == 404:
                            return None
                        if is_google_books and resp.status_code == 429:
                            logger.debug("Google Books fallback rate limited (429); skipping fallback")
                            return None
                        if resp.status_code == 429 or resp.status_code >= 500:
                            if getattr(resp, "_request", None) is None:
                                resp._request = httpx.Request("GET", url)
                            resp.raise_for_status()
                        if resp.status_code != 200:
                            return None
                        return resp.json()
        except RetryError as exc:
            logger.warning(f"OpenLibrary retry exhausted: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"OpenLibrary error: {exc}")
            return None
        return None
