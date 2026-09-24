"""Canonicalization helpers shared by retrieval and local-database lookup.

The extractor intentionally preserves PDF punctuation in ``Citation.title`` and
author fields for auditability.  Retrieval keys must be more forgiving: a final
period, Unicode dash, initials, or ``et al.`` should not turn the same paper
into a cache miss.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from difflib import SequenceMatcher

from integrity_checker.models.citation import Citation

_DOI_PREFIX_RE = re.compile(r"^(?:https?://)?(?:dx\.)?doi\.org/", re.IGNORECASE)
_ARXIV_PREFIX_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/|^arxiv:",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")
_ET_AL_RE = re.compile(r"\bet\s+al\.?\b", re.IGNORECASE)
_DASH_TRANSLATION = str.maketrans({
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
})


def normalize_doi(value: str | None) -> str | None:
    """Return a stable DOI key, or ``None`` for an empty value."""
    if not value:
        return None
    value = unicodedata.normalize("NFKC", str(value)).strip()
    value = _DOI_PREFIX_RE.sub("", value)
    value = value.rstrip(" \t\r\n.,;:)]}>")
    return value.casefold() or None


def normalize_arxiv_id(value: str | None) -> str | None:
    """Return a stable arXiv identifier without version suffix."""
    if not value:
        return None
    value = unicodedata.normalize("NFKC", str(value)).strip()
    value = _ARXIV_PREFIX_RE.sub("", value)
    value = value.split("?", 1)[0].split("#", 1)[0]
    value = value.rstrip(" \t\r\n.,;:)]}>")
    value = re.sub(r"v\d+$", "", value, flags=re.IGNORECASE)
    return value.casefold() or None


def normalize_text(value: str | None) -> str:
    """Normalize human text for matching while preserving word boundaries."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(_DASH_TRANSLATION)
    text = _ET_AL_RE.sub(" ", text)
    text = text.casefold()
    # Keep Unicode letters/numbers, turn punctuation and symbols into spaces.
    text = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in text)
    return " ".join(text.split())


def title_tokens(value: str | None) -> list[str]:
    """Tokenize a normalized title, dropping one-character initials."""
    return [token for token in normalize_text(value).split() if len(token) > 1]


def author_key(value: object) -> str:
    """Extract a normalized first-author/last-name key from an author value."""
    if value is None:
        return ""
    if hasattr(value, "last_name"):
        value = getattr(value, "last_name", "")
    text = _ET_AL_RE.sub(" ", str(value))
    # APA ``Lastname, F.``: the token before the comma is the last name.
    if "," in text:
        text = text.split(",", 1)[0]
    tokens = title_tokens(text)
    if not tokens:
        return ""
    return tokens[-1]


def author_keys(authors: Iterable[object] | object | None) -> set[str]:
    """Normalize an author list; accept a single string for compatibility."""
    if authors is None:
        return set()
    if isinstance(authors, str):
        values: list[object] = [authors]
    else:
        try:
            values = list(authors)  # type: ignore[arg-type]
        except TypeError:
            values = [authors]
    return {key for key in (author_key(value) for value in values) if key}


def year_key(value: str | int | None) -> int | None:
    """Parse a four-digit publication year, ignoring APA suffixes."""
    if value is None:
        return None
    match = _YEAR_RE.search(str(value))
    return int(match.group(0)) if match else None


def title_similarity(query: str | None, candidate: str | None) -> float:
    """Token-aware title similarity in ``[0, 1]``.

    A shorter extracted title that is fully contained in a longer database
    title is considered a strong match (e.g. ``BERT: Pre-training``).
    """
    query_tokens = set(title_tokens(query))
    candidate_tokens = set(title_tokens(candidate))
    if not query_tokens or not candidate_tokens:
        return 0.0
    if query_tokens <= candidate_tokens:
        return 0.95
    intersection = len(query_tokens & candidate_tokens)
    union = len(query_tokens | candidate_tokens)
    jaccard = intersection / union if union else 0.0
    sequence = SequenceMatcher(
        None,
        " ".join(sorted(query_tokens)),
        " ".join(sorted(candidate_tokens)),
    ).ratio()
    return max(jaccard, sequence)


def citation_key(citation: Citation) -> str:
    """Canonical key used to deduplicate retrieval work across citation forms."""
    doi = normalize_doi(citation.doi)
    if doi:
        return f"doi:{doi}"
    arxiv_id = normalize_arxiv_id(citation.url or citation.raw_text)
    if arxiv_id and re.fullmatch(r"\d{4}\.\d{4,5}", arxiv_id):
        return f"arxiv:{arxiv_id}"
    title = normalize_text(citation.title)
    authors = sorted(author_keys(citation.authors))
    year = year_key(citation.year)
    if title:
        return f"title:{title}|author:{','.join(authors[:3])}|year:{year or ''}"
    return f"raw:{normalize_text(citation.raw_text)}"
