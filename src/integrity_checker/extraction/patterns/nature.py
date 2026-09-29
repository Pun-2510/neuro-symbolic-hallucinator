"""Nature citation format patterns and parser.

This module provides Nature citation format implementation for the
modular citation pattern system.

Nature Style Citations:
    In-text:
        - Superscript numbers: ^1, ^2
        - Sometimes bracketed: [1], [2]

    Reference list:
        - Numbered list: 1. Authors, Title, Journal Volume, Pages (Year).
        - Compact format: Authors, Title, Journal Volume, Pages (Year).
        - Abbreviated journal names
        - No period after journal name before year

Key characteristics:
    - Superscript citations preferred
    - Compact reference format
    - Journal name usually abbreviated
    - Year in parentheses at end

Reference:
    https://www.nature.com/nature-authors
    https://www.nature.com/srep/author-instructions
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType
from integrity_checker.extraction.patterns.registry import register_format
from integrity_checker.matching.author_parser import parse_authors
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# =============================================================================
# Nature Pattern Definitions
# =============================================================================

# --- In-text Nature patterns ---

# Superscript numbers: ^1, ^2
_NATURE_SUPERSCRIPT = CompiledPattern.create(
    name="nature_superscript",
    pattern=r"\^(\d+)",
    pattern_type=PatternType.IN_TEXT,
    description="Nature superscript: ^1 | ^2",
)

# Bracketed numbers: [1], [2]
_NATURE_BRACKETED = CompiledPattern.create(
    name="nature_bracketed",
    pattern=r"\[(\d+)\]",
    pattern_type=PatternType.IN_TEXT,
    description="Nature bracketed: [1] | [2]",
)

# Comma-separated superscripts: ^1,^2,^3
_NATURE_SUPERSCRIPT_COMMA = CompiledPattern.create(
    name="nature_superscript_comma",
    pattern=r"\^(\d+(?:,\s*\^*\d+)+)",
    pattern_type=PatternType.IN_TEXT,
    description="Nature superscript comma: ^1,^2 | ^1, ^2",
)

# --- Reference list Nature patterns ---

# Nature compact article:
# 1. Authors. Title, Journal Volume, Pages (Year).
_NATURE_REFERENCE_COMPACT = CompiledPattern.create(
    name="nature_reference_compact",
    pattern=(
        r"^"
        r"(?:\d+\.?\s*)?"  # Optional number.
        r"(?P<authors>.+?)\.\s+"  # Authors.
        r"(?P<title>.+?),"  # Title,
        r"\s*(?P<venue>[^0-9]+)\s*"  # Journal (no numbers)
        r"(?P<volume>\d+)"  # Volume
        r"(?:,\s*(?P<pages>[\d–-]+))?"  # , Pages
        r"\s*\((?P<year>\d{4})\)"  # (Year)
        r"(?P<rest>.*)$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Nature compact: Authors. Title, Journal Volume, Pages (Year).",
)

# Nature with numbered prefix:
# [1] Authors. Title, Journal Volume, Pages (Year).
_NATURE_NUMBERED = CompiledPattern.create(
    name="nature_numbered",
    pattern=(
        r"^\[\s*(?P<index>\d+)\s*\]\s*"  # [N]
        r"(?P<authors>.+?)\.\s+"  # Authors.
        r"(?P<title>.+?),"  # Title,
        r"\s*(?P<venue>[^0-9]+)\s*"  # Journal (no numbers)
        r"(?P<volume>\d+)"  # Volume
        r"(?:,\s*(?P<pages>[\d–-]+))?"  # , Pages
        r"\s*\((?P<year>\d{4})\)"  # (Year)
        r"(?P<rest>.*)$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Nature numbered: [1] Authors. Title, Journal Volume, Pages (Year).",
)

# Nature article with DOI:
# 1. Authors. Title, Journal Volume, Pages (Year). doi:...
_NATURE_REFERENCE_DOI = CompiledPattern.create(
    name="nature_reference_doi",
    pattern=(
        r"^"
        r"(?:\d+\.?\s*)?"  # Optional number.
        r"(?P<authors>.+?)\.\s+"  # Authors.
        r"(?P<title>.+?),"  # Title,
        r"\s*(?P<venue>[^0-9]+)\s*"  # Journal (no numbers)
        r"(?P<volume>\d+)"  # Volume
        r"(?:,\s*(?P<pages>[\d–-]+))?"  # , Pages
        r"\s*\((?P<year>\d{4})\)"  # (Year)
        r"(?:\.\s*)?doi:(?P<doi>.+)?"  # . doi:...
        r"$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Nature with DOI: Authors. Title, Journal Volume, Pages (Year). doi:...",
)

# Nature book:
# Authors, Book Title, Publisher, Year.
_NATURE_BOOK = CompiledPattern.create(
    name="nature_book",
    pattern=(
        r"^"
        r"(?:\d+\.?\s*)?"  # Optional number.
        r"(?P<authors>.+?),?\s+"  # Authors,
        r"(?P<title>.+?),?\s+"  # Title,
        r"(?P<publisher>.+?),?\s*"  # Publisher,
        r"(?P<year>\d{4})?"  # Optional year
        r"(?P<rest>.*)$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Nature book: Authors, Book Title, Publisher, Year.",
)

# Nature book chapter:
# Authors, Chapter title, in Book Title (ed. Editor), Publisher, Year.
_NATURE_BOOK_CHAPTER = CompiledPattern.create(
    name="nature_book_chapter",
    pattern=(
        r"^"
        r"(?:\d+\.?\s*)?"  # Optional number.
        r"(?P<authors>.+?),?\s+"  # Authors,
        r"(?P<chapter_title>.+?),?\s+"  # Chapter title,
        r"in\s+"  # in
        r"(?P<book_title>.+?)"  # Book title
        r"(?:\s*\(eds?\.?\s+(?P<editor>.+?)\))?"  # (ed. Editor)
        r"(?:,\s*(?P<publisher>.+?))?"  # , Publisher
        r"(?:,\s*(?P<year>\d{4}))?"  # , Year
        r"(?P<rest>.*)$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Nature book chapter: Authors, Chapter, in Book (ed. Editor), Publisher.",
)

# Nature website:
# Authors, Title, URL (Year).
_NATURE_WEBSITE = CompiledPattern.create(
    name="nature_website",
    pattern=(
        r"^"
        r"(?:\d+\.?\s*)?"  # Optional number.
        r"(?P<authors>.+?),?\s+"  # Authors,
        r"(?P<title>.+?),?\s+"  # Title,
        r"(?P<url>https?://.+)"  # URL
        r"(?:\s*\((?P<year>\d{4})\))?"  # Optional (Year)
        r"$"
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="Nature website: Authors, Title, URL (Year).",
)

# --- Utility pattern ---

_NATURE_NUMBER_MARKER = CompiledPattern.create(
    name="nature_number_marker",
    pattern=r'^\s*(?:\[\d+\]|\d+\.|\^?\d+)\s*',
    pattern_type=PatternType.UTILITY,
    description="Nature number marker: [N] | N. | ^N",
)


# =============================================================================
# Nature Format Implementation
# =============================================================================


class NatureFormat:
    """Nature citation format implementation.

    Nature style is commonly used in:
        - Nature journals
        - Scientific research
        - Biology, physics, medicine

    Key characteristics:
        - Superscript citations preferred
        - Compact reference format
        - Journal name abbreviated
        - Year in parentheses at end

    This implementation handles:
        - In-text numeric citations: ^1, [1]
        - Reference list entries for articles, books, chapters, websites
        - Both numbered and unnumbered formats
    """

    @property
    def name(self) -> str:
        """Format name."""
        return "Nature"

    @property
    def priority(self) -> int:
        """Priority for format resolution (higher = try first).

        Nature is common in scientific journals.
        Priority 78 (similar to AMA).
        """
        return 78

    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting Nature in-text citations."""
        return [
            _NATURE_SUPERSCRIPT,
            _NATURE_BRACKETED,
            _NATURE_SUPERSCRIPT_COMMA,
        ]

    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting Nature reference list entries."""
        return [
            _NATURE_REFERENCE_DOI,
            _NATURE_NUMBERED,
            _NATURE_REFERENCE_COMPACT,
            _NATURE_BOOK_CHAPTER,
            _NATURE_BOOK,
            _NATURE_WEBSITE,
        ]

    def parse_reference_entry(self, text: str) -> Optional[Citation]:
        """Parse Nature reference entry into Citation object.

        Args:
            text: Raw reference entry text

        Returns:
            Citation object if successfully parsed, None otherwise

        Examples:
            >>> text = "1. Smith, J. & Jones, A. Article title, Nature 10, 123-145 (2020)."
            >>> citation = NatureFormat().parse_reference_entry(text)
            >>> citation.authors
            >>> citation.year
            '2020'
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Extract numeric index first
        numeric_index = None
        idx_match = re.search(r'\[\s*(\d+)\s*\]', text)
        if idx_match:
            numeric_index = int(idx_match.group(1))
        else:
            # Try period-numbered: "1. Authors..."
            num_match = re.match(r'^(\d+)\.?\s', text)
            if num_match:
                numeric_index = int(num_match.group(1))

        # Try article with DOI format first (most specific)
        citation = self._try_parse_article_doi(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try numbered variant
        citation = self._try_parse_numbered(text)
        if citation:
            return citation

        # Try compact format
        citation = self._try_parse_compact(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try book chapter format
        citation = self._try_parse_book_chapter(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try book format
        citation = self._try_parse_book(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try website format
        citation = self._try_parse_website(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Fallback
        return self._parse_nature_fallback(text)

    def _try_parse_article_doi(self, text: str) -> Optional[Citation]:
        """Try to parse Nature article with DOI format."""
        match = _NATURE_REFERENCE_DOI.search(text)
        if match:
            return self._parse_article_doi_entry(match, text)
        return None

    def _try_parse_numbered(self, text: str) -> Optional[Citation]:
        """Try to parse Nature numbered format."""
        match = _NATURE_NUMBERED.search(text)
        if match:
            return self._parse_numbered_entry(match, text)
        return None

    def _try_parse_compact(self, text: str) -> Optional[Citation]:
        """Try to parse Nature compact format."""
        match = _NATURE_REFERENCE_COMPACT.search(text)
        if match:
            return self._parse_compact_entry(match, text)
        return None

    def _try_parse_book(self, text: str) -> Optional[Citation]:
        """Try to parse Nature book format."""
        match = _NATURE_BOOK.search(text)
        if match:
            return self._parse_book_entry(match, text)
        return None

    def _try_parse_book_chapter(self, text: str) -> Optional[Citation]:
        """Try to parse Nature book chapter format."""
        match = _NATURE_BOOK_CHAPTER.search(text)
        if match:
            return self._parse_book_chapter_entry(match, text)
        return None

    def _try_parse_website(self, text: str) -> Optional[Citation]:
        """Try to parse Nature website format."""
        match = _NATURE_WEBSITE.search(text)
        if match:
            return self._parse_website_entry(match, text)
        return None

    def _parse_article_doi_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse Nature article with DOI entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_reference_doi",
        )

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract title
        title = match.group('title').strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract venue and volume
        venue = match.group('venue').strip()
        volume = match.group('volume')
        pages = match.group('pages')

        if volume:
            citation.venue = f"{venue} {volume}"
            citation.volume = volume
        else:
            citation.venue = venue

        if pages:
            citation.pages = pages

        # Extract year
        year_str = match.group('year')
        if year_str:
            citation.year = year_str

        # Extract DOI
        doi = match.group('doi')
        if doi:
            citation.doi = doi.strip()

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_numbered_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse Nature numbered entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_numbered",
        )

        # Extract numeric index
        index = match.group('index')
        if index:
            citation.numeric_index = int(index)

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract title
        title = match.group('title').strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract venue and volume
        venue = match.group('venue').strip()
        volume = match.group('volume')
        pages = match.group('pages')

        if volume:
            citation.venue = f"{venue} {volume}"
            citation.volume = volume
        else:
            citation.venue = venue

        if pages:
            citation.pages = pages

        # Extract year
        year_str = match.group('year')
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_match = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_match:
            citation.doi = doi_match.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_compact_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse Nature compact entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_reference_compact",
        )

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract title
        title = match.group('title').strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract venue and volume
        venue = match.group('venue').strip()
        volume = match.group('volume')
        pages = match.group('pages')

        if volume:
            citation.venue = f"{venue} {volume}"
            citation.volume = volume
        else:
            citation.venue = venue

        if pages:
            citation.pages = pages

        # Extract year
        year_str = match.group('year')
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_match = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_match:
            citation.doi = doi_match.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_book_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse Nature book entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_book",
        )

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract title
        title = match.group('title').strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract publisher and year
        publisher = match.group('publisher')
        year_str = match.group('year')

        if publisher:
            citation.venue = publisher.strip()
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_match = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_match:
            citation.doi = doi_match.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_book_chapter_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse Nature book chapter entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_book_chapter",
        )

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract chapter title
        chapter_title = match.group('chapter_title').strip()
        citation.title = chapter_title
        citation.title_normalized = self._normalize_title(chapter_title)

        # Extract book title (as venue)
        book_title = match.group('book_title').strip()
        editor = match.group('editor')
        publisher = match.group('publisher')
        year_str = match.group('year')

        citation.venue = book_title
        if editor:
            citation.venue += f" (ed. {editor.strip()})"
        if publisher:
            citation.venue += f", {publisher.strip()}"
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_match = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_match:
            citation.doi = doi_match.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_website_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse Nature website entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_website",
        )

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract title
        title = match.group('title').strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract URL
        url = match.group('url')
        if url:
            citation.url = url.strip()

        # Extract year
        year_str = match.group('year')
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_match = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_match:
            citation.doi = doi_match.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_nature_fallback(self, text: str) -> Optional[Citation]:
        """Fallback parser: extract whatever metadata possible."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.NATURE,
            matched_pattern="nature_fallback",
        )

        # Extract numeric index
        idx_match = re.search(r'\[\s*(\d+)\s*\]', text)
        if idx_match:
            citation.numeric_index = int(idx_match.group(1))
        else:
            num_match = re.match(r'^(\d+)\.?\s', text)
            if num_match:
                citation.numeric_index = int(num_match.group(1))

        # Try to extract year from parentheses
        year_m = re.search(r'\((?:\d{4})\)', text)
        if year_m:
            citation.year = year_m.group(0)[1:-1]

        # Try to extract title (usually the longest quoted or capitalized segment)
        # Look for text between author and year
        if year_m:
            before_year = text[:year_m.start()]
            parts = before_year.split(',')
            if len(parts) >= 2:
                # Title is often the second or third part
                for part in parts[1:]:
                    part = part.strip()
                    if len(part) > 10:
                        citation.title = part
                        citation.title_normalized = self._normalize_title(part)
                        break

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation if citation.title or citation.year else None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string

        Returns:
            List of author strings (via parse_authors)
        """
        return parse_authors(authors_str)

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison: lowercase, remove punctuation."""
        if not title:
            return ''
        t = title.lower()
        t = re.sub(r'[^\w\s]', ' ', t)
        t = re.sub(r'\s+', ' ', t)
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
        """Check if text is a valid Nature citation.

        Args:
            text: Text to validate

        Returns:
            True if text matches Nature citation pattern, False otherwise
        """
        # Check for superscript pattern
        if re.match(r'^\^?\s*\d+', text.strip()):
            return True

        # Check for bracketed number pattern
        bracket_pattern = r'^\[\s*\d+\s*\]'
        if re.match(bracket_pattern, text.strip()):
            return True

        # Check for Nature reference pattern: Authors, Title, Journal Volume (Year)
        if re.search(r',\s+\d+\s+\(\d{4}\)', text):
            return True

        return False

    def is_reference_list_marker(self, text: str) -> bool:
        """Check if text is a reference list marker.

        Args:
            text: Text to check

        Returns:
            True if text is a reference list marker, False otherwise
        """
        # Match standalone [N] or N. at start
        if re.match(r'^\s*\[\d+\]\s*$', text):
            return True
        if re.match(r'^\s*\d+\.\s*$', text):
            return True
        if re.match(r'^\s*\^\d+\s*$', text):
            return True

        return False


# =============================================================================
# Auto-registration
# =============================================================================

# Register Nature format when this module is imported
register_format(NatureFormat())


# =============================================================================
# Module-level pattern lists for convenience
# =============================================================================

NATURE_IN_TEXT_PATTERNS = [
    _NATURE_SUPERSCRIPT,
    _NATURE_BRACKETED,
    _NATURE_SUPERSCRIPT_COMMA,
]

NATURE_REFERENCE_PATTERNS = [
    _NATURE_REFERENCE_DOI,
    _NATURE_NUMBERED,
    _NATURE_REFERENCE_COMPACT,
    _NATURE_BOOK_CHAPTER,
    _NATURE_BOOK,
    _NATURE_WEBSITE,
]
