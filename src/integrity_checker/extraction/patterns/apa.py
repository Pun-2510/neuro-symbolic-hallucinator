"""APA citation format patterns and parser.

This module provides APA (American Psychological Association) citation format
implementation for the modular citation pattern system.

APA Style Citations:
    In-text:
        - Parenthetical: (Author, 2020), (Author et al., 2020)
        - Narrative: Author (2020), Author et al. (2020)

    Reference list:
        - Author, A. A., & Author, B. B. (Year). Title of article. Journal, Vol(Issue), pages.
        - Author, A. A. (Year). Title of book. Publisher.

Reference:
    https://apastyle.apa.org/
"""

from __future__ import annotations

from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType
from integrity_checker.extraction.patterns.registry import register_format
from integrity_checker.models.citation import Citation, CitationStyle


# =============================================================================
# APA Pattern Definitions
# =============================================================================

# --- In-text APA patterns ---

# Pattern allows compound words like "NovelPaper", "AuthorA", "SurveyAuthors"
# [A-Z] matches first letter, [a-zÀ-ž]* matches rest (may have uppercase in middle)
_APA_INTEXT_PARENTHETICAL = CompiledPattern.create(
    name="apa_intext_parenthetical",
    pattern=r"\(([A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*,?\s*(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*)?,?\s*\d{4}[a-z]?)\)",
    pattern_type=PatternType.IN_TEXT,
    description="APA in-text parenthetical: (Author, 2020) | (Author et al., 2020)",
)

_APA_INTEXT_NARRATIVE = CompiledPattern.create(
    name="apa_intext_narrative",
    pattern=r"([A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*,?\s*(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*)?,?\s*\(\d{4}[a-z]?\))",
    pattern_type=PatternType.IN_TEXT,
    description="APA narrative: Author (2020) | Author et al. (2020)",
)

# --- Reference list APA patterns (simplified) ---

_APA_REFERENCE_ENTRY = CompiledPattern.create(
    name="apa_reference_entry",
    pattern=(
        r"^([A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.\s*[A-Z]?[a-zÀ-ž]*)*"  # authors
        r"(?:,\s*&\s*[A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.\s*[A-Z]?[a-zÀ-ž]*)*)?)"  # & authors
        r"\s*\(\d{4}[a-z]?\)"  # year
        r"\.\s*(.+?)\."  # title
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="APA reference list entry (simplified)",
)


# =============================================================================
# APA Format Implementation
# =============================================================================


class APAFormat:
    """APA citation format implementation.

    APA (American Psychological Association) style is commonly used in:
        - Social sciences
        - Psychology
        - Education
    """

    @property
    def name(self) -> str:
        """Format name."""
        return "APA"

    @property
    def priority(self) -> int:
        """Priority for format resolution (lower = higher priority)."""
        return 10

    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting APA in-text citations."""
        return [
            _APA_INTEXT_PARENTHETICAL,
            _APA_INTEXT_NARRATIVE,
        ]

    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting APA reference list entries."""
        return [
            _APA_REFERENCE_ENTRY,
        ]

    def parse_reference_entry(self, text: str) -> Optional[Citation]:
        """Parse APA reference entry into Citation object.

        Args:
            text: Raw reference entry text

        Returns:
            Citation object if successfully parsed, None otherwise

        Examples:
            >>> text = "Smith, J., & Jones, A. (2020). Paper Title. Journal, 10(2), 1-15."
            >>> citation = APAFormat().parse_reference_entry(text)
            >>> citation.authors
            ['Smith, J.', 'Jones, A.']
            >>> citation.year
            '2020'
        """
        import re

        # Try each reference pattern
        for pattern in self.reference_patterns:
            match = pattern.search(text)
            if not match:
                continue

            raw = match.group(0)
            citation = Citation(
                raw_text=raw,
                citation_type=Citation.citation_type,  # type: ignore
                style=CitationStyle.APA,
                matched_pattern=pattern.name,
            )

            # Extract authors
            if match.lastindex and match.lastindex >= 1:
                authors_str = match.group(1)
                if authors_str:
                    citation.authors = self._parse_authors(authors_str)

            # Extract year
            year_match = re.search(r"\((\d{4}[a-z]?)\)", raw)
            if year_match:
                citation.year = year_match.group(1)

            # Extract title (simplified - between year and next period)
            title_match = re.search(r"\)\.\s*(.+?)\.", raw)
            if title_match:
                citation.title = title_match.group(1).strip()

            return citation

        return None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string like "Smith, J., & Jones, A."

        Returns:
            List of author strings
        """
        import re

        authors: list[str] = []

        # Split by "&" or "and"
        parts = re.split(r"\s*[,;]\s*&\s*|,\s+and\s+", authors_str)

        for part in parts:
            part = part.strip()
            if part:
                # Clean up individual author
                author = re.sub(r"\s+", " ", part).strip()
                if author:
                    authors.append(author)

        return authors

    def is_valid_citation(self, text: str) -> bool:
        """Check if text is a valid APA citation.

        Args:
            text: Text to validate

        Returns:
            True if text matches APA citation pattern, False otherwise
        """
        import re

        # Check for year in parentheses (required for APA)
        year_pattern = r"\(\d{4}[a-z]?\)"
        if not re.search(year_pattern, text):
            return False

        # Check for author name pattern (capitalized word)
        author_pattern = r"[A-Z][a-zÀ-ž]"
        if not re.search(author_pattern, text):
            return False

        return True


# =============================================================================
# Auto-registration
# =============================================================================

# Register APA format when this module is imported
register_format(APAFormat())


# =============================================================================
# Module-level pattern lists for convenience
# =============================================================================

APA_IN_TEXT_PATTERNS = [
    _APA_INTEXT_PARENTHETICAL,
    _APA_INTEXT_NARRATIVE,
]

APA_REFERENCE_PATTERNS = [
    _APA_REFERENCE_ENTRY,
]
