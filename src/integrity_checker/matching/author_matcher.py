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
# Note: "le" and "la" are French particles ("Le Pen") but also common Vietnamese/Asian
# standalone surnames ("Lê", "La"), so they are only stripped when followed by another token.
_PURE_PARTICLES = {
    "van", "de", "der", "von", "den", "das", "ten",
    "du", "di", "el", "al", "st", "st.",
}
_AMBIGUOUS_PARTICLES = {"le", "la"}
_PARTICLES = _PURE_PARTICLES | _AMBIGUOUS_PARTICLES
_GENERATIONAL_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}

# Strip punctuation EXCEPT apostrophe (which joins words like O'Brien, D'Angelo, L’Engle)
_PUNCT_RE = re.compile(r"[^\w\s']", re.UNICODE)
# Remove apostrophes only when surrounded by whitespace (lone apostrophes)
_LONE_APOSTROPHE_RE = re.compile(r"\s'|'s\s|'s$|^'|'$", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
# Initial pattern: "J", "J.", "J.K." (case-sensitive for 2-letter undotted "JK")
_INITIAL_RE = re.compile(r"^[A-Za-z]\.?$|^[A-Za-z](?:\.[A-Za-z])+\.?$|^[A-Z]{2}$")


def _is_initial_token(raw_tok: str, all_caps_name: bool = False) -> bool:
    """Return True if raw_tok is a given-name initial (e.g. 'J', 'J.', 'J.K.', 'JK').

    Distinguishes 2-letter TitleCase surnames ('Ji', 'Yu', 'Su', 'Xu', 'Lo',
    'Li', 'Wu', 'He', 'Le', 'Vo', 'Ho', 'Do') from true initials ('J.', 'J.K.',
    or Vancouver all-caps 'JK').
    """
    tok = raw_tok.strip().strip(",;:")
    if not tok:
        return False
    if re.match(r"^[A-Za-z]\.?$", tok):
        return True
    if re.match(r"^[A-Za-z](?:\.[A-Za-z])+\.?$", tok):
        return True
    if not all_caps_name and re.match(r"^[A-Z]{2}$", tok):
        return True
    return False
# Concatenated CamelCase author token from OpenAlex/Crossref (e.g. "PedregosaFabian")
_CAMEL_AUTHOR_RE = re.compile(r"^([A-ZÀ-ÖØ-Þ][a-zà-ÿ]{2,})([A-ZÀ-ÖØ-Þ][a-zà-ÿ]+)$")
_SURNAME_PREFIXES = {
    "mac", "van", "von", "fitz", "del", "dal", "das", "dos",
    "las", "los", "san", "bin", "abu", "ben",
}


def _split_camel_author(name: str) -> str:
    """Split concatenated CamelCase 'LastFirst' (e.g. 'PedregosaFabian' -> 'Pedregosa, Fabian')."""
    stripped = name.strip()
    if " " not in stripped and "," not in stripped:
        m = _CAMEL_AUTHOR_RE.match(stripped)
        if m and m.group(1).lower() not in _SURNAME_PREFIXES:
            return f"{m.group(1)}, {m.group(2)}"
    return name


def _fold_diacritics(text: str) -> str:
    """Fold diacritics: 'Nguyễn' → 'Nguyen', 'Đặng' → 'Dang'.

    Dùng NFD + filter combining marks + Vietnamese Đ/đ replacement.
    """
    nfd = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _strip_punctuation(text: str) -> str:
    """Remove punctuation, keep apostrophes within words.

    E.g. "O'Brien" → "O'Brien" (preserved), "Smith, J." → "Smith  J ".
    """
    return _PUNCT_RE.sub(" ", text)


def _strip_leading_particles(tokens: list[str]) -> list[str]:
    """Strip leading surname particles while preserving standalone 'Le'/'La' surnames."""
    res = list(tokens)
    while res:
        head = res[0]
        if head in _PURE_PARTICLES:
            res.pop(0)
        elif head in _AMBIGUOUS_PARTICLES and len(res) > 1:
            res.pop(0)
        else:
            break
    return res


def _canonicalize_last_name(name: str, *, fold_diacritics: bool = True) -> str:
    """Canonicalize last_name cho matching.

    Handles:
        - Comma-split (APA / Chicago): "Smith, J." → last_name = "smith"
        - No-comma (IEEE): "J. K. Smith" → last_name = "smith"
        - Multi-word: "van der Berg" → "berg" (strip leading particles)
        - Vietnamese: "Nguyễn Bảo Minh" → "minh" (last token if no comma)
        - Diacritics: "Nguyễn" → "nguyen", "Đặng" → "dang", "Lê, L." → "le"

    Returns:
        Canonical last_name (lowercase, no diacritics, no particles).
    """
    if not name:
        return ""
    name = name.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
    name = _split_camel_author(name)
    has_comma = "," in name

    if has_comma:
        # APA-like: "Smith, J." or "van der Berg, J." or "Pouget-Abadie, J."
        surname_part = name.split(",", 1)[0]
        s = (_fold_diacritics(surname_part) if fold_diacritics else surname_part).lower()
        s = _strip_punctuation(s)
        s = _LONE_APOSTROPHE_RE.sub(" ", s)
        s = _WHITESPACE_RE.sub(" ", s).strip()
        if not s:
            return ""
        tokens = _strip_leading_particles(s.split())
        while len(tokens) > 1 and tokens[-1] in _GENERATIONAL_SUFFIXES:
            tokens.pop()
        if not tokens:
            return ""
        return tokens[-1]

    # No comma: take LAST non-initial token
    # E.g. "Smith J. K." → ["smith", "j", "k"] → "smith" (last non-initial)
    # E.g. "J. K. Smith" → ["j", "k", "smith"] → "smith" (also last)
    # E.g. "John Smith" → ["john", "smith"] → "smith"
    # E.g. "Ziwei Ji" → ["ziwei", "ji"] → "ji" (2-letter TitleCase surname preserved)
    raw_folded = _fold_diacritics(name) if fold_diacritics else name
    alpha_chars = [c for c in raw_folded if c.isalpha()]
    all_caps_name = bool(alpha_chars) and all(c.isupper() for c in alpha_chars)
    raw_tokens = raw_folded.split()
    while len(raw_tokens) > 1 and raw_tokens[-1].lower().strip(".,;:") in _GENERATIONAL_SUFFIXES:
        raw_tokens.pop()

    # Strip leading particles first
    while raw_tokens:
        first_clean = _WHITESPACE_RE.sub(
            " ", _LONE_APOSTROPHE_RE.sub(" ", _strip_punctuation(raw_tokens[0].lower()))
        ).strip()
        if first_clean in _PURE_PARTICLES:
            raw_tokens.pop(0)
        elif first_clean in _AMBIGUOUS_PARTICLES and len(raw_tokens) > 1:
            # Check if remaining tokens have at least one non-initial token
            has_other_surname = any(
                not _is_initial_token(rt, all_caps_name=all_caps_name)
                for rt in raw_tokens[1:]
            )
            if has_other_surname:
                raw_tokens.pop(0)
            else:
                break
        else:
            break
    if not raw_tokens:
        return ""

    # Find last token that's NOT an initial
    last_non_initial = ""
    fallback_tokens: list[str] = []
    for rt in raw_tokens:
        ct = _WHITESPACE_RE.sub(
            " ", _LONE_APOSTROPHE_RE.sub(" ", _strip_punctuation(rt.lower()))
        ).strip()
        if not ct:
            continue
        ct_parts = ct.split()
        fallback_tokens.extend(ct_parts)
        if not _is_initial_token(rt, all_caps_name=all_caps_name):
            last_non_initial = ct_parts[-1]
    # If all are initials, fallback to last token
    return last_non_initial if last_non_initial else (fallback_tokens[-1] if fallback_tokens else "")


def _author_to_last_name(author: Union[Author, str], *, fold_diacritics: bool = True) -> str:
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
    return _canonicalize_last_name(last_name, fold_diacritics=fold_diacritics)


def _to_last_name_set(authors: list, *, fold_diacritics: bool = True) -> set[str]:
    """Convert list[Author|str] → set[canonical last_name]."""
    result: set[str] = set()
    for a in authors:
        ln = _author_to_last_name(a, fold_diacritics=fold_diacritics)
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

    FIX v1.11: Improved handling for first-author-only citations.
    When citation has 1 author but candidate has many, we check if the
    first author matches any candidate author (common in short citations
    like "Settles, B (2012)").

    Args:
        cited: Citation.authors (list[Author] or list[str]).
        candidate: SourceCandidate.authors (list[str]).
        fold_diacritics: True nếu muốn fold 'Nguyễn' → 'nguyen'
            (recommended for Vietnamese names).

    Returns:
        0.0–1.0. 1.0 = perfect match; 0.0 = no overlap.
        Returns 0.0 nếu 1 trong 2 lists rỗng.
    """
    cited_set = _to_last_name_set(cited, fold_diacritics=fold_diacritics)
    cand_set = _to_last_name_set(candidate, fold_diacritics=fold_diacritics)
    if not cited_set or not cand_set:
        return 0.0

    # FIX v1.11: If all cited authors are present in the candidate's author list
    # (e.g., "Settles, B" or "Pedregosa, Varoquaux, Gramfort, et al." on a 16-author paper),
    # treat as full author match.
    if cited_set <= cand_set:
        return 1.0  # Exact subset match (et al. truncation)
    if len(cand_set) == 1 and cand_set <= cited_set and cited:
        first_cited = _author_to_last_name(cited[0], fold_diacritics=fold_diacritics)
        if first_cited and first_cited in cand_set:
            return 1.0  # Cited entry also listed editors/introducers alongside primary author

    intersect = len(cited_set & cand_set)
    # Fallback: check prefix/suffix/apostrophe match for compound tokens (len >= 5)
    if intersect == 0:
        prefix_matches = sum(
            1
            for ca in cited_set
            if len(ca) >= 4
            and any(
                len(cb) >= 4
                and (
                    ca.replace("'", "") == cb.replace("'", "")
                    or (len(ca) >= 5 and len(cb) >= 5 and (ca.startswith(cb) or cb.startswith(ca) or ca.endswith(cb) or cb.endswith(ca)))
                )
                for cb in cand_set
            )
        )
        if prefix_matches > 0:
            return prefix_matches / len(cited_set)
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
    cited_set = _to_last_name_set(cited, fold_diacritics=fold_diacritics)
    cand_set = _to_last_name_set(candidate, fold_diacritics=fold_diacritics)
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
