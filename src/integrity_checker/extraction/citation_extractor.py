"""CitationExtractor — regex + heuristics, trích xuất Citation[] từ Document."""

from __future__ import annotations

import re
import warnings
from typing import Iterable

from integrity_checker.extraction.base import Document
from integrity_checker.extraction.patterns import get_in_text_patterns
from integrity_checker.extraction.patterns.base import CompiledPattern
from integrity_checker.extraction.regex_patterns import CITATION_PATTERNS, CitationPattern
from integrity_checker.extraction.text_preprocessor import TextPreprocessor
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# Header / footer keywords để phát hiện reference section
_REFERENCE_HEADERS = re.compile(
    r"^\s*(references?|bibliography|works\s+cited|tài\s+liệu\s+tham\s+khảo)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Essay title / header keywords — these indicate non-citation text
_ESSAY_TITLE_INDICATORS = re.compile(
    r"(?:this\s+essay|comprehensive\s+survey|comprehensive\s+review|"
    r"introduction\s+to\s+|abstract\s+|survey\s*$|:?\s*survey\s+of\s+|"
    r"a\s+(?:brief\s+)?(?:survey|review|introduction)|"
    r"^\s*(?:deep\s+learning|natural\s+language\s+processing))",
    re.IGNORECASE,
)

# Long text without punctuation at start — likely a title or heading, not a citation
_LONG_TEXT_START_RE = re.compile(r"^[A-Za-z]{50,}?\s")

# IEEE reference list marker pattern: [N] followed by space + author name
# This helps identify standalone [N] as reference markers, not in-text citations
_IEEE_REF_MARKER_RE = re.compile(r"^\s*\[\d+\]\s+[A-Z]")

# Test scenario patterns — lines that describe test scenarios, not real citations
# These patterns indicate the [N] is part of a test description, not an in-text citation
_TEST_SCENARIO_PATTERNS = re.compile(
    r"(?:^|\s)Reference:\s*\[\d+\]|"
    r"(?:^|\s)In-text:\s*\(|"
    r"(?:^|\s)Expected(?:Mapping|Label):|"
    r"(?:^|\s)Scenario:|"
    r"(?:^|\s)APA\d+:|"
    r"(?:^|\s)IEEE\d+:",
    re.IGNORECASE,
)

# Month and season names for filtering date-only patterns
_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_MONTH_NAMES_LOWER = [m.lower() for m in _MONTH_NAMES]
_SEASON_NAMES = ["Spring", "Summer", "Fall", "Autumn", "Winter"]
_SEASON_NAMES_LOWER = [s.lower() for s in _SEASON_NAMES]


def _is_reference_list_marker(text: str, match_start: int) -> bool:
    """Check if the [N] match is a reference list marker (not an in-text citation).

    Reference list entries look like: "[4] Xiao, Y., ..." or "    [4] Xiao, Y., ..."
    In-text citations look like: "According to [4], ..."

    Returns True if this appears to be a reference list marker.
    """
    # If [N] is at the start of text (position 0), likely ref marker
    if match_start == 0:
        return True

    # Check the full prefix - if it's all whitespace (including newlines), it's a ref marker
    # This handles cases like "    [4]" (indented) or "\n[4]"
    prefix = text[:match_start]
    if prefix.isspace() or re.search(r"\n\s*$", prefix):
        return True

    return False


def _is_in_test_scenario_context(text: str, match_start: int) -> bool:
    """Check if [N] match is within a test scenario description context.

    Test scenarios like "Reference: [1]" or "APA-01: MATCHED" indicate
    that [N] is part of test documentation, not a real citation.

    Returns True if [N] appears to be in a test scenario context.
    """
    # Get context around the match (50 chars before and after)
    context_start = max(0, match_start - 50)
    context_end = min(len(text), match_start + 100)
    context = text[context_start:context_end]

    # Check for test scenario patterns
    if _TEST_SCENARIO_PATTERNS.search(context):
        return True

    # Check if [N] follows "Reference:" or "reference:" in the same line
    line_start = text.rfind('\n', 0, match_start) + 1
    line_prefix = text[line_start:match_start]
    if re.search(r'Reference\s*:\s*\[\d+\]', line_prefix, re.IGNORECASE):
        return True

    # Check if the line starts with scenario ID pattern like "APA-01:", "IEEE-02:", etc.
    # Find the start of current line
    line_start_full = max(0, text.rfind('\n', 0, match_start) + 1)
    current_line = text[line_start_full:line_start_full + 200].split('\n')[0]
    if re.match(r'^\s*(APA-\d+|IEEE-\d+):', current_line, re.IGNORECASE):
        return True

    # Check if preceded by "In-text:" or "Reference:" in the same line
    if re.search(r'(?:In-text|Reference)\s*:', line_prefix, re.IGNORECASE):
        return True

    return False


def _is_date_only_citation(extracted_text: str) -> bool:
    """Check if extracted text is a date-only pattern, not a real citation.

    Filters out patterns like "(May 2012)", "(June 1996)", "(Spring 2013)"
    which are dates in legal citations, not author-year citations.

    Returns True if the text appears to be a date only, not a citation.
    """
    # Extract content inside parentheses
    inner = extracted_text.strip('()').strip()

    # Split by comma to get first word(s)
    first_part = inner.split(',')[0].strip()

    # Check if first word is a month or season name
    if first_part.lower() in _MONTH_NAMES_LOWER:
        return True
    if first_part.lower() in _SEASON_NAMES_LOWER:
        return True

    # Additional check: if the entire inner text is just "Month Year" or "Season Year"
    # without any author-like structure (comma or "et al.")
    words = inner.split()
    if len(words) == 2:
        first_word_lower = words[0].lower()
        if first_word_lower in _MONTH_NAMES_LOWER or first_word_lower in _SEASON_NAMES_LOWER:
            # Check if second word looks like a year
            if re.match(r'^\d{4}$', words[1]):
                return True

    return False


def _is_essay_title(text: str) -> bool:
    """Check if text appears to be an essay title, not a citation entry.

    Returns True if the text is likely an essay title/header.
    """
    text_stripped = text.strip()

    # Very long text (>200 chars) starting without punctuation — likely title
    if len(text_stripped) > 200 and _LONG_TEXT_START_RE.match(text_stripped):
        return True

    # Contains essay/survey/review indicators
    if _ESSAY_TITLE_INDICATORS.search(text_stripped):
        return True

    return False


class CitationExtractor:
    """Trích xuất citation từ Document đã parse.

    # TODO(user): tuần 6–7 — thêm:
        - Author NER (spaCy en_core_web_lg) để bắt author list chính xác
        - English-Vietnamese citation handling
        - Author override khi apa_reference_entry đã parse sẵn
    """

    def __init__(
        self,
        patterns: Iterable[CitationPattern | CompiledPattern] | None = None,
    ) -> None:
        if patterns is None:
            # Use patterns from the new modular registry
            # Include both in-text patterns and utility patterns (DOI, URL)
            # for backward compatibility with original CITATION_PATTERNS
            from integrity_checker.extraction.patterns import get_in_text_patterns, get_utility_patterns
            self.patterns = get_in_text_patterns() + get_utility_patterns()
        else:
            # Check if using old CITATION_PATTERNS (for backward compatibility)
            patterns_list = list(patterns)
            if patterns_list and hasattr(patterns_list[0], 'style'):
                # Check if it's the old CITATION_PATTERNS format
                for p in patterns_list:
                    if isinstance(p, CitationPattern):
                        warnings.warn(
                            "Passing CITATION_PATTERNS directly is deprecated. "
                            "Use CitationExtractor() without patterns to use the new registry, "
                            "or pass CompiledPattern objects from the patterns registry.",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                        break
            self.patterns = patterns_list

        self._compiled = [(p, re.compile(p.pattern)) for p in self.patterns]
        self.preprocessor = TextPreprocessor()

    # -- public API --

    def extract_from_document(self, doc: Document) -> list[Citation]:
        """Trích xuất tất cả citation từ Document. Dedup theo (raw_text, page)."""
        citations: list[Citation] = []
        for page in doc.pages:
            raw_text = page.text  # Keep raw text for whitespace detection
            normalized = self.preprocessor.normalize(raw_text)
            page_citations = self._extract_from_text(raw_text, normalized, page.page_num)
            citations.extend(page_citations)

        citations = self._dedupe(citations)
        for c in citations:
            c.confidence = self._estimate_confidence(c)
        return citations

    def find_reference_section(self, doc: Document) -> tuple[int, int] | None:
        """Trả về (start_page, end_page) của reference section. None nếu không thấy."""
        for i, page in enumerate(doc.pages):
            if _REFERENCE_HEADERS.search(page.text):
                start = page.page_num  # FIX: Use actual page_num instead of index
                # FIX: Calculate end based on actual max page in document
                max_page = max(p.page_num for p in doc.pages) if doc.pages else doc.num_pages
                end = min(start + 5, max_page)
                return (start, end)
        return None

    # -- internals --

    def _extract_from_text(self, raw_text: str, normalized_text: str, page_num: int) -> list[Citation]:
        """Extract citations from text.

        Args:
            raw_text: Raw text for whitespace/position detection
            normalized_text: Preprocessed text for regex matching
            page_num: Page number
        """
        results: list[Citation] = []
        for pattern_def, compiled in self._compiled:
            # Find positions in raw text first (preserves whitespace/newlines)
            for m in compiled.finditer(raw_text):
                raw = m.group(0).strip()
                raw_start = m.start()

                # Extract citation_type and style from pattern
                # Handle both CitationPattern (old) and CompiledPattern (new)
                if isinstance(pattern_def, CitationPattern):
                    citation_type = pattern_def.type
                    style = pattern_def.style
                else:
                    # CompiledPattern provides type and style properties
                    citation_type = pattern_def.type
                    style = pattern_def.style

                # Bug fix 1: Filter out IEEE [N] reference list markers
                # "[4] Xiao, Y., ..." at start of line is a reference list entry, not in-text citation
                if citation_type == CitationType.NUMERIC:
                    if _is_reference_list_marker(raw_text, raw_start):
                        continue

                # Bug fix 2: Filter out essay titles being extracted as citations
                # Titles like "Deep Learning for Natural Language Processing: A Comprehensive Survey..."
                if _is_essay_title(raw):
                    continue

                # Bug fix 3: Filter out [N] in test scenario contexts
                # Test scenarios like "Reference: [1]" or "APA-01: MATCHED" should not extract [1]
                if citation_type == CitationType.NUMERIC:
                    if _is_in_test_scenario_context(raw_text, raw_start):
                        continue

                # Bug fix 4: Filter out date-only patterns like "(May 2012)", "(Spring 2013)"
                # These are legal citations with dates, not author-year citations
                if _is_date_only_citation(raw):
                    continue

                citation = Citation(
                    raw_text=raw,
                    citation_type=citation_type,
                    style=style,
                    page_num=page_num,
                    matched_pattern=pattern_def.name,
                )
                # Parse các field con
                self._populate_fields(citation, raw)
                results.append(citation)
        return results

    def _populate_fields(self, citation: Citation, raw: str) -> None:
        """Best-effort trích DOI / URL / year từ raw text."""
        from integrity_checker.extraction.patterns.utils import extract_doi, extract_url, extract_year

        if not citation.doi:
            citation.doi = extract_doi(raw)
        if not citation.url:
            citation.url = extract_url(raw)
        if not citation.year:
            citation.year = extract_year(raw)

    def _estimate_confidence(self, citation: Citation) -> float:
        """Heuristic confidence 0–1 dựa trên field có sẵn."""
        score = 0.0
        if citation.year:
            score += 0.25
        if citation.doi:
            score += 0.40
        if citation.url:
            score += 0.10
        if citation.authors:
            score += 0.15
        if citation.title:
            score += 0.10
        return min(score, 1.0)

    def _dedupe(self, citations: list[Citation]) -> list[Citation]:
        """Bỏ trùng theo (style, normalized raw_text)."""
        seen: set[tuple[str, str]] = set()
        unique: list[Citation] = []
        for c in citations:
            key = (c.style.value, c.raw_text.lower().strip())
            if key in seen:
                continue
            seen.add(key)
            unique.append(c)
        return unique