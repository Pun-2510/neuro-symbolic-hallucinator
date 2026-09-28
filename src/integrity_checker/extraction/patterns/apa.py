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
        - Author, A. A. (Year). Chapter title. In A. Editor (Ed.), Book title (pp. xx-xx). Publisher.

Reference:
    https://apastyle.apa.org/
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType
from integrity_checker.extraction.patterns.registry import register_format
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# =============================================================================
# APA Pattern Definitions
# =============================================================================

# --- In-text APA patterns ---

# Parenthetical: (Author, 2020), (Author et al., 2020)
# Supports: Single author, multiple authors, "et al.", "and"
# Note: Supports compound names like "van der", "de la"
_APA_INTEXT_PARENTHETICAL = CompiledPattern.create(
    name="apa_intext_parenthetical",
    pattern=r"\(\s*([A-Za-zÀ-ž][a-zÀ-ž]*(?:['\s][a-zA-ZÀ-ž][a-zÀ-ž]*)*(?:[A-Z][a-zÀ-ž]*)*(?:,?\s+(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*|,?\s*[A-Z][a-zÀ-ž]*\.?\s*[A-Z]?[a-zÀ-ž]*\.?)*)?)\s*,\s*(\d{4}[a-z]?)\s*\)",
    pattern_type=PatternType.IN_TEXT,
    description="APA in-text parenthetical: (Author, 2020) | (Author et al., 2020)",
)

# Narrative: Author (2020), Author et al. (2020)
# Supports: Single author, multiple authors, "et al.", "and"
_APA_INTEXT_NARRATIVE = CompiledPattern.create(
    name="apa_intext_narrative",
    pattern=r"([A-Za-zÀ-ž][a-zÀ-ž]*(?:['\s][a-zA-ZÀ-ž][a-zÀ-ž]*)*(?:[A-Z][a-zÀ-ž]*)*(?:,?\s+(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*|,?\s*[A-Z][a-zÀ-ž]*\.?\s*[A-Z]?[a-zÀ-ž]*\.?)*)?)\s+\((\d{4}[a-z]?)\)",
    pattern_type=PatternType.IN_TEXT,
    description="APA narrative: Author (2020) | Author et al. (2020)",
)

# --- Reference list APA patterns ---

