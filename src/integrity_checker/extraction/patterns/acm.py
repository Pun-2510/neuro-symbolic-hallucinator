"""ACM (Association for Computing Machinery) citation format patterns and parser.

This module provides ACM citation format implementation for the
modular citation pattern system.

ACM Style Citations:
    In-text:
        - Numeric bracketed: [1], [2], [3]
        - Can also use APA-like: (Author, 2020) in some ACM templates

    Reference list:
        - Numbered list: [1] Authors. Title. Venue. Year.
        - Format: [N] Authors, "Title," Venue details, Year
        - Similar to IEEE but with different punctuation

Key characteristics:
    - Numeric bracketed citations
    - Similar to IEEE in many ways
    - Often uses full author names in references

Reference:
    https://www.acm.org/publications/proceedings-template
    https://doi.org/10.1145/3442188.3445922
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType
from integrity_checker.extraction.patterns.registry import register_format
from integrity_checker.matching.author_parser import parse_authors
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# =============================================================================
# ACM Pattern Definitions
# =============================================================================

# --- In-text ACM patterns ---

# Numeric bracketed: [1], [2], [3]
_ACM_NUMERIC = CompiledPattern.create(
    name="acm_numeric",
    pattern=r"\[(\d+)\]",
    pattern_type=PatternType.IN_TEXT,
    description="ACM numeric in-text: [1] | [2] | [3]",
)

# Numeric with comma: [1], [2], [3]
_ACM_NUMERIC_COMMA = CompiledPattern.create(
    name="acm_numeric_comma",
    pattern=r"\[(\d+(?:[,\s]+\d+)*)\]",
    pattern_type=PatternType.IN_TEXT,
    description="ACM numeric: [1], [2], [3] | [1, 2, 3]",
)

# Numeric range: [1-5]
_ACM_NUMERIC_RANGE = CompiledPattern.create(
    name="acm_numeric_range",
    pattern=r"\[(\d+(?:[,\s\-–]+\d+)*)\]",
    pattern_type=PatternType.IN_TEXT,
    description="ACM numeric range: [1-5] | [1, 2-5]",
)

# --- Reference list ACM patterns ---

# ACM reference with quoted title:
# [1] Authors, "Title," Venue details, Year.
_ACM_REFERENCE_ENTRY = CompiledPattern.create(
    name="acm_reference_entry",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'(?P<venue>.+?)(?:,?\s*\d{4}[a-z]?\.)?$'  # venue and optional year
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM reference: [N] Authors, \"Title,\" Venue, Year.",
)

# ACM conference paper:
# [N] Authors, "Title," in Conf. Name, Location, Year, pp. XX-XX.
_ACM_CONFERENCE = CompiledPattern.create(
    name="acm_conference",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'in\s+'  # in
        r'(?P<conference>[^,]+)'  # Conference name
        r'(?:,\s*(?P<location>[^,]+))?'  # Optional location
        r'(?:,\s*(?P<year>\d{4}))?'  # Optional year
        r'(?:,\s*pp?\.\s*(?P<pages>[\d–-]+))?'  # Optional pages
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM conference: [N] Authors, \"Title,\" in Conf. Name, Year.",
)

# ACM book:
# [N] Authors, Book Title. Publisher, Year.
_ACM_BOOK = CompiledPattern.create(
    name="acm_book",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'(?P<title>[^,]+),?\s*'  # Book title
        r'(?P<publisher>.+?),?\s*'  # Publisher
        r'(?P<year>\d{4})?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM book: [N] Authors, Book Title. Publisher, Year.",
)

# ACM book chapter:
# [N] Authors, "Chapter title," in Book Title, Publisher, Year, pp. XX-XX.
_ACM_BOOK_CHAPTER = CompiledPattern.create(
    name="acm_book_chapter",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'in\s+'  # in
        r'(?P<book_title>[^,]+)'  # Book title
        r'(?:,\s*(?P<publisher>[^,]+))?'  # Optional publisher
        r'(?:,\s*(?P<year>\d{4}))?'  # Optional year
        r'(?:,\s*pp?\.\s*(?P<pages>[\d–-]+))?'  # Optional pages
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM book chapter: [N] Authors, \"Title,\" in Book, Publisher, Year.",
)

# ACM journal article:
# [N] Authors. Title. Journal, vol. X, no. Y, pp. Z-Z, Year.
_ACM_JOURNAL = CompiledPattern.create(
    name="acm_journal",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?)\.\s*'  # Authors.
        r'(?P<title>.+?)\.\s*'  # Title.
        r'(?P<venue>.+?)'  # Venue
        r'(?:,\s*(?P<year>\d{4}))?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM journal: [N] Authors. Title. Journal, Year.",
)

# ACM tech report:
# [N] Authors, "Title," Tech. Rep., Institution, Year.
_ACM_TECH_REPORT = CompiledPattern.create(
    name="acm_tech_report",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?),?\s*'  # Authors
        r'[""](?P<title>[^""]+)[""],?\s*'  # "title,"
        r'(?P<type>Tech\.\s*Rep\.?|Technical\s+Report)'  # Type
        r'(?:,\s*(?P<institution>[^,]+))?'  # Optional institution
        r'(?:,\s*(?P<year>\d{4}))?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM tech report: [N] Authors, \"Title,\" Tech. Rep., Institution.",
)

# ACM with full name format (different from IEEE):
# [N] FirstName LastName and FirstName LastName. Title. Venue. Year.
_ACM_FULL_NAME = CompiledPattern.create(
    name="acm_full_name",
    pattern=(
        r'^\[\s*(?P<index>\d+)\s*\]\s*'  # [N]
        r'(?P<authors>.+?)\.\s*'  # Authors.
        r'(?P<title>.+?)\.\s*'  # Title.
        r'(?P<venue>.+?)'  # Venue
        r'(?:\s+(?P<year>\d{4}))?'  # Optional year
        r'\.?$'
    ),
    pattern_type=PatternType.REFERENCE_ENTRY,
    description="ACM full name: [N] FirstName LastName. Title. Venue. Year.",
)

# --- Utility pattern ---

_ACM_BRACKET_RE = CompiledPattern.create(
    name="acm_bracket_marker",
    pattern=r'^\s*\[\d+\]\s*',
    pattern_type=PatternType.UTILITY,
    description="ACM reference list marker: [N]",
)


# =============================================================================
# ACM Format Implementation
# =============================================================================


class ACMFormat:
    """ACM citation format implementation.

    ACM style is commonly used in:
        - Computer Science
        - Information Technology
        - Software Engineering
        - Computing conferences and journals

    Key characteristics:
        - Numeric bracketed citations
        - Similar to IEEE in many ways
        - Reference list uses [N] numbering
        - Can have full author names in references

    This implementation handles:
        - In-text numeric citations: [1], [2], [3]
        - Reference list entries for conferences, journals, books, tech reports
        - Both abbreviated and full name author formats
    """

    @property
    def name(self) -> str:
        """Format name."""
        return "ACM"

    @property
    def priority(self) -> int:
        """Priority for format resolution (higher = try first).

        ACM is common in CS but similar to IEEE.
        Priority 88 (slightly lower than IEEE since IEEE is more common).
        """
        return 88

    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting ACM in-text citations."""
        return [
            _ACM_NUMERIC_RANGE,
            _ACM_NUMERIC_COMMA,
            _ACM_NUMERIC,
        ]

    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting ACM reference list entries."""
        return [
            _ACM_REFERENCE_ENTRY,
            _ACM_CONFERENCE,
            _ACM_JOURNAL,
            _ACM_FULL_NAME,
            _ACM_BOOK_CHAPTER,
            _ACM_BOOK,
            _ACM_TECH_REPORT,
        ]

    def parse_reference_entry(self, text: str) -> Optional[Citation]:
        """Parse ACM reference entry into Citation object.

        Args:
            text: Raw reference entry text

        Returns:
            Citation object if successfully parsed, None otherwise

        Examples:
            >>> text = '[1] John Smith and Jane Doe. 2020. Article title. Journal 10, 2, 1-15.'
            >>> citation = ACMFormat().parse_reference_entry(text)
            >>> citation.authors
            ['John Smith', 'Jane Doe']
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

        # Try quote-based parsing first (most reliable for ACM with titles)
        citation = self._parse_acm_quote_based(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try conference format
        citation = self._try_parse_conference(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try journal format
        citation = self._try_parse_journal(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Try full name format
        citation = self._try_parse_full_name(text)
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

        # Try tech report format
        citation = self._try_parse_tech_report(text)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Fallback
        return self._parse_acm_fallback(text)

    def _parse_acm_quote_based(self, text: str) -> Optional[Citation]:
        """Parse ACM entry using quote-based heuristic."""
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
        title_raw = remainder[first_q + 1:close_q].strip().rstrip(',').strip()
        venue_year = remainder[close_q + 1:].strip().lstrip(',').strip()

        # Year usually at end
        year_m = re.search(r'\b((?:19|20)\d{2})([a-z]?)\b', venue_year)
        year = year_m.group(1) if year_m else None
        year_suffix = year_m.group(2) if year_m and year_m.group(2) else None

        citation = Citation(
            raw_text=text.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_quote_based',
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

    def _try_parse_conference(self, text: str) -> Optional[Citation]:
        """Try to parse ACM conference format."""
        match = _ACM_CONFERENCE.search(text)
        if match:
            return self._parse_conference_entry(match, text)
        return None

    def _try_parse_journal(self, text: str) -> Optional[Citation]:
        """Try to parse ACM journal format."""
        match = _ACM_JOURNAL.search(text)
        if match:
            return self._parse_journal_entry(match, text)
        return None

    def _try_parse_full_name(self, text: str) -> Optional[Citation]:
        """Try to parse ACM full name format."""
        match = _ACM_FULL_NAME.search(text)
        if match:
            return self._parse_full_name_entry(match, text)
        return None

    def _try_parse_book(self, text: str) -> Optional[Citation]:
        """Try to parse ACM book format."""
        match = _ACM_BOOK.search(text)
        if match:
            return self._parse_book_entry(match, text)
        return None

    def _try_parse_book_chapter(self, text: str) -> Optional[Citation]:
        """Try to parse ACM book chapter format."""
        match = _ACM_BOOK_CHAPTER.search(text)
        if match:
            return self._parse_book_chapter_entry(match, text)
        return None

    def _try_parse_tech_report(self, text: str) -> Optional[Citation]:
        """Try to parse ACM tech report format."""
        match = _ACM_TECH_REPORT.search(text)
        if match:
            return self._parse_tech_report_entry(match, text)
        return None

    def _parse_conference_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse ACM conference entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_conference',
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
        year_str = match.group('year')
        pages = match.group('pages')

        citation.venue = conference
        if location:
            citation.venue += f', {location.strip()}'

        if year_str:
            citation.year = year_str
        if pages:
            citation.pages = pages

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_journal_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse ACM journal entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_journal',
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
            citation.year = year_str

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_full_name_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse ACM full name entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_full_name',
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
            citation.year = year_str

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_book_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse ACM book entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_book',
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

        # Extract publisher and year
        publisher = match.group('publisher')
        year_str = match.group('year')

        if publisher:
            citation.venue = publisher.strip()
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_book_chapter_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse ACM book chapter entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_book_chapter',
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
        title = match.group('title').strip()
        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        # Extract book title (as venue)
        book_title = match.group('book_title').strip()
        publisher = match.group('publisher')
        year_str = match.group('year')
        pages = match.group('pages')

        citation.venue = book_title
        if publisher:
            citation.venue += f', {publisher.strip()}'
        if year_str:
            citation.year = year_str
        if pages:
            citation.pages = pages

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_tech_report_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse ACM tech report entry."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_tech_report',
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
        year_str = match.group('year')

        citation.venue = report_type
        if institution:
            citation.venue += f', {institution.strip()}'
        if year_str:
            citation.year = year_str

        # Extract DOI if present
        doi_m = re.search(r'10\.\d{4,9}/[^\s\]\)\,;]+', text)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip('.')

        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_acm_fallback(self, text: str) -> Optional[Citation]:
        """Fallback parser: extract whatever metadata possible."""
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.ACM,
            matched_pattern='acm_fallback',
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
        return citation if citation.title or citation.year else None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string

        Returns:
            List of author strings (via parse_authors)
        """
        return parse_authors(authors_str)

    def _parse_venue(self, citation: Citation, venue_text: str) -> None:
        """Parse venue information from remaining text."""
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
        venue_name_match = re.search(
            r'^(?P<venue>[^,]+?)(?:,\s*(?:vol\.|no\.|pp\.))', venue_text, re.IGNORECASE
        )
        if venue_name_match:
            citation.venue = venue_name_match.group('venue').strip()
        else:
            # Clean up venue
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
        """Check if text is a valid ACM citation.

        Args:
            text: Text to validate

        Returns:
            True if text matches ACM citation pattern, False otherwise
        """
        # Check for bracketed number pattern
        bracket_pattern = r'\[\d+(?:[,\s\-]+\d+)*\]'
        if re.match(bracket_pattern, text.strip()):
            return True

        # Check for reference entry pattern
        if re.match(r'^\s*\[\d+\]\s*', text):
            return True

        return False

    def is_reference_list_marker(self, text: str) -> bool:
        """Check if text is a reference list marker.

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

# Register ACM format when this module is imported
register_format(ACMFormat())


# =============================================================================
# Module-level pattern lists for convenience
# =============================================================================

ACM_IN_TEXT_PATTERNS = [
    _ACM_NUMERIC_RANGE,
    _ACM_NUMERIC_COMMA,
    _ACM_NUMERIC,
]

ACM_REFERENCE_PATTERNS = [
    _ACM_REFERENCE_ENTRY,
    _ACM_CONFERENCE,
    _ACM_JOURNAL,
    _ACM_FULL_NAME,
    _ACM_BOOK_CHAPTER,
    _ACM_BOOK,
    _ACM_TECH_REPORT,
]
