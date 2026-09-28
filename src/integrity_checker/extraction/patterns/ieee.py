"""IEEE citation format patterns and parser.

This module provides IEEE (Institute of Electrical and Electronics Engineers)
citation format implementation for the modular citation pattern system.

IEEE Style Citations:
    In-text:
        - Numeric bracketed: [1], [1,2], [1-5], [1, 2, 3]
        - Reference list markers: [N] format

    Reference list:
        Format: [N] Authors, "Title," Journal, vol. X, no. Y, pp. Z-Z, Mon. Year
        Handles: journal articles, conference papers, books, tech reports

Reference:
    https://ieee-dataport.org/sites/default/files/analysis/27/
    IEEE%20Reference%20Guide%20(updated)%20-%20Final.pdf
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType
from integrity_checker.extraction.patterns.registry import register_format
from integrity_checker.matching.author_parser import parse_authors
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# =============================================================================
# IEEE Pattern Definitions
# =============================================================================

# --- In-text IEEE patterns ---

# IEEE numeric: [1], [1,2], [1-5], [1, 2, 3]
_IEEE_NUMERIC = CompiledPattern.create(
    name="ieee_numeric",
    pattern=r"\[(\d+(?:[,\s\-]+\d+)*)\]",
    pattern_type=PatternType.IN_TEXT,
    description="IEEE numeric in-text: [1] | [1,2] | [1-5] | [1, 2, 3]",
)

# --- Reference list IEEE patterns ---

# IEEE reference entry with full metadata extraction
# Format: [N] Authors, "Title," Venue details, Year.
# Using character class to match both straight and curly quotes
_IEEE_REFERENCE_ENTRY = CompiledPattern.create(
    name="ieee_reference_entry",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'(?P<venue>.+?)(?:,?\s*\d{4}[a-z]?\.)?$'  # venue and optional year
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="IEEE reference entry: [N] Authors, \"Title,\" Venue...",
)

# IEEE entry with year at end: Authors, "Title," Venue, Year
_IEEE_REFERENCE_YEAR_END = CompiledPattern.create(
    name="ieee_reference_year_end",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'(?P<venue>.+?),?\s*'  # Venue
        r'(?P<year>\d{4}[a-z]?)\.?$'  # Year at end
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="IEEE entry with year at end: Authors, \"Title,\" Venue, 2020.",
)

# IEEE book reference: Authors, "Chapter title," in Book Title, Publisher, Year.
_IEEE_BOOK_CHAPTER = CompiledPattern.create(
    name="ieee_book_chapter",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "chapter title,"
        r'in\s+'  # "in"
        r'(?P<book_title>[^,]+)'  # Book title
        r'(?:,\s*(?P<publisher>[^,]+))?'  # Optional publisher
        r'(?:,\s*(?P<year>\d{4}[a-z]?))?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="IEEE book chapter: Authors, \"Title,\" in Book Title, Publisher.",
)

# IEEE technical report: Authors, "Title," Tech. Rep., Institution, Year.
_IEEE_TECH_REPORT = CompiledPattern.create(
    name="ieee_tech_report",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'(?P<type>Tech\.\s*Rep\.?|Technical\s+Report)'  # Type
        r'(?:,\s*(?P<institution>[^,]+))?'  # Optional institution
        r'(?:,\s*(?P<year>\d{4}[a-z]?))?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="IEEE tech report: Authors, \"Title,\" Tech. Rep., Institution.",
)

# IEEE conference paper: Authors, "Title," in Conf. Name, Location, Year.
_IEEE_CONFERENCE = CompiledPattern.create(
    name="ieee_conference",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'in\s+'  # "in"
        r'(?P<conference>[^,]+)'  # Conference name
        r'(?:,\s*(?P<location>[^,]+))?'  # Optional location
        r'(?:,\s*(?P<year>\d{4}[a-z]?))?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="IEEE conference: Authors, \"Title,\" in Conf. Name, Location.",
)

# --- Utility pattern for detecting reference list marker [N] ---

_IEEE_BRACKET_RE = CompiledPattern.create(
    name="ieee_bracket_marker",
    pattern=r'^\s*\[\d+\]\s*',
    pattern_type=PatternType.UTILITY,
    description="IEEE reference list marker: [N]",
)


# =============================================================================
# IEEE Format Implementation
# =============================================================================


class IEEEFormat:
    """IEEE citation format implementation.

    IEEE style is commonly used in:
        - Engineering
        - Computer Science
        - Electronics
        - Physics

    This implementation handles:
        - In-text numeric citations: [1], [1,2], [1-5]
        - Reference list entries with full metadata extraction
        - Journal articles: [N] Authors, "Title," Journal, vol. X, pp. Z-Z, Year.
        - Conference papers: [N] Authors, "Title," in Conf. Name, Year.
        - Books: [N] Authors, Book Title. Publisher, Year.
        - Book chapters: [N] Authors, "Title," in Book Title, Publisher, Year.
        - Technical reports: [N] Authors, "Title," Tech. Rep., Institution, Year.
    """

    @property
    def name(self) -> str:
        """Format name."""
        return "IEEE"

    @property
    def priority(self) -> int:
        """Priority for format resolution (higher = try first).

        IEEE is common in CS/Engineering papers.
        Priority 90 (after APA at 100).
        """
        return 90

    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting IEEE in-text citations."""
        return [
            _IEEE_NUMERIC,
        ]

    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting IEEE reference list entries."""
        return [
            _IEEE_REFERENCE_ENTRY,
            _IEEE_REFERENCE_YEAR_END,
            _IEEE_BOOK_CHAPTER,
            _IEEE_TECH_REPORT,
            _IEEE_CONFERENCE,
        ]

    def parse_reference_entry(self, text: str) -> Optional[Citation]:
        """Parse IEEE reference entry into Citation object.

        Args:
            text: Raw reference entry text

        Returns:
            Citation object if successfully parsed, None otherwise

        Examples:
            >>> text = '[1] S. J. Pan and Q. Yang, "A Survey on Transfer Learning," IEEE Trans. Knowl. Data Eng., vol. 22, no. 10, pp. 1345-1359, 2010.'
            >>> citation = IEEEFormat().parse_reference_entry(text)
            >>> citation.authors
            ['S. J. Pan', 'Q. Yang']
            >>> citation.title
            'A Survey on Transfer Learning'
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Extract numeric index first
        numeric_index = None
        idx_match = re.search(r'\[\s*(\d+)\s*\]', text)
        if idx_match:
            numeric_index = int(idx_match.group(1))

        # Try quote-based parsing first (most reliable for IEEE)
        citation = self._parse_ieee_quote_based(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try pattern-based parsing
        patterns_to_try = [
            (_IEEE_REFERENCE_ENTRY, self._parse_ieee_entry),
            (_IEEE_REFERENCE_YEAR_END, self._parse_ieee_year_end_entry),
            (_IEEE_BOOK_CHAPTER, self._parse_ieee_book_chapter_entry),
            (_IEEE_TECH_REPORT, self._parse_ieee_tech_report_entry),
            (_IEEE_CONFERENCE, self._parse_ieee_conference_entry),
        ]

        for pattern, parser_func in patterns_to_try:
            match = pattern.search(text)
            if match:
                citation = parser_func(match, text)
                if citation:
                    if numeric_index and citation.numeric_index is None:
                        citation.numeric_index = numeric_index
                    return citation

        # Fallback: try to extract whatever we can
        return self._parse_ieee_fallback(text)

    def _parse_ieee_quote_based(self, text: str) -> Optional[Citation]:
        """Parse IEEE entry using quote-based heuristic.

        Strategy: Split on quote marks (regex title extraction may fail because
        commas can appear in titles). Uses split-based heuristic.

        This is the same approach used in reference_parser.py.
        """
        # Match [N] at start
        idx_m = re.match(r'\[\s*(\d+)\s*\]\s*', text)
        if not idx_m:
            return None
        numeric_index = int(idx_m.group(1))
        remainder = text[idx_m.end():]

        # Find first quote pair (supports " and unicode "")
        quote_chars_open = ['"', '"', '"']

        first_q = None
        for i, c in enumerate(remainder):
            if c in quote_chars_open:
                first_q = i
                break

        if first_q is None:
            return None

        close_q = None
        quote_close_chars = ['"', '"', '"']
        for j in range(first_q + 1, len(remainder)):
            if remainder[j] in quote_close_chars:
                close_q = j
                break

        if close_q is None:
            return None

        authors_part = remainder[:first_q].strip().rstrip(',').rstrip()
        title_raw = remainder[first_q + 1:close_q].strip().rstrip(',').rstrip()
        venue_year = remainder[close_q + 1:].strip().lstrip(',').strip()

        # Year usually at end of venue_year
        year_m = re.search(r'\b((?:19|20)\d{2})([a-z]?)\b', venue_year)
        year = year_m.group(1) if year_m else None
        year_suffix = year_m.group(2) if year_m and year_m.group(2) else None

        citation = Citation(
            raw_text=text.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='ieee_quote_based',
            numeric_index=numeric_index,
            title=title_raw,
            title_normalized=self._normalize_title(title_raw),
            year=year,
            year_suffix=year_suffix,
            venue=venue_year,
            authors=self._parse_authors(authors_part),
        )

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        # Parse venue components
        self._parse_venue(citation, venue_year)

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_ieee_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse standard IEEE reference entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='ieee_reference_entry',
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

        # Extract venue
        venue = match.group('venue').strip()
        self._parse_venue(citation, venue)

        # Extract year
        year_m = re.search(r'\b((?:19|20)\d{2})([a-z]?)\b', venue)
        if year_m:
            citation.year = year_m.group(1)
            citation.year_suffix = year_m.group(2) if year_m.group(2) else None

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_ieee_year_end_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse IEEE entry with year at end."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='ieee_reference_year_end',
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

        # Extract venue
        venue = match.group('venue').strip()
        self._parse_venue(citation, venue)

        # Extract year
        year_str = match.group('year')
        if year_str:
            year_m = re.search(r'(\d{4})([a-z]?)', year_str)
            if year_m:
                citation.year = year_m.group(1)
                citation.year_suffix = year_m.group(2) if year_m.group(2) else None

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_ieee_book_chapter_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse IEEE book chapter entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='ieee_book_chapter',
        )

        # Extract numeric index
        index = match.group('index')
        if index:
            citation.numeric_index = int(index)

        # Extract authors
        authors_str = match.group('authors')
        if authors_str:
            citation.authors = self._parse_authors(authors_str)

        # Extract chapter title
        chapter_title = match.group('title').strip()
        citation.title = chapter_title
        citation.title_normalized = self._normalize_title(chapter_title)

        # Extract book title (stored in venue as "In Book Title")
        book_title = match.group('book_title').strip()
        publisher = match.group('publisher')
        citation.venue = f'In {book_title}' + (f'. {publisher.strip()}' if publisher else '')

        # Extract year
        year_str = match.group('year')
        if year_str:
            year_m = re.search(r'(\d{4})([a-z]?)', year_str)
            if year_m:
                citation.year = year_m.group(1)
                citation.year_suffix = year_m.group(2) if year_m.group(2) else None

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_ieee_tech_report_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse IEEE technical report entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='ieee_tech_report',
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

        # Build venue from type and institution
        report_type = match.group('type').strip()
        institution = match.group('institution')
        citation.venue = report_type
        if institution:
            citation.venue += f', {institution.strip()}'

        # Extract year
        year_str = match.group('year')
        if year_str:
            year_m = re.search(r'(\d{4})([a-z]?)', year_str)
            if year_m:
                citation.year = year_m.group(1)
                citation.year_suffix = year_m.group(2) if year_m.group(2) else None

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_ieee_conference_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse IEEE conference paper entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='ieee_conference',
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

        # Build venue from conference and location
        conference = match.group('conference').strip()
        location = match.group('location')
        citation.venue = conference
        if location:
            citation.venue += f', {location.strip()}'

        # Extract year
        year_str = match.group('year')
        if year_str:
            year_m = re.search(r'(\d{4})([a-z]?)', year_str)
            if year_m:
                citation.year = year_m.group(1)
                citation.year_suffix = year_m.group(2) if year_m.group(2) else None

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_ieee_fallback(self, text: str) -> Optional[Citation]:
        """Fallback parser: extract whatever metadata possible from unstructured text."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern='fallback_ieee_entry',
        )

        # Extract numeric index
        idx_match = re.search(r'\[\s*(\d+)\s*\]', text)
        if idx_match:
            citation.numeric_index = int(idx_match.group(1))

        # Try to extract year
        year_m = re.search(r'\b((?:19|20)\d{2})([a-z]?)\b', text)
        if year_m:
            citation.year = year_m.group(1)
            if year_m.group(2):
                citation.year_suffix = year_m.group(2)

        # Try to extract title from quoted text
        quote_m = re.search(r'["""]([^""""]+)["""]', text)
        if quote_m:
            title = quote_m.group(1).strip()
            citation.title = title
            citation.title_normalized = self._normalize_title(title)

        # Extract DOI
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        # Only return if we have meaningful data
        return citation if citation.title or citation.year else None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string like "S. J. Pan and Q. Yang"

        Returns:
            List of author strings (via parse_authors)
        """
        return parse_authors(authors_str)

    def _parse_venue(self, citation: Citation, venue_text: str) -> None:
        """Parse venue information from remaining text.

        Handles:
        - Journal with volume and issue: "IEEE Trans. Knowl. Data Eng., vol. 22, no. 10, pp. 1345-1359"
        - Conference: "Proc. IEEE Int. Conf. Data Mining"
        - With pages: "pp. 1345-1359"
        """
        if not venue_text:
            return

        venue_text = venue_text.strip()

        # Extract volume: "vol. 22" or "vol. 22, no. 10"
        vol_match = re.search(
            r'(?:^|,?\s*)vol\.\s*(?P<vol>\d+[A-Z]?)', venue_text, re.IGNORECASE
        )
        if vol_match:
            citation.volume = vol_match.group('vol')

        # Extract issue: "no. 10"
        issue_match = re.search(
            r'(?:^|,?\s*)no\.\s*(?P<issue>\d+)', venue_text, re.IGNORECASE
        )
        if issue_match:
            citation.issue = issue_match.group('issue')

        # Extract pages: "pp. 1345-1359" or "p. 42"
        pages_match = re.search(
            r'(?:^|,?\s*)(?:pp?\.\s*)?(?P<pages>[\d–-]+)', venue_text, re.IGNORECASE
        )
        if pages_match:
            citation.pages = pages_match.group('pages')

        # Extract venue name (before volume/issue/pages)
        # Pattern: everything before ", vol." or ", no." or ", pp."
        venue_name_match = re.search(
            r'^(?P<venue>[^,]+?)(?:,\s*(?:vol\.|no\.|pp\.))', venue_text, re.IGNORECASE
        )
        if venue_name_match:
            citation.venue = venue_name_match.group('venue').strip()
        else:
            # No volume - try to extract just the journal/conference name
            # Remove year and DOI from venue
            clean_venue = re.sub(r'\d{4}[a-z]?\s*$', '', venue_text).strip()
            doi_match = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', clean_venue)
            if doi_match:
                clean_venue = clean_venue[:doi_match.start()].strip()
            if clean_venue:
                citation.venue = clean_venue.rstrip('.,')

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
        """Check if text is a valid IEEE citation.

        Args:
            text: Text to validate

        Returns:
            True if text matches IEEE citation pattern, False otherwise
        """
        # Check for bracketed number pattern
        bracket_pattern = r'\[\d+(?:[,\s\-]+\d+)*\]'
        if re.match(bracket_pattern, text.strip()):
            return True

        # Check for reference entry pattern
        if re.match(r'^\s*\[\d+\]\s*', text):
            # Should have quoted title
            if re.search(r'["""].+["""]', text):
                return True

        return False

    def is_reference_list_marker(self, text: str) -> bool:
        """Check if text is a reference list marker [N].

        This is used for filtering out markers during citation extraction.

        Args:
            text: Text to check

        Returns:
            True if text is a reference list marker, False otherwise
        """
        # Match standalone [N] at start of text
        if re.match(r'^\s*\[\d+\]\s*$', text):
            return True

        # Match [N] followed by space and lowercase (not a new entry)
        if re.match(r'^\s*\[\d+\]\s+[a-z]', text):
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
    _IEEE_NUMERIC,
]

IEEE_REFERENCE_PATTERNS = [
    _IEEE_REFERENCE_ENTRY,
    _IEEE_REFERENCE_YEAR_END,
    _IEEE_BOOK_CHAPTER,
    _IEEE_TECH_REPORT,
    _IEEE_CONFERENCE,
]

IEEE_UTILITY_PATTERNS = [
    _IEEE_BRACKET_RE,
]