# Standard APA reference entry:
# Author, A. A., & Author, B. B. (Year). Title of work. Publisher/DOI.
_APA_REFERENCE_ENTRY = CompiledPattern.create(
    name="apa_reference_entry",
    pattern=(
        r"^"
        r"(?P<authors>.+?)"
        r"\s+\(\s*(?P<year>\d{4})(?P<suffix>[a-z])?(?:\s*,\s*[^)]+)?\s*\)"
        r"\.?\s*"
        r"(?P<title>[^\.]+?)"
        r"\.(?:\s*)"
        r"(?P<venue>.+)"
        r"$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="APA reference entry with full author block and venue",
)

# APA reference entry with numbered prefix: [1] Author (Year). Title. Venue.
_APA_NUMBERED_REFERENCE = CompiledPattern.create(
    name="apa_numbered_reference",
    pattern=(
        r"^\[\s*\d+\s*\]\s*"
        r"(?P<authors>[A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.?\s*[A-Z]?[a-zÀ-ž]*)*)"
        r"\s+\(\s*(?P<year>\d{4})(?P<suffix>[a-z])?(?:\s*,\s*[^)]+)?\s*\)"
        r"\.?\s*"
        r"(?P<title>[^\.]+?)"
        r"\.(?:\s*)"
        r"(?P<venue>.+)"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Numbered APA reference: [1] Author (Year). Title. Venue.",
)

# Book chapter: Author (Year). Chapter title. In A. Editor (Ed.), Book title (pp. xx-xx). Publisher.
_APA_BOOK_CHAPTER = CompiledPattern.create(
    name="apa_book_chapter",
    pattern=(
        r"^"
        r"(?P<authors>.+?)"
        r"\s+\(\s*(?P<year>\d{4})(?P<suffix>[a-z])?(?:\s*,\s*[^)]+)?\s*\)"
        r"\.?\s*"
        r"(?P<title>[^\.]+?)"
        r"\.\s*"
        r"In\s+"
        r"(?P<editor>.+?)"
        r"(?:\s*\(Eds?\.?\)|\(Ed\.?\))?,?"
        r"\s*"
        r"(?P<book_title>.+?)(?:\s*\(pp\.\s*[\d\-–]+\))?"
        r"(?:\.\s*(?P<publisher>.+))?"
        r"$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="APA book chapter: Author (Year). Chapter. In Editor (Ed.), Book (pp. xx).",
)

# Simple APA entry (minimal): Author (Year). Title. Venue/DOI.
_APA_SIMPLE_ENTRY = CompiledPattern.create(
    name="apa_simple_entry",
    pattern=(
        r"^"
        r"(?P<authors>[A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.?\s*[A-Z]?[a-zÀ-ž]*)*)"
        r"\s+\(\s*(?P<year>\d{4})(?P<suffix>[a-z])?\)"
        r"\.?\s*"
        r"(?P<title>[^\.]+?)"
        r"\.\s*"
        r"(?P<venue>.+)"
        r"$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Simple APA entry: Author (Year). Title. Venue.",
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
        - Most common citation style in academic papers

    This implementation handles:
        - In-text parenthetical citations: (Smith, 2020), (Smith et al., 2020)
        - In-text narrative citations: Smith (2020), Smith et al. (2020)
        - Reference list entries with full metadata extraction
        - Book chapters with editor information
        - Numbered reference list entries
    """

    @property
    def name(self) -> str:
        """Format name."""
        return "APA"

    @property
    def priority(self) -> int:
        """Priority for format resolution (higher = try first).

        APA is the most common citation style, so it gets highest priority.
        """
        return 100

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
            _APA_NUMBERED_REFERENCE,
            _APA_BOOK_CHAPTER,
            _APA_SIMPLE_ENTRY,
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

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Check for numbered reference first (has [N] prefix)
        idx_match = re.search(r"\[\s*(\d+)\s*\]", text)
        numeric_index = int(idx_match.group(1)) if idx_match else None

        # Try each reference pattern in order
        patterns_to_try = [
            (_APA_REFERENCE_ENTRY, self._parse_apa_entry),
            (_APA_NUMBERED_REFERENCE, self._parse_apa_numbered_entry),
            (_APA_BOOK_CHAPTER, self._parse_apa_book_chapter_entry),
            (_APA_SIMPLE_ENTRY, self._parse_apa_simple_entry),
        ]

        for pattern, parser_func in patterns_to_try:
            match = pattern.search(text)
            if match:
                citation = parser_func(match, text)
                if citation:
                    # Set numeric_index if found and not already set
                    if numeric_index and citation.numeric_index is None:
                        citation.numeric_index = numeric_index
                    return citation

        # Fallback: try to extract whatever we can from unstructured text
        return self._parse_apa_fallback(text)

    def _parse_apa_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse standard APA reference entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_reference_entry",
        )

        # Extract authors
        authors_str = match.group("authors")
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract year
        citation.year = match.group("year")
        suffix = match.group("suffix")
        citation.year_suffix = suffix if suffix else None

        # Extract title
        title = match.group("title").strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract venue (rest of the text after title)
        venue = match.group("venue").strip()
        self._parse_venue(citation, venue)

        # Extract DOI if present
        doi_match = re.search(r"https?://(?:dx\.)?doi\.org/(.+)", text)
        if doi_match:
            citation.doi = doi_match.group(1).rstrip(".,;")
        else:
            doi_match = re.search(r"(10\.\d{4,9}/[^\s\]\)\,;]+)", text)
            if doi_match:
                citation.doi = doi_match.group(1).rstrip(".,;")

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_apa_numbered_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse numbered APA reference entry like [1] Author (Year). Title."""
        # Extract numeric index
        idx_match = re.search(r"\[\s*(\d+)\s*\]", text)
        numeric_index = int(idx_match.group(1)) if idx_match else None

        citation = self._parse_apa_entry(match, text)
        if citation and numeric_index:
            citation.numeric_index = numeric_index
        return citation

    def _parse_apa_book_chapter_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse APA book chapter entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_book_chapter",
        )

        # Extract authors
        authors_str = match.group("authors")
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract year
        citation.year = match.group("year")
        suffix = match.group("suffix")
        citation.year_suffix = suffix if suffix else None

        # Extract chapter title
        chapter_title = match.group("title").strip()
        citation.title = chapter_title
        citation.title_normalized = self._normalize_title(chapter_title)

        # Extract book title (stored in venue as "In Book Title")
        book_title = match.group("book_title").strip()
        publisher = match.group("publisher")
        citation.venue = f"In {book_title}" + (f". {publisher.strip()}" if publisher else "")

        # Extract DOI if present
        doi_match = re.search(r"(10\.\d{4,9}/[^\s\]\)\,;]+)", text)
        if doi_match:
            citation.doi = doi_match.group(1).rstrip(".,;")

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_apa_simple_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse simple APA reference entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_simple_entry",
        )

        # Extract authors
        authors_str = match.group("authors")
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract year
        citation.year = match.group("year")
        suffix = match.group("suffix")
        citation.year_suffix = suffix if suffix else None

        # Extract title
        title = match.group("title").strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract venue
        venue = match.group("venue").strip()
        self._parse_venue(citation, venue)

        # Extract DOI if present
        doi_match = re.search(r"(10\.\d{4,9}/[^\s\]\)\,;]+)", text)
        if doi_match:
            citation.doi = doi_match.group(1).rstrip(".,;")

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_apa_fallback(self, text: str) -> Optional[Citation]:
        """Fallback parser: extract whatever metadata possible from unstructured text."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_fallback",
        )

        # Try to extract year
        year_match = re.search(r"\((\d{4})([a-z])?\)", text)
        if year_match:
            citation.year = year_match.group(1)
            if year_match.group(2):
                citation.year_suffix = year_match.group(2)

        # Try to extract title (text between year and period after it)
        if year_match:
            after_year = text[year_match.end():]
            title_match = re.search(r"\.?\s*(.+?)\.", after_year)
            if title_match:
                title = title_match.group(1).strip()
                if title and len(title) > 5:
                    citation.title = title
                    citation.title_normalized = self._normalize_title(title)

        # Try to extract DOI
        doi_match = re.search(r"(10\.\d{4,9}/[^\s\]\)\,;]+)", text)
        if doi_match:
            citation.doi = doi_match.group(1).rstrip(".,;")

        citation.confidence = self._estimate_confidence(citation)
        return citation if citation.year else None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string like "Smith, J., & Jones, A."

        Returns:
            List of author strings
        """
        authors: list[str] = []

        # Clean up the string
        authors_str = authors_str.strip()

        # Split by "&" or "and" with proper handling
        # Pattern: ", & " or ", and " or just " & "
        parts = re.split(
            r"\s*,\s*&\s+|\s+and\s+|,&", authors_str
        )

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Clean up individual author
            # Remove trailing commas
            author = re.sub(r",$", "", part).strip()

            # Normalize spacing
            author = re.sub(r"\s+", " ", author)

            if author:
                authors.append(author)

        return authors

    def _parse_venue(self, citation: Citation, venue_text: str) -> None:
        """Parse venue information from remaining text.

        Handles:
        - Journal with volume and issue: "Journal Name, 10(2), 1-15"
        - Journal with DOI only: "Journal Name. https://doi.org/..."
        - Publisher: "Publisher Name"
        """
        if not venue_text:
            return

        venue_text = venue_text.strip()

        # Extract volume and issue: "Journal, 10(2)"
        vol_issue_match = re.search(
            r"(?P<journal>.+?),\s*(?P<vol>\d+)\((?P<issue>\d+)\)",
            venue_text
        )
        if vol_issue_match:
            citation.venue = vol_issue_match.group("journal").strip()
            citation.volume = vol_issue_match.group("vol")
            citation.issue = vol_issue_match.group("issue")

            # Extract pages after volume(issue)
            remaining = venue_text[vol_issue_match.end():]
            pages_match = re.search(r",\s*(?P<pages>[\d–-]+)", remaining)
            if pages_match:
                citation.pages = pages_match.group("pages")
        else:
            # Try just volume: "Journal, 10"
            vol_match = re.search(
                r"(?P<journal>.+?),\s*(?P<vol>\d+)(?P<pages>(?:\s*,\s*pp?\.\s*[\d–-]+)?)",
                venue_text
            )
            if vol_match:
                citation.venue = vol_match.group("journal").strip()
                citation.volume = vol_match.group("vol")
                pages = vol_match.group("pages")
                if pages:
                    # Extract page numbers from "pp. 1-15" or just "1-15"
                    pages_clean = re.sub(r"^,?\s*(?:pp?\.\s*)?", "", pages)
                    if pages_clean:
                        citation.pages = pages_clean.strip()
            else:
                # No volume - just journal name or publisher
                citation.venue = venue_text

        # Clean up venue
        if citation.venue:
            # Remove DOI from venue
            citation.venue = re.sub(
                r"\s*https?://(?:dx\.)?doi\.org/\S+",
                "",
                citation.venue
            ).strip()
            citation.venue = re.sub(
                r"\s*10\.\d{4,9}/\S+",
                "",
                citation.venue
            ).strip()
            citation.venue = citation.venue.rstrip(".,")

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison: lowercase, remove punctuation."""
        if not title:
            return ""
        t = title.lower()
        t = re.sub(r"[^\w\s]", " ", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    def _estimate_confidence(self, citation: Citation) -> float:
        """Estimate parse confidence based on extracted fields."""
        score = 0.0
        if citation.title:
            score += 0.4
        if citation.year:
            score += 0.3
        if citation.authors:
            score += 0.2
        if citation.doi:
            score += 0.1
        return min(round(score, 2), 1.0)

    def is_valid_citation(self, text: str) -> bool:
        """Check if text is a valid APA citation.

        Args:
            text: Text to validate

        Returns:
            True if text matches APA citation pattern, False otherwise
        """
        import re

        # Check for year pattern: any 4-digit year in reasonable range
        if not re.search(r"\b(19|20)\d{2}\b", text):
            return False

        # Check for author name pattern (capitalized word)
        author_pattern = r"[A-Z][a-zÀ-ž]"
        if not re.search(author_pattern, text):
            return False

        # Check if it's a parenthetical citation (starts with opening paren)
        stripped = text.strip()
        if stripped.startswith("("):
            # For parenthetical: author should be inside parentheses before year
            # Pattern: (Author, Year) or (Author et al., Year)
            paren_match = re.search(r"\(([^)]+)\)", text)
            if paren_match:
                paren_content = paren_match.group(1)
                # Check for year in parentheses
                if not re.search(r"\d{4}", paren_content):
                    return False
                # Check for author in parentheses (capitalized word)
                if not re.search(author_pattern, paren_content):
                    return False
                return True

        # For narrative citations: Author (Year) - author outside parens
        # Check if there's a capitalized word followed by (Year)
        narrative_pattern = r"[A-Z][a-zÀ-ž](?:[a-zÀ-ž]*[A-Z][a-zÀ-ž]*)*\s+\(\d{4}"
        if re.search(narrative_pattern, text):
            return True

        # Fallback: just check if it has both author and year
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
    _APA_NUMBERED_REFERENCE,
    _APA_BOOK_CHAPTER,
    _APA_SIMPLE_ENTRY,
]
