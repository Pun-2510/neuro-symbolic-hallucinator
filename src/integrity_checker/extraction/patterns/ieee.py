"""IEEE/Numeric citation format patterns and parser.

This module provides IEEE and numeric citation format implementation
for the modular citation pattern system.

Numeric Style Citations:
    In-text:
        - Bracketed numbers: [1], [1,2], [1-5], [1, 2, 3]
        - Superscript: ^1 (TODO)

    Reference list:
        - Numbered entries: [1] Author, A. (Year). Title. ...

Reference:
    https://ieee-dataport.org/sites/default/files/analysis/27/
    IEEE%20Reference%20Guide%20(updated)%20-%20Final.pdf
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType
from integrity_checker.extraction.patterns.registry import register_format
from integrity_checker.models.citation import Citation, CitationStyle


# =============================================================================
# IEEE/Numeric Pattern Definitions
# =============================================================================

# --- In-text Numeric patterns ---

# Bracketed numbers: [1], [1,2], [1-5], [1, 2, 3]
_NUMERIC_BRACKETED = CompiledPattern.create(
    name="numeric_bracketed",
    pattern=r"\[(\d+(?:[,\s\-]+\d+)*)\]",
    pattern_type=PatternType.IN_TEXT,
    description="Numeric bracketed: [1] | [1,2] | [1-5] | [1, 2, 3]",
)

# --- Reference list numeric patterns ---

# IEEE reference entry: [N] Author, A. A. (Year). Title. ...
_IEEE_REFERENCE_ENTRY = CompiledPattern.create(
    name="ieee_reference_entry",
    pattern=r"^\s*\[\d+\]\s+([A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.?\s*[A-Z]?[a-zÀ-ž]*)*)",
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="IEEE reference entry: [1] Author...",
)


# =============================================================================
# IEEE/Numeric Format Implementation
# =============================================================================


class IEEEFormat:
    """IEEE/Numeric citation format implementation.

    IEEE style is commonly used in:
        - Engineering
        - Computer Science
        - Electronics
    """

    @property
    def name(self) -> str:
        """Format name."""
        return "IEEE"

    @property
    def priority(self) -> int:
        """Priority for format resolution (lower = higher priority)."""
        return 20

    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting numeric in-text citations."""
        return [
            _NUMERIC_BRACKETED,
        ]

    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting IEEE reference list entries."""
        return [
            _IEEE_REFERENCE_ENTRY,
        ]

    def parse_reference_entry(self, text: str) -> Optional[Citation]:
        """Parse IEEE reference entry into Citation object.

        Args:
            text: Raw reference entry text

        Returns:
            Citation object if successfully parsed, None otherwise

        Examples:
            >>> text = "[1] Smith, J. and Jones, A. (2020). Paper Title. Journal."
            >>> citation = IEEEFormat().parse_reference_entry(text)
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
                style=CitationStyle.IEEE,
                matched_pattern=pattern.name,
            )

            # Extract numeric index
            index_match = re.search(r"\[(\d+)\]", raw)
            if index_match:
                citation.numeric_index = int(index_match.group(1))

            # Extract authors
            if match.lastindex and match.lastindex >= 1:
                authors_str = match.group(1)
                if authors_str:
                    citation.authors = self._parse_authors(authors_str)

            # Extract year
            year_match = re.search(r"\((\d{4}[a-z]?)\)", raw)
            if year_match:
                citation.year = year_match.group(1)

            # Extract title (simplified - between year and period)
            title_match = re.search(r"\)\.\s+(.+?)\.", raw)
            if title_match:
                citation.title = title_match.group(1).strip()

            return citation

        return None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string like "Smith, J. and Jones, A."

        Returns:
            List of author strings
        """
        import re

        authors: list[str] = []

        # Split by "and"
        parts = re.split(r"\s+and\s+", authors_str)

        for part in parts:
            part = part.strip()
            if part:
                # Clean up individual author
                author = re.sub(r"\s+", " ", part).strip()
                if author:
                    authors.append(author)

        return authors

    def is_valid_citation(self, text: str) -> bool:
        """Check if text is a valid IEEE/numeric citation.

        Args:
            text: Text to validate

        Returns:
            True if text matches numeric citation pattern, False otherwise
        """
        import re

        # Check for bracketed number pattern
        bracket_pattern = r"\[\d+(?:[,\s\-]+\d+)*\]"
        if re.match(bracket_pattern, text.strip()):
            return True

        return False


# =============================================================================
# Auto-registration
# =============================================================================

# Register IEEE format when this module is imported
register_format(IEEEFormat())


# =============================================================================
# Module-level pattern lists for convenience
# =============================================================================

IEEE_IN_TEXT_PATTERNS = [
    _NUMERIC_BRACKETED,
]

IEEE_REFERENCE_PATTERNS = [
    _IEEE_REFERENCE_ENTRY,
]
