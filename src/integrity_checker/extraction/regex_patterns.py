"""Citation regex patterns — APA / MLA / Chicago / IEEE / numeric / DOI / URL.

Mỗi pattern có:
    - name: id nội bộ
    - pattern: regex string
    - style: CitationStyle
    - type: CitationType
    - description: cho documentation

# TODO(user): tuần 6 — bổ sung thêm:
    - Numeric citation kiểu superscript (^1)
    - Citation với page number (Smith, 2020, p. 45)
    - Author groups kiểu "Smith, J., & Jones, A."
"""

from __future__ import annotations

from dataclasses import dataclass

from integrity_checker.models.citation import CitationStyle, CitationType


@dataclass(frozen=True)
class CitationPattern:
    name: str
    pattern: str
    style: CitationStyle
    type: CitationType
    description: str


# --- In-text APA ---
_APA_INTEXT_SINGLE = (
    r"\(([A-Z][a-zÀ-ž]+(?:\s+(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]+))?,?\s*\d{4}[a-z]?)\)"
)
_APA_NAMED_SINGLE = (
    r"([A-Z][a-zÀ-ž]+(?:\s+(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]+))?,?\s*\(\d{4}[a-z]?\))"
)

# --- Numeric (IEEE, Vancouver) ---
_NUMERIC_BRACKET = r"\[(\d+(?:[,\s\-]+\d+)*)\]"

# --- DOI ---
_DOI_PATTERN = r"10\.\d{4,9}/[^\s\]\)\,;]+"

# --- URL ---
_URL_PATTERN = r"https?://[^\s\]\)\,;]+"

# --- Reference list APA (simplified) ---
_APA_REFERENCE = (
    r"^([A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.\s*[A-Z]?[a-zÀ-ž]*)*"  # authors
    r"(?:,\s*&\s*[A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.\s*[A-Z]?[a-zÀ-ž]*)*)?)"
    r"\s*\(\d{4}[a-z]?\)"  # year
    r"\.\s*(.+?)\."  # title
)

CITATION_PATTERNS: list[CitationPattern] = [
    CitationPattern(
        name="apa_intext_parenthetical",
        pattern=_APA_INTEXT_SINGLE,
        style=CitationStyle.APA,
        type=CitationType.IN_TEXT,
        description="APA in-text: (Author, 2020) | (Author et al., 2020)",
    ),
    CitationPattern(
        name="apa_intext_narrative",
        pattern=_APA_NAMED_SINGLE,
        style=CitationStyle.APA,
        type=CitationType.IN_TEXT,
        description="APA narrative: Author (2020) | Author et al. (2020)",
    ),
    CitationPattern(
        name="numeric_brackets",
        pattern=_NUMERIC_BRACKET,
        style=CitationStyle.IEEE,
        type=CitationType.NUMERIC,
        description="IEEE numeric: [1] | [1,2] | [1-5]",
    ),
    CitationPattern(
        name="doi",
        pattern=_DOI_PATTERN,
        style=CitationStyle.UNKNOWN,
        type=CitationType.DOI,
        description="DOI: 10.xxxx/yyyy",
    ),
    CitationPattern(
        name="url",
        pattern=_URL_PATTERN,
        style=CitationStyle.UNKNOWN,
        type=CitationType.URL,
        description="URL: http(s)://...",
    ),
    CitationPattern(
        name="apa_reference_entry",
        pattern=_APA_REFERENCE,
        style=CitationStyle.APA,
        type=CitationType.REFERENCE_LIST,
        description="APA reference list entry (simplified)",
    ),
]


def get_all_patterns() -> list[CitationPattern]:
    """Trả về tất cả patterns."""
    return list(CITATION_PATTERNS)