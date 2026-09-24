"""ReferenceListParser — parse các entry ở cuối bài (References section).

Hỗ trợ (v1.2 §3.4):
    - APA-like: 'Smith, J. (2020). Title. Journal A, 10(2), 1-10. DOI: ...'
    - IEEE-like: '[1] Smith, J., "Title," Journal A, vol. 10, 2020.'
    - Vancouver: 'Smith J. Title. Journal A. 2020;10:1-10.'
    - Chicago author-date: tương tự APA

Output:
    Citation với citation_type=REFERENCE_LIST và:
        - authors: list[str] (raw, dùng author_parser để canonicalize ở pipeline)
        - year + year_suffix
        - title (string)
        - title_normalized (cho duplicate detector)
        - venue
        - doi, url
        - numeric_index (cho IEEE-like)
        - order_index (vị trí trong bibliography)

References:
    v1.2 §3.4 (Reference list parsing)
    v1.2 §3.5 (bidirectional linking — cần title_normalized)
    v1.2 §4.3 (annotation guideline — reference variants)
    config.linking.duplicate_detection.title_year_author_similarity
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

from integrity_checker.extraction.base import Document
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.matching.author_parser import parse_authors
from integrity_checker.models.citation import Citation, CitationStyle, CitationType

logger = logging.getLogger(__name__)


# --- Regex patterns ---

# APA entry: authors block + (year) + . + title + . + venue + ... + DOI
_APA_ENTRY_RE = re.compile(
    r"""
    ^(?P<authors>.+?)                # authors block (lazy)
    \s*\(\s*(?P<year>\d{4})(?P<suffix>[a-z])?\s*\)
    \.?\s*
    (?P<title>[^\.]+?)               # title (up to first period — may include colons)
    \.\s*
    (?P<venue>.+?)                   # venue + volume + pages + DOI
    $
    """,
    re.VERBOSE | re.MULTILINE,
)

# IEEE entry: [N] authors, "title," venue, ...
# Tách theo dấu phẩy: phần trước quote-title là authors+initials, sau là venue.
_IEEE_ENTRY_RE = re.compile(
    r"""
    ^\[\s*(?P<index>\d+)\s*\]\s*      # [N]
    (?P<authors>[^"]+?),\s*           # authors (everything until quote)
    ["“](?P<title>[^"”]+)["”]\s*,\s*   # "title,"
    (?P<venue>.+?)$                   # venue (rest of line)
    """,
    re.VERBOSE,
)

# Vancouver: "Smith J. Title. Journal. 2020;10:1-10."
_VANCOUVER_ENTRY_RE = re.compile(
    r"""
    ^(?P<authors>.+?)\.\s+              # authors (everything up to first period)
    (?P<title>.+?)\.\s+                 # title (up to next period)
    (?P<venue>.+?)\.\s+                 # venue (up to next period)
    (?P<year>\d{4})(?P<rest>.*)$         # year + rest
    """,
    re.VERBOSE,
)

# DOI regex (tách riêng vì có thể xuất hiện ở cuối nhiều style)
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\]\)\,;]+")
_URL_RE = re.compile(r"https?://[^\s\]\)\,;]+")
_YEAR_RE = re.compile(r"\b((?:19|20)\d{2})([a-z]?)\b")

# Essay title indicators — entries matching these should be filtered out
_ESSAY_TITLE_RE = re.compile(
    r"(?:this\s+essay|comprehensive\s+survey|comprehensive\s+review|"
    r"introduction\s+to\s+|abstract\s+|survey\s*$|:?\s*survey\s+of\s+|"
    r"a\s+(?:brief\s+)?(?:survey|review|introduction)|"
    r"^\s*(?:deep\s+learning|natural\s+language\s+processing))",
    re.IGNORECASE,
)

# Long text without year — likely not a citation entry
_LONG_TEXT_NO_YEAR_RE = re.compile(r"^[A-Za-z]{50,}")


def _is_essay_title_entry(entry: str) -> bool:
    """Check if a reference entry is actually an essay title or header, not a citation.

    Returns True if the entry should be filtered out.
    """
    text_stripped = entry.strip()

    # Very long text without year — likely a title or header
    if len(text_stripped) > 200 and _LONG_TEXT_NO_YEAR_RE.match(text_stripped):
        return True

    # Contains essay/survey/review indicators
    if _ESSAY_TITLE_RE.search(text_stripped):
        return True

    return False


def _normalize_title(title: str) -> str:
    """Chuẩn hoá title: lowercase, bỏ punctuation, gộp spaces."""
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


class ReferenceListParser:
    """Parse danh sách References ở cuối tiểu luận."""

    def __init__(self, extractor: CitationExtractor | None = None) -> None:
        self.extractor = extractor or CitationExtractor()

    def parse_reference_section(self, doc: Document) -> list[Citation]:
        """Trích và parse các entry ở reference section.

        Returns:
            List[Citation] với citation_type = REFERENCE_LIST.

        Note:
            Section text KHÔNG qua TextPreprocessor.normalize đầy đủ vì
            _fix_broken_lines có thể nối "References\nvan" → "References van"
            (false positive khi 's' cuối + '\n' + 'v' đầu). Thay vào đó chỉ
            áp dụng normalize nhẹ (Unicode NFC + ligature).
        """
        ref_range = self.extractor.find_reference_section(doc)
        if ref_range is None:
            return []
        start, end = ref_range
        raw_text = "\n".join(p.text for p in doc.pages if start <= p.page_num <= end)
        # Light normalize — KHÔNG qua _fix_broken_lines
        pp = self.extractor.preprocessor
        section_text = pp._normalize_unicode(pp._fix_ligatures(raw_text))

        entries = self._split_entries(section_text)
        citations: list[Citation] = []
        for idx, entry in enumerate(entries, start=1):
            # Bug fix: Filter out essay title/header entries (not actual citations)
            if _is_essay_title_entry(entry):
                logger.debug(f"Skipping essay title entry: {entry[:50]}...")
                continue
            citation = self._parse_entry(entry, order_index=idx, page_num=start)
            if citation:
                citations.append(citation)
        return citations

    def _split_entries(self, text: str) -> list[str]:
        """Tách các entry riêng.

        Strategy (fallback nhiều tầng):
            1. Bỏ prefix "References" / "Tài liệu tham khảo" / "Bibliography".
            2. Nếu có dòng bắt đầu bằng `[N]` → IEEE entries (từng dòng).
            3. Tách IEEE entries trên cùng dòng (do PDF wrapping): [N]...[M]...
            4. Merge wrapped lines, rồi tách bằng year-marker boundary.
            5. Fallback: tách bằng blank line.
            6. Nếu vẫn chỉ 1 entry → trả nguyên text.
        """
        # 1. Strip header prefix
        header_strip_re = re.compile(
            r"^\s*(?:references?|bibliography|tài\s+liệu\s+tham\s+khảo"
            r"|danh\s+mục\s+tài\s+liệu|works?\s+cited)\s*[:.]?\s*",
            flags=re.IGNORECASE,
        )
        text = header_strip_re.sub("", text, count=1).strip()

        if not text:
            return []

        # 2. IEEE entries (each on separate line)
        if re.search(r"^\s*\[\d+\]", text, flags=re.MULTILINE):
            entries: list[str] = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^\[\d+\]", line):
                    if entries and entries[-1]:
                        pass
                    entries.append(line)
                else:
                    if entries:
                        entries[-1] = entries[-1] + " " + line
            result = [e for e in entries if len(e) > 20]
            if len(result) >= 2:
                # FIX: Check if any entries contain multiple [N] references (inline merge)
                # Split them using _split_ieee_inline
                final_entries = []
                for entry in result:
                    sub_entries = self._split_ieee_inline(entry)
                    if len(sub_entries) >= 2:
                        final_entries.extend(sub_entries)
                    else:
                        final_entries.append(entry)
                return final_entries if len(final_entries) >= 2 else result
            return result

        # 3. FIX: Split IEEE entries that are on the same line (PDF wrapping issue)
        # Pattern: [N] ... [M] ... where each [N] starts a new entry
        # This handles cases like: [9] ... 2010. [10] ... 2020.
        ieee_inline_split = self._split_ieee_inline(text)
        if len(ieee_inline_split) >= 2:
            return ieee_inline_split

        # 4. Merge wrapped lines + year-marker boundary split
        entries = self._split_by_year_boundary(text)
        if len(entries) >= 2:
            return entries

        # 5. Fallback: blank-line split
        merged = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = re.split(r"\n\s*\n", merged)
        result = [p.strip() for p in parts if len(p.strip()) > 20]
        if len(result) >= 2:
            return result

        # 6. Chỉ 1 entry
        return [text] if len(text) > 20 else []

    def _split_ieee_inline(self, text: str) -> list[str]:
        """Split IEEE entries that are on the same line due to PDF text wrapping.

        Pattern: [N] ... [M] ... where each [N] starts a new entry.
        This handles cases like:
            [9] S. J. Pan and Q. Yang. "A Survey..." IEEE Transactions, 2010. [10] F. Pan et al. "Transfer Learning..." 2020.

        Returns list of individual entries.
        """
        # Pattern: [N] followed by text, then [M] (a new entry)
        # Split at: ] followed by space and capital letter (start of next entry)
        # But be careful not to split inside quotes

        # Find all [N] positions
        bracket_pattern = re.compile(r'\[\d+\]')
        matches = list(bracket_pattern.finditer(text))

        if len(matches) < 2:
            return []

        # Build entries by splitting at [N] positions
        entries = []
        for i, m in enumerate(matches):
            start = m.start()
            # Find the end of this entry (start of next [N] or end of text)
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)

            entry = text[start:end].strip()
            # Clean up: remove leading whitespace and period before [
            entry = re.sub(r'^\s*\.\s*', '', entry)
            entry = re.sub(r'\s+', ' ', entry)

            if len(entry) > 20:
                entries.append(entry)

        return entries if len(entries) >= 2 else []

    def _split_by_year_boundary(self, text: str) -> list[str]:
        """Tach entries bang DOI URL boundaries.

        Algorithm:
            1. Merge wrapped author lines (lowercase continuation).
            2. Tim DOI URL boundaries, split tai do.
            3. Trim trailing DOI URLs, replace newlines with spaces.
            4. Neu 2+ entries -> tra ve. Fallback -> year markers.
        """
        # Step 1: Merge wrapped author lines
        merged_lines: list[str] = []
        current = ""
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                if current:
                    merged_lines.append(current)
                    current = ""
            elif re.match(r"^[a-zà-ỳ]", stripped):
                current = (current + " " + stripped).strip()
            else:
                if current:
                    merged_lines.append(current)
                current = stripped
        if current:
            merged_lines.append(current)
        merged_text = "\n".join(merged_lines)

        # Step 2: Tim DOI URL boundaries
        doi_url_re = re.compile(r"(doi\.org/10\.[^\s\n]+)(\n)?", flags=re.IGNORECASE)
        matches = list(doi_url_re.finditer(merged_text))
        if len(matches) >= 1:
            entries: list[str] = []
            start = 0
            for m in matches:
                end = m.end()
                chunk = merged_text[start:end].strip()
                if len(chunk) > 20:
                    entries.append(chunk)
                start = end
            # Last chunk (after last DOI URL)
            last_chunk = merged_text[start:].strip()
            if len(last_chunk) > 20:
                entries.append(last_chunk)

            if len(entries) >= 2:
                return entries

        # Step 3: Fallback - split on year markers
        return self._split_by_year_fallback(merged_text)

    def _split_by_year_fallback(self, text: str) -> list[str]:
        """Fallback: split reference list by newline boundaries.

        This method is called when DOI/URL-based splitting fails.
        Each reference entry is on its own line (or separated by blank lines).
        Returns list of entries.
        """
        # Split by blank lines first (paragraph-style)
        parts = re.split(r"\n\s*\n", text)
        if len(parts) >= 2:
            result = [p.strip() for p in parts if len(p.strip()) > 20]
            if len(result) >= 2:
                return result

        # Split by newlines - each line is likely an entry
        lines = text.split("\n")
        entries: list[str] = []
        current = ""

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Blank line - end current entry if any
                if current:
                    entries.append(current.strip())
                    current = ""
            elif re.match(r"^[A-Z][a-zÀ-ž]", stripped):
                # Line starts with uppercase - new entry
                if current:
                    entries.append(current.strip())
                current = stripped
            else:
                # Continuation line (wrapped text) - append to current
                current = (current + " " + stripped).strip()

        # Don't forget the last entry
        if current.strip():
            entries.append(current.strip())

        # Filter out very short entries (likely not citations)
        result = [e for e in entries if len(e) > 20]

        return result if len(result) >= 2 else []

    def _parse_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Parse 1 entry. Thử lần lượt APA, IEEE, Vancouver."""
        # Normalize: replace newlines with spaces (wrapped lines)
        entry = entry.replace("\n", " ").replace("  ", " ")

        # FIX: Extract numeric_index first if entry starts with [N] prefix
        numeric_index = None
        idx_match = re.match(r"^\[\s*(\d+)\s*\]", entry)
        if idx_match:
            numeric_index = int(idx_match.group(1))

        # IEEE first (vì có marker [N] đặc trưng)
        if re.match(r"^\s*\[\d+\]", entry):
            citation = self._parse_ieee_entry(entry, order_index, page_num)
            if citation and numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            if citation:
                return citation

        citation = self._parse_apa_entry(entry, order_index, page_num)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # Vancouver last — heuristic loose
        citation = self._parse_vancouver_entry(entry, order_index, page_num)
        if citation:
            if numeric_index and citation.numeric_index is None:
                citation.numeric_index = numeric_index
            return citation

        # FIX: Fallback - create citation with numeric_index if available
        # and extract whatever metadata we can from the raw entry
        if numeric_index is not None:
            citation = self._parse_fallback_entry(
                entry, numeric_index, order_index, page_num
            )
            if citation:
                return citation

        return None

    # -- per-style parsers --

    def _parse_apa_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        m = _APA_ENTRY_RE.search(entry)
        if not m:
            return None

        # FIX: Extract numeric_index if entry starts with [N] prefix (APA with numbering)
        numeric_index = None
        idx_match = re.match(r"^\[\s*(\d+)\s*\]", entry)
        if idx_match:
            numeric_index = int(idx_match.group(1))

        citation = Citation(
            raw_text=entry.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            page_num=page_num,
            matched_pattern="apa_reference_entry",
            order_index=order_index,
            numeric_index=numeric_index,  # FIX: Set numeric_index for APA entries with [N]
        )
        citation.year = m.group("year")
        suffix = m.group("suffix")
        citation.year_suffix = suffix if suffix else None
        title = m.group("title").strip().rstrip(".")
        citation.title = title
        citation.title_normalized = _normalize_title(title)
        citation.venue = m.group("venue").strip().rstrip(".")
        citation.authors = parse_authors(m.group("authors"))
        # DOI
        doi_m = _DOI_RE.search(entry)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip(".")
        return citation

    def _parse_ieee_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Parse 1 IEEE entry: '[N] authors, "title," venue, year.'

        Strategy: split trên quote marks (regex title có thể fail vì
        dấu phẩy trong title). Dùng split-based heuristic.
        """
        # Match [N] đầu dòng
        idx_m = re.match(r"^\[\s*(\d+)\s*\]\s*", entry)
        if not idx_m:
            return None
        remainder = entry[idx_m.end():]

        # Tìm cặp quote đầu tiên (mở + đóng) — hỗ trợ " và unicode “”
        quote_chars_open = '"“'
        quote_chars_close = '"”'

        first_q: int | None = None
        for i, c in enumerate(remainder):
            if c in quote_chars_open:
                first_q = i
                break
        if first_q is None:
            return None

        close_q: int | None = None
        for j in range(first_q + 1, len(remainder)):
            if remainder[j] in quote_chars_close:
                close_q = j
                break
        if close_q is None:
            return None

        authors_part = remainder[:first_q].strip().rstrip(",").rstrip()
        title_raw = remainder[first_q + 1:close_q].strip().rstrip(",").rstrip()
        venue_year = remainder[close_q + 1:].strip().lstrip(",").strip()

        # Year thường ở cuối venue_year
        year_m = _YEAR_RE.search(venue_year)
        year = year_m.group(1) if year_m else None
        suffix = year_m.group(2) if year_m and year_m.group(2) else None

        citation = Citation(
            raw_text=entry.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            page_num=page_num,
            matched_pattern="ieee_reference_entry",
            order_index=order_index,
            numeric_index=int(idx_m.group(1)),
        )
        citation.year = year
        citation.year_suffix = suffix
        citation.title = title_raw
        citation.title_normalized = _normalize_title(title_raw)
        citation.venue = venue_year
        citation.authors = parse_authors(authors_part)

        doi_m = _DOI_RE.search(entry)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip(".")
        return citation

    def _parse_fallback_entry(
        self, entry: str, numeric_index: int, order_index: int, page_num: int
    ) -> Citation | None:
        """Fallback parser: extract whatever metadata possible from an unparseable entry.

        Handles IEEE-style entries that lack quoted titles, or have unusual formatting.
        Extracts: numeric_index, DOI/arXiv, year, authors, venue, and a best-effort title.
        """
        text = entry.strip()

        # Extract DOI if present
        doi_m = _DOI_RE.search(text)
        doi = doi_m.group(0).rstrip(".").rstrip(",") if doi_m else None

        # Extract arXiv ID if present
        arxiv_m = re.search(r"(?:arXiv:|arxiv\.org/abs/)(\d+\.\d+)", text, re.IGNORECASE)
        arxiv_id = arxiv_m.group(1) if arxiv_m else None

        # Extract year
        year_m = _YEAR_RE.search(text)
        year = year_m.group(1) if year_m else None
        year_suffix = year_m.group(2) if year_m and year_m.group(2) else None

        # Extract authors: everything after [N] up to first recognizable year/doi
        # Pattern: [N] Authors, "Title" OR just Authors (year) until next [N]
        after_index = re.sub(r"^\[\s*\d+\s*\]\s*", "", text).strip()

        # Remove common metadata patterns that confuse title extraction
        # "vol. N", "no. N", "pp. N-N", "pp. N", "p. N", "Chapter N"
        clean_text = after_index
        for pattern in [
            r',?\s*vol\.\s*\d+[A-Z]?(?:-\d+)?',      # vol. 5 or vol. 5-7
            r',?\s*no\.\s*\d+',                       # no. 3
            r',?\s*pp\.\s*[\d\-–]+',                 # pp. 1-20 or pp. 123
            r',?\s*p\.\s*\d+',                        # p. 42
            r',?\s*chapters?\s+\d+',                   # chapter 3
            r',?\s*edition',                           # edition marker
            r',?\s*technical\s+report[^,]*',          # technical report
            r'\s+\d{4}[a-z]?\s*$',                    # trailing year at end
        ]:
            clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE).strip()

        # Try to find title: text between quotes, or text after authors
        title_raw = None
        # Quoted title
        quote_m = re.search(r'[""]([^""]+)[""]', clean_text)
        if quote_m:
            title_raw = quote_m.group(1).strip().rstrip(",")
        else:
            # Fallback title: everything after authors, before year/DOI
            remaining = clean_text
            if doi_m:
                remaining = remaining[:doi_m.start()].strip()
            if year_m:
                # Only use year as boundary if it's followed by end or punctuation
                y_end = year_m.end()
                remaining = remaining[:year_m.start()].strip()

            # STRATEGY 1: For entries like "[N] Authors. Title." (title after period)
            # Look for period followed by space and capitalized word (title)
            if not title_raw:
                period_title_m = re.search(r"\.\s+(?=[A-Z][a-z])", remaining)
                if period_title_m:
                    # Title is after the period
                    candidate = remaining[period_title_m.end():].strip()
                    if candidate and len(candidate) > 5:
                        title_raw = candidate.rstrip(".,").strip()
                        # Authors are everything before the period
                        authors_candidate = remaining[:period_title_m.start()].strip().rstrip(".")
                        if authors_candidate and authors_candidate != remaining:
                            authors_part = authors_candidate

            # STRATEGY 2: Authors end with comma followed by capitalized word (less reliable)
            # Only use this if Strategy 1 didn't work
            if not title_raw:
                author_end = re.search(
                    r",\s*(?=[A-Z][a-z])", remaining
                )
                if author_end:
                    candidate = remaining[author_end.end():].strip()
                    if candidate and len(candidate) > 10:
                        title_raw = candidate.rstrip(".,").strip()
                elif "," in remaining:
                    # Last comma before end is likely the author-title boundary
                    parts = remaining.rsplit(",", 1)
                    if len(parts) >= 2 and len(parts[1].strip()) > 10:
                        title_raw = parts[1].strip().rstrip(".,").strip()

            if remaining and len(remaining) > 10 and not title_raw:
                title_raw = remaining.rstrip(".,").strip()

        # Extract authors: everything before the title or year
        authors_part = ""
        if title_raw:
            idx = after_index.find(title_raw)
            if idx > 0:
                authors_part = after_index[:idx].strip().rstrip(",").rstrip()
        elif year_m:
            idx = after_index.find(year_m.group(0))
            if idx > 0:
                authors_part = after_index[:idx].strip().rstrip(",").rstrip()

        # Parse authors
        authors = parse_authors(authors_part) if authors_part else []

        # Extract venue: text after year (before DOI)
        venue = None
        if year_m and doi_m:
            venue = text[year_m.end():doi_m.start()].strip().rstrip(".,")
        elif year_m:
            venue = text[year_m.end():].strip().rstrip(".,")
        elif doi_m:
            venue = text[:doi_m.start()].strip().rstrip(".,")
            # Try to remove the authors from venue
            if authors_part and venue.startswith(authors_part):
                venue = venue[len(authors_part):].strip().lstrip(",").rstrip(".,")

        # Build title if not found: use arXiv ID or first part
        if not title_raw:
            if arxiv_id:
                title_raw = f"arXiv:{arxiv_id}"
            elif len(after_index) > 20:
                title_raw = after_index[:100].strip()

        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            page_num=page_num,
            matched_pattern="fallback_ieee_entry",
            order_index=order_index,
            numeric_index=numeric_index,
            title=title_raw if title_raw else None,
            title_normalized=_normalize_title(title_raw) if title_raw else None,
            year=year,
            year_suffix=year_suffix,
            authors=authors if authors else None,
            venue=venue if venue and len(venue) > 2 else None,
            doi=doi,
            confidence=0.7,  # Lower confidence for fallback parsing
        )
        return citation

    def _parse_vancouver_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        m = _VANCOUVER_ENTRY_RE.search(entry)
        if not m:
            return None

        # FIX: Extract numeric_index if entry starts with [N] prefix
        numeric_index = None
        idx_match = re.match(r"^\[\s*(\d+)\s*\]", entry)
        if idx_match:
            numeric_index = int(idx_match.group(1))

        citation = Citation(
            raw_text=entry.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.VANCOUVER,
            page_num=page_num,
            matched_pattern="vancouver_reference_entry",
            order_index=order_index,
            numeric_index=numeric_index,  # FIX: Set numeric_index for Vancouver entries with [N]
        )
        citation.year = m.group("year")
        title = m.group("title").strip()
        citation.title = title
        citation.title_normalized = _normalize_title(title)
        citation.venue = m.group("venue").strip()
        citation.authors = parse_authors(m.group("authors"))
        doi_m = _DOI_RE.search(entry)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip(".")
        return citation