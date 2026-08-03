"""Author matching layer — v1.2 §3.6 (task #29).

Mục đích: Match ``Citation.authors`` (parsed từ PDF) với
``SourceCandidate.authors`` (raw strings từ scholarly APIs).

Vấn đề:
    - Citation.authors là ``list[Author]`` (last_name, initials, full_names).
    - SourceCandidate.authors là ``list[str]`` raw: "John Smith" hoặc "Smith, J."
      hoặc "J. K. Smith" — mỗi source API trả format khác nhau.
    - Citation.authors có thể là ``list[str]`` legacy (nếu parse fail).

Edge cases (theo §1.1 KNOWN_ISSUES):
    - "van der Berg, J." → last_name = "van der berg" (lowercase, multi-token).
    - "Smith J. K." → last_name = "smith" (no comma).
    - "J. K. Smith" → last_name = "smith" (no comma).
    - Vietnamese: "Nguyễn Bảo Minh" → "minh" (last token).
    - Diacritics: "Nguyễn" vs "Nguyen" (fold).

Solution:
    1. Normalize cả 2 sides về canonical form (lowercase, fold diacritics,
       strip particles).
    2. Compare canonical last-name tokens.
    3. Tính Jaccard-like score = |intersect| / |union| trên token sets.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Union

from integrity_checker.matching.author_parser import Author

# Multi-token particles (compound last names) — theo §1.1
_PARTICLES = {
    "van", "de", "der", "von", "den", "das", "der", "ten",
    "du", "le", "la", "di", "el", "al", "st", "st.",
    "nguyễn", "trần", "lê", "hoàng", "huỳnh", "phan", "võ", "đặng",  # VN
}

# Strip punctuation EXCEPT apostrophe (which joins words like O'Brien, D'Angelo)
_PUNCT_RE = re.compile(r"[^\w\s']", re.UNICODE)
# Remove apostrophes only when surrounded by whitespace (lone apostrophes)
_LONE_APOSTROPHE_RE = re.compile(r"\s'|'s\s|'s$|^'|'$", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
# Initial pattern: "J", "J.", "JK", "J.K.", "J K"
_INITIAL_RE = re.compile(r"^[A-Z]\.?$|^[A-Z]\.?[A-Z]\.?$", re.IGNORECASE)


def _fold_diacritics(text: str) -> str:
    """Fold diacritics: 'Nguyễn' → 'Nguyen'.

    Dùng NFD + filter combining marks. Reverse nếu cần original.
    """
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _strip_punctuation(text: str) -> str:
    """Remove punctuation, keep apostrophes within words.

    E.g. "O'Brien" → "O'Brien" (preserved), "Smith, J." → "Smith  J ".
    """
    return _PUNCT_RE.sub(" ", text)


def _canonicalize_last_name(name: str) -> str:
    """Canonicalize last_name cho matching.

    Handles:
        - Comma-split (APA / Chicago): "Smith, J." → last_name = "smith"
        - No-comma (IEEE): "J. K. Smith" → last_name = "smith"
        - Multi-word: "van der Berg" → "berg" (strip leading particles)
        - Vietnamese: "Nguyễn Bảo Minh" → "minh" (last token if no comma)
        - Diacritics: "Nguyễn" → "nguyen"

    Returns:
        Canonical last_name (lowercase, no diacritics, no particles).
    """
    if not name:
        return ""
    # Normalize + fold
    s = _fold_diacritics(name).lower()
    has_comma = "," in name
    s = _strip_punctuation(s)
    # Normalize whitespace + remove lone apostrophes (not within words)
    s = _LONE_APOSTROPHE_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    if not s:
        return ""
    tokens = s.split()

    if has_comma:
        # APA-like: "Smith, J." → "smith" is first token
        # Note: sometimes comma in middle like "Smith, J. K." → still first token
        # Strip particles from start
        while tokens and tokens[0] in _PARTICLES:
            tokens.pop(0)
        if not tokens:
            return ""
        return tokens[0]

    # No comma: take LAST non-initial token
    # E.g. "Smith J. K." → ["smith", "j", "k"] → "smith" (last non-initial)
    # E.g. "J. K. Smith" → ["j", "k", "smith"] → "smith" (also last)
    # E.g. "John Smith" → ["john", "smith"] → "smith"
    # Strip leading particles first
    while tokens and tokens[0] in _PARTICLES:
        tokens.pop(0)
    if not tokens:
        return ""
    # Find last token that's NOT an initial
    last_non_initial = ""
    for t in tokens:
        if not _INITIAL_RE.match(t):
            last_non_initial = t
    # If all are initials, fallback to last token
    return last_non_initial if last_non_initial else (tokens[-1] if tokens else "")


def _author_to_last_name(author: Union[Author, str]) -> str:
    """Extract last_name string từ Author or str.

    Args:
        author: Author object (with last_name) hoặc raw string "John Smith".

    Returns:
        Canonical last_name (lowercase, no diacritics, no particles).
        Empty string nếu không extract được.
    """
    if isinstance(author, Author):
        last_name = author.last_name or ""
    else:
        # String — use _canonicalize_last_name directly (more reliable than
        # normalize_author for ambiguous cases like "Alice Doe" where VN
        # heuristic incorrectly takes first token).
        last_name = str(author)
    return _canonicalize_last_name(last_name)


def _to_last_name_set(authors: list) -> set[str]:
    """Convert list[Author|str] → set[canonical last_name]."""
    result: set[str] = set()
    for a in authors:
        ln = _author_to_last_name(a)
        if ln:
            result.add(ln)
    return result


def author_match_score(
    cited: list,
    candidate: list,
    *,
    fold_diacritics: bool = True,
) -> float:
    """Tính similarity score giữa 2 author lists.

    Args:
        cited: Citation.authors (list[Author] or list[str]).
        candidate: SourceCandidate.authors (list[str]).
        fold_diacritics: True nếu muốn fold 'Nguyễn' → 'nguyen'
            (recommended for Vietnamese names).

    Returns:
        0.0–1.0. 1.0 = perfect match; 0.0 = no overlap.
        Returns 0.0 nếu 1 trong 2 lists rỗng.
    """
    cited_set = _to_last_name_set(cited)
    cand_set = _to_last_name_set(candidate)
    if not cited_set or not cand_set:
        return 0.0
    intersect = len(cited_set & cand_set)
    if intersect == 0:
        return 0.0
    union = len(cited_set | cand_set)
    return intersect / union if union else 0.0


def author_match_details(
    cited: list,
    candidate: list,
    *,
    fold_diacritics: bool = True,
) -> "AuthorMatchResult":
    """Trả về chi tiết match (để debug/log).

    Args:
        cited: Citation.authors.
        candidate: SourceCandidate.authors.

    Returns:
        AuthorMatchResult với:
            - score: 0.0–1.0
            - matched: list[last_name] chung
            - only_cited: list[last_name] chỉ có ở cited
            - only_candidate: list[last_name] chỉ có ở candidate
    """
    cited_set = _to_last_name_set(cited)
    cand_set = _to_last_name_set(candidate)
    matched = sorted(cited_set & cand_set)
    only_cited = sorted(cited_set - cand_set)
    only_cand = sorted(cand_set - cited_set)
    score = (
        author_match_score(cited, candidate, fold_diacritics=fold_diacritics)
        if (cited_set and cand_set)
        else 0.0
    )
    return AuthorMatchResult(
        score=score,
        matched=matched,
        only_cited=only_cited,
        only_candidate=only_cand,
    )


# --- Result dataclass ---

from dataclasses import dataclass, field  # noqa: E402


@dataclass
class AuthorMatchResult:
    """Output chi tiết của author_match_details() — cho debug/log."""

    score: float = 0.0
    matched: list[str] = field(default_factory=list)
    only_cited: list[str] = field(default_factory=list)
    only_candidate: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """One-line summary cho log."""
        return (
            f"score={self.score:.2f} "
            f"matched={self.matched} "
            f"only_cited={self.only_cited} "
            f"only_candidate={self.only_candidate}"
        )
