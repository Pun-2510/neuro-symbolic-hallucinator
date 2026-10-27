"""ReferenceListParser — parse các entry ở cuối bài (References section).

Hỗ trợ (v1.2 §3.4):
    - APA-like: 'Smith, J. (2020). Title. Journal A, 10(2), 1-10. DOI: ...'
    - IEEE-like: '[1] Smith, J., "Title," Journal A, vol. 10, 2020.'
    - Vancouver: 'Smith J. Title. Journal A. 2020;10:1-10.'
    - Chicago author-date: tương tự APA

Sử dụng modular citation format system (patterns/):
    - Formats are loaded from registry at initialization
    - Format modules (APA, IEEE, Vancouver) are tried first
    - Legacy patterns kept as fallback for backward compatibility

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
from collections import Counter
from typing import Iterable

from integrity_checker.extraction.base import Document
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.extraction.patterns import get_format, get_all_formats
from integrity_checker.extraction.patterns.apa import is_vn_legal_reference, parse_vn_legal_reference
from integrity_checker.extraction.patterns.base import CitationFormat
from integrity_checker.matching.author_parser import parse_authors
from integrity_checker.models.citation import Citation, CitationStyle, CitationType

logger = logging.getLogger(__name__)


# --- Regex patterns ---

# APA entry: authors block + (year) + . + title + . + venue + ... + DOI
_APA_ENTRY_RE = re.compile(
    r"""
    ^(?P<authors>.+?)                # authors block (lazy)
    \s*\(\s*(?:(?P<year>\d{4})(?P<suffix>[a-z])?(?:\s*,\s*[^)]*)?|(?P<nd>n\.?\s*d\.?))
    \s*\)
    \.?\s*
    (?P<title>[^\.]+?)               # title (up to first period — may include colons)
    \.\s*
    (?P<venue>.+?)                   # venue + volume + pages + DOI
    $
    """,
    re.VERBOSE | re.MULTILINE | re.IGNORECASE,
)

# IEEE entry: [N] authors, "title," venue, ...
# Tách theo dấu phẩy: phần trước quote-title là authors+initials, sau là venue.
# Support straight and curly double/single quotes emitted by PDF extractors.
_IEEE_ENTRY_RE = re.compile(
    r"""
    ^\[\s*(?P<index>\d+)\s*\]\s*      # [N]
    (?P<authors>[^"]+?),\s*           # authors (everything until quote)
    ["“‘](?P<title>[^"”’]+)["”’]\s*,\s*   # "title," / ''title,''
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

# Vancouver variant: "Authors. Year. Title. Venue." (used by BERT paper)
# Example: "Samuel R. Bowman et al. 2015. A large annotated corpus..."
_VANCOUVER_YEAR_FIRST_RE = re.compile(
    r"""
    ^(?P<authors>.+?)\.\s*             # authors (ends with period)
    \(?(?P<year>\d{4})\)?             # year (with optional parens)
    [a-z]?\.\s+                         # period + space
    (?P<title>.+?)\.\s+                 # title (ends with period)
    (?P<venue>.+)$                      # venue
    """,
    re.VERBOSE,
)

# Unquoted book / chapter entry (APA-like, no quoted title):
#   "Settles, B, Active Learning (2012) Synthesis Lectures on ..."
# Parsed with plain string operations instead of one big regex: the author
# segment is the leading sequence of "Surname, Initials" pairs (ambiguous
# commas such as "Learning, Active" are resolved by trying every split, see
# ``_parse_unquoted_book_entry``). Avoids regex backtracking entirely.
_YEAR_PAREN_SEARCH = re.compile(r"\((?:19|20)\d{2}[a-z]?\)")
_INITIALS_FULLMATCH = re.compile(r"[A-ZÀ-Ý](?:\.?-?[A-ZÀ-Ý])*\.?")

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

# A line that is only a bibliography header or TDTU structural sub-header
# (used to drop it wherever it lands once running headers/page numbers have been stripped).
_BIB_HEADER_LINE_RE = re.compile(
    r"^\s*(?:(?:\d+|[A-Z]|[IVX]+)\s*[\.\)]\s*)?(?:"
    r"references?|bibliography|works?\s+cited"
    r"|danh\s+mục\s+tài\s+liệu(?:\s+tham\s+khảo)?|tài\s+liệu\s+tham\s+khảo"
    r"|văn\s+bản\s+(?:quy\s+phạm\s+)?pháp\s+luật"
    r"|(?:tài\s+liệu\s+)?(?:tiếng\s+việt|tiếng\s+anh|tiếng\s+pháp|tiếng\s+đức"
    r"|tiếng\s+nga|tiếng\s+trung|tiếng\s+nhật|nước\s+ngoài)"
    r")\s*[:.]?\s*$",
    re.IGNORECASE,
)

_LEADING_SUBHEADER_RE = re.compile(
    r"^\s*(?:(?:[A-Z]|[IVX]+|\d+)\s*[\.\)]\s*)?(?:"
    r"văn\s+bản\s+(?:quy\s+phạm\s+)?pháp\s+luật"
    r"|danh\s+mục\s+tài\s+liệu(?:\s+tham\s+khảo)?"
    r"|tài\s+liệu\s+tham\s+khảo"
    r"|(?:tài\s+liệu\s+)?(?:tiếng\s+việt|tiếng\s+anh|tiếng\s+pháp|tiếng\s+đức"
    r"|tiếng\s+nga|tiếng\s+trung|tiếng\s+nhật|nước\s+ngoài)"
    r")\s*[:.]?\s+",
    re.IGNORECASE,
)

_UPPER_VN_R = r"[A-ZÀ-ÝĂÂĐÊÔƠƯĨŨẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ]"
_PERSONAL_AUTHOR_HEAD_R = (
    rf"(?:(?:van|de|der|den|von|le|la|du|di|da)\s+)*{_UPPER_VN_R}[a-zA-ZÀ-ỹ'\u2019\-]+,\s*"
    rf"(?:{_UPPER_VN_R}\.?\s*[-–]?\s*)+"
    rf"(?:,\s*(?:&\s*|và\s*|and\s*)?(?:(?:van|de|der|den|von)\s+)*{_UPPER_VN_R}[a-zA-ZÀ-ỹ'\u2019\-]+,\s*(?:{_UPPER_VN_R}\.?\s*[-–]?\s*)+)*"
    rf"(?:\s+(?:&|và|and)\s+(?:(?:van|de|der|den|von)\s+)*{_UPPER_VN_R}[a-zA-ZÀ-ỹ'\u2019\-]+,\s*(?:{_UPPER_VN_R}\.?\s*[-–]?\s*)+)*"
    r"(?:\s*,?\s*(?:et\s+al\.?|và\s+cộng\s+sự|và\s+cs\.?))?"
    r"\s*\(\s*(?:(?:19|20)\d{2}[a-z]?(?:,\s*[A-Za-z]+\.?(?:\s+\d{1,2})?)?|n\.?\s*d\.?)\s*\)"
)
_DATED_WEB_AUTHOR_HEAD_R = (
    rf"{_UPPER_VN_R}[A-Za-zÀ-ỹ0-9.'\u2019\-]+(?:\s+{_UPPER_VN_R}?[A-Za-zÀ-ỹ0-9.'\u2019\-]+){{0,3}}\.?\s*"
    r"\(\s*(?:19|20)\d{2}[a-z]?,\s*[A-Za-z]+\.?(?:\s+\d{1,2})?\s*\)\."
)
_CORP_AUTHOR_HEAD_R = (
    r"(?:(?:Bộ|Tổng\s+cục|Ủy\s+ban|Uỷ\s+ban|Chính\s+phủ|Ngân\s+hàng|Tổ\s+chức|Hiệp\s+hội"
    r"|Department|Ministry|Reserve\s+Bank|World\s+Health|United\s+Nations|World\s+Bank)"
    r"[^().\n]{2,70}?\.?\s*\(\s*(?:19|20)\d{2}[a-z]?\s*\)\.)"
)
_LEGAL_HEAD_R = (
    r"(?:\d+\s*[\.\)]\s*)?(?:Hiến\s+pháp(?:\s+năm|\s+\d{4})"
    r"|(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s+[^().\n]{2,80}?(?:\((?:Bộ\s+luật|Luật|Pháp\s+lệnh)?\s*số|\bsố\s+\d|\bngày\s+\d)"
    r"|(?:Nghị\s+định|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định|Nghị\s+quyết(?:\s+liên\s+tịch)?|Chỉ\s+thị)\s+(?:số\s+)?\d+/\d{4}/)"
)
_MLA_BOOK_AUTHOR_HEAD_R = (
    rf"(?:{_UPPER_VN_R}[a-zA-ZÀ-ỹ'\u2019\-]+,\s+{_UPPER_VN_R}[A-Za-zÀ-ỹ.\s'\u2019\-]{{1,35}}?(?:,\s*et\s+al\.|\.)"
    r"|(?:Homer|Aeschylus|Euripides|Herodotus|Sophocles|Plato|Aristotle|Virgil|Ovid|Seneca|Epictetus|Augustine|Aquinas|Cicero|Plutarch|Thucydides|Tacitus|Dante|Boethius)\."
    r"|(?:The\s+)?(?:English\s+Standard\s+Version|ESV(?:\s+Study)?|King\s+James|New\s+International\s+Version|NIV|NKJV|NASB|Holy)\s+Bible[.,]"
    r"|[\-\u2013\u2014_]{3,}\.)\s+(?=[A-Z0-9\"\u201c])"
)
_INLINE_ENTRY_START_RE = re.compile(
    rf"(?:{_PERSONAL_AUTHOR_HEAD_R}|{_DATED_WEB_AUTHOR_HEAD_R}|{_CORP_AUTHOR_HEAD_R}|{_LEGAL_HEAD_R})"
)
_MLA_INLINE_SPLIT_RE = re.compile(
    rf"(?:(?<=\b(?:19|20)\d{{2}}\.)|(?<=ProQuest Ebook Central\.)|(?<=Google Scholar\.))\s+(?={_MLA_BOOK_AUTHOR_HEAD_R})"
)

# URL/DOI terminator — most web-style APA/MLA entries end with one of these
# (optionally followed by MLA "Accessed DD Mon. YYYY."), which makes them a
# reliable boundary between consecutive reference entries.
_URL_BOUNDARY_RE = re.compile(
    r"(?:(?:https?://|www\.|doi\.org/)\S+|\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|org|edu|gov|net)/\S+)"
    r"(?:\s+Accessed\s+\d{1,2}\s+[A-Za-z.]+\s+(?:19|20)\d{2}\.?)?",
    re.IGNORECASE,
)


def _is_essay_title_entry(entry: str) -> bool:
    """Check if a reference entry is actually an essay title or header, not a citation.

    Returns True if the entry should be filtered out.
    """
    text_stripped = entry.strip()

    # Structured reference entries (Author (Year). / [N] / Vietnamese legal docs)
    # whose paper title contains "A survey of..." or "Introduction to..." are real citations.
    if (
        _INLINE_ENTRY_START_RE.match(text_stripped)
        or re.match(r"^\s*\[\d+\]", text_stripped)
        or re.search(r"\(\s*(?:19|20)\d{2}[a-z]?\s*\)\.", text_stripped)
    ):
        return False

    # Very long text without year — likely a title or header
    if len(text_stripped) > 200 and _LONG_TEXT_NO_YEAR_RE.match(text_stripped):
        return True

    # Contains essay/survey/review indicators (without a citation year)
    if _ESSAY_TITLE_RE.search(text_stripped) and not re.search(r"\b(?:19|20)\d{2}\b", text_stripped):
        return True

    return False


# FIX v1.11: Fake/non-citation entry patterns - filter out method descriptions
_FAKE_ENTRY_PATTERNS = [
    # Pattern: Methodology-related headings that are not citations
    # Also matches when preceded by [N] (e.g., "[1] Context from...")
    re.compile(r'^\[\s*\d+\s*\]\s*(Context|Input\s*Processing|Classification|Loss|Computation|Optimization|'
              r'Model\s*\d*:|Embedding\s*Generation|Group\s*\d*:|'
              r'Robust\s*Vietnamese|Robustness|Fine-tuning|'
              r'Architecture|Training|Evaluation|Methodology)'
              r'[:\s]', re.IGNORECASE),
    # Pattern without [N] prefix
    re.compile(r'^(Context|Input\s*Processing|Classification|Loss|Computation|Optimization|'
              r'Model\s*\d*:|Embedding\s*Generation|Group\s*\d*:|'
              r'Robust\s*Vietnamese|Robustness|Fine-tuning|'
              r'Architecture|Training|Evaluation|Methodology)'
              r'[:\s]', re.IGNORECASE),
    # Pattern: Multi-word headings ending with colon
    re.compile(r'^\[\s*\d+\s*\]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}:'),
    re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}:'),
    # Pattern: Entries starting with verbs (method descriptions)
    re.compile(r'^\[\s*\d+\s*\]\s*(Predicting|Training|Using|Applying|Extracting|Computing|'
              r'Encoding|Decoding|Processing|Analyzing|Evaluating)'
              r'\s+[a-z]', re.IGNORECASE),
    re.compile(r'^(Predicting|Training|Using|Applying|Extracting|Computing|'
              r'Encoding|Decoding|Processing|Analyzing|Evaluating)'
              r'\s+[a-z]', re.IGNORECASE),
    # Pattern: Table of Contents leader dots, leading colon, or structural headings
    re.compile(r'(?:\.\s*){5,}'),
    re.compile(r'^\s*:'),
    re.compile(
        r'^(?:CHAPTER|SECTION|TABLE\s+OF\s+CONTENTS|LIST\s+OF\s+(?:FIGURES|TABLES))\b',
        re.IGNORECASE,
    ),
]

_METHOD_INDICATORS = [
    'is first tokenized', 'is encoded using', 'is passed through',
    'is computed from', 'token embedding', 'classification head',
    'cross-entropy loss', 'learning rate', 'weight decay',
    'gradient clipping', 'linear warmup', 'class-based tf-idf',
    'sentence embeddings', 'topic modeling', 'pre-trained', 'fine-tune',
]


def _is_fake_entry(entry: str) -> bool:
    """Check if an entry looks like a method description, not a citation.

    FIX v1.11: Filter out entries that are methodology descriptions,
    not actual citations (e.g., "[1] Context from both left and right of each token...").

    Returns True if the entry should be filtered out as fake/non-citation.
    """
    text_stripped = entry.strip()

    # TDTU §2.6.1 Vietnamese legal documents (e.g. "1. Hiến pháp 2013.") are valid references
    if is_vn_legal_reference(text_stripped):
        return False

    # Skip very short entries unless they have explicit Author (Year) Title structure
    if len(text_stripped) < 30:
        if len(text_stripped) >= 20 and re.search(
            r"^[A-ZÀ-Ý][A-Za-zÀ-ỹ'\u2019\-]+,\s+[A-Z].*\(\s*(?:19|20)\d{2}[a-z]?\s*\)\s+\S+",
            text_stripped,
        ):
            return False
        return True

    # FIX v1.11: Remove [N] prefix for pattern matching
    text_without_index = re.sub(r'^\[\s*\d+\s*\]\s*', '', text_stripped)

    # Check for basic citation structure (author + year)
    has_year = bool(re.search(r'\b(19|20)\d{2}\b', text_stripped))
    has_author_pattern = bool(re.search(r'[A-Z][a-z]+,\s*[A-Z]', text_stripped))
    has_doi_or_url = bool(_DOI_RE.search(text_stripped) or _URL_RE.search(text_stripped))

    # Check against fake entry patterns (both with and without [N] prefix)
    for pattern in _FAKE_ENTRY_PATTERNS:
        if pattern.search(text_stripped) or pattern.search(text_without_index):
            # A reference containing an explicit DOI or URL is not a methodology section heading
            if has_doi_or_url and pattern.pattern in (
                r'^\[\s*\d+\s*\]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}:',
                r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){2,}:',
            ):
                continue
            return True

    # Check for method description indicators
    lower_entry = text_without_index.lower()
    indicator_count = sum(1 for ind in _METHOD_INDICATORS if ind in lower_entry)

    # If many method indicators but no year or author pattern, it's fake
    if indicator_count >= 2 and not has_year and not has_author_pattern:
        return True

    # Filter out Appendix / codebase / annotation-guideline artifacts when no year/DOI/URL exists
    if not has_year and not has_doi_or_url:
        if (
            re.search(r"\b[a-z]+_[a-z]+\b", text_stripped)
            or re.search(r"\b[a-z_]{2,}/(?:[a-z0-9_.]*)", text_stripped, re.IGNORECASE)
            or "\u037e" in text_stripped
            or "↔" in text_stripped
            or re.search(
                r"\b(?:Precision,\s*Recall,\s*F1|JSONL\s+loader|Pairwise\s+Cohen)",
                text_stripped,
                re.IGNORECASE,
            )
        ):
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


def _estimate_reference_confidence(citation: Citation) -> float:
    """Heuristic parse-confidence (0–1) for a reference-list entry.

    Reference-list parsers previously left ``confidence`` at the ``Citation``
    default of 0.0.  That made every structured reference look like the least
    trustworthy citation in the corpus (app DB average was 0.128).  Score the
    entry by how much structured metadata the pattern actually recovered:
    title, authors, year, then DOI/venue as smaller bonuses.
    """
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


class ReferenceListParser:
    """Parse danh sách References ở cuối tiểu luận."""

    def __init__(self, extractor: CitationExtractor | None = None) -> None:
        self.extractor = extractor or CitationExtractor()
        # Initialize format parsers from registry (ordered by priority)
        # IEEE has [N] marker detection and should be tried first for numbered entries
        self.format_parsers: dict[str, CitationFormat] = {}
        for fmt in get_all_formats():
            self.format_parsers[fmt.name] = fmt

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
            # FIX v1.11: Filter out fake/non-citation entries (method descriptions)
            if _is_fake_entry(entry):
                logger.debug(f"Skipping fake entry: {entry[:50]}...")
                continue

            # Support Chicago/MLA 3-em dash (———.) author inheritance from preceding entry
            dash_m = re.match(
                r"^\s*(?:[\u2014\u2013\u2012―—–_-]{2,})\.?\s+(?P<rest>.+)$",
                entry,
                flags=re.DOTALL,
            )
            if dash_m and citations and citations[-1].authors:
                prev_authors = list(citations[-1].authors)
                lead_author = str(prev_authors[0]).rstrip(".")
                synth_entry = f"{lead_author}. {dash_m.group('rest').strip()}"
                citation = self._parse_entry(synth_entry, order_index=idx, page_num=start)
                if citation:
                    citation.raw_text = entry.strip()
                    citation.authors = prev_authors
            else:
                citation = self._parse_entry(entry, order_index=idx, page_num=start)

            if citation:
                # FIX v1.11: Double-check parsed citation is not fake
                # Some entries pass _is_fake_entry but get parsed anyway
                if _is_fake_entry(citation.raw_text):
                    logger.debug(f"Skipping parsed fake entry: {citation.raw_text[:50]}...")
                    continue
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
            r"^\s*(?:\d+\.?\s+)?(?:references?|bibliography"
            r"|danh\s+mục\s+tài\s+liệu(?:\s+tham\s+khảo)?|tài\s+liệu\s+tham\s+khảo"
            r"|works?\s+cited)\s*[:.]?\s*",
            flags=re.IGNORECASE,
        )
        text = header_strip_re.sub("", text, count=1).strip()

        if not text:
            return []

        # 1b. Drop page furniture (running headers + page numbers) so they do
        # not get glued to the front of an entry that starts after a page break.
        text = self._strip_running_headers(text)
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
                        entries[-1] = self._join_wrapped_line(entries[-1], line)
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

        # Find all [N] positions (excluding 4-digit years like [2020])
        bracket_pattern = re.compile(r'\[(?!19\d{2}\]|20\d{2}\])\d+\]')
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

    @staticmethod
    def _join_wrapped_line(prev: str, nxt: str) -> str:
        """Join a wrapped bibliography line, repairing hyphenated word breaks and split URLs."""
        prev_s = prev.rstrip()
        nxt_s = nxt.lstrip()
        if not prev_s:
            return nxt_s
        if not nxt_s:
            return prev_s

        # 1. URL wrapped across lines after '/' or '-' (e.g. "https://github.com/kermitt2/\ngrobid")
        if re.search(r"https?://\S+[/\-]$", prev_s) and re.match(
            r"^[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$", nxt_s.split()[0]
        ):
            return prev_s + nxt_s

        # 2. Word hyphenated at line end (e.g. "recog-\nnition", "Ide-\nSmith", "Pre-\ntraining")
        m_hyph = re.search(r"([A-Za-zÀ-ỹ]+)-$", prev_s)
        if m_hyph and re.match(r"^[A-Za-zÀ-ỹ]", nxt_s):
            prefix = m_hyph.group(1)
            nxt_word_m = re.match(r"^([A-Za-zÀ-ỹ]+)", nxt_s)
            nxt_word = nxt_word_m.group(1).lower() if nxt_word_m else ""
            # Keep hyphen for capitalized second part (compound surname like Ide-Smith)
            # or genuine compound prefixes (e.g. Pre-training, fine-tuning, neuro-symbolic)
            compound_prefixes = {
                "pre", "self", "multi", "cross", "neuro", "non", "semi",
                "fine", "zero", "few", "real", "open", "high", "low", "tf",
            }
            compound_roots = {
                "training", "trained", "tuning", "tuned", "supervised", "symbolic",
                "lingual", "modal", "task", "attention", "shot", "time", "source",
                "level", "scale", "idf", "based", "centric", "driven",
            }
            if nxt_s[0].isupper() or (
                prefix.lower() in compound_prefixes and nxt_word in compound_roots
            ):
                return prev_s + nxt_s
            return prev_s[:-1] + nxt_s

        return prev_s + " " + nxt_s

    @staticmethod
    def _clean_subheader_prefix(entry: str) -> str:
        """Strip leading TDTU structural sub-headers (e.g. 'A. Văn bản...', 'Tiếng Việt')."""
        cleaned = (entry or "").strip()
        while cleaned:
            m = _LEADING_SUBHEADER_RE.match(cleaned)
            if not m:
                break
            cleaned = cleaned[m.end():].strip()
        return cleaned

    def _split_inline_entries(self, chunk: str) -> list[str]:
        """Split a chunk that may contain multiple APA or Vietnamese legal entries."""
        cleaned_chunk = self._clean_subheader_prefix(chunk)
        if not cleaned_chunk:
            return []

        valid_starts: list[int] = []
        for m in _INLINE_ENTRY_START_RE.finditer(cleaned_chunk):
            pos = m.start()
            if pos == 0:
                valid_starts.append(pos)
                continue
            prefix = cleaned_chunk[:pos]
            # Must follow a sentence-ending period/semicolon, a URL, or a sub-header
            if re.search(
                r"(?:[\.;]|https?://\S+)\s+$"
                r"|(?:văn\s+bản\s+(?:quy\s+phạm\s+)?pháp\s+luật|tài\s+liệu\s+tham\s+khảo"
                r"|tiếng\s+việt|tiếng\s+anh|tiếng\s+pháp)\s*[:.]?\s+$",
                prefix,
                flags=re.IGNORECASE,
            ):
                valid_starts.append(pos)

        if not valid_starts or (len(valid_starts) == 1 and valid_starts[0] == 0):
            mla_parts = [p.strip() for p in _MLA_INLINE_SPLIT_RE.split(cleaned_chunk) if len(p.strip()) > 20]
            if len(mla_parts) >= 2:
                return mla_parts
            return [cleaned_chunk] if (len(cleaned_chunk) > 20 or is_vn_legal_reference(cleaned_chunk)) else []

        sub_entries: list[str] = []
        if valid_starts[0] > 0:
            leading = self._clean_subheader_prefix(cleaned_chunk[:valid_starts[0]])
            if len(leading) > 20 or is_vn_legal_reference(leading):
                for mp in _MLA_INLINE_SPLIT_RE.split(leading):
                    if len(mp.strip()) > 20:
                        sub_entries.append(mp.strip())

        for idx, start_pos in enumerate(valid_starts):
            end_pos = valid_starts[idx + 1] if idx + 1 < len(valid_starts) else len(cleaned_chunk)
            piece = self._clean_subheader_prefix(cleaned_chunk[start_pos:end_pos])
            # Trim any trailing sub-header that belongs to the next section
            piece = re.sub(
                r"\s+(?:[A-Z]\.\s*)?(?:Văn\s+bản\s+(?:quy\s+phạm\s+)?pháp\s+luật"
                r"|B\.\s*Tài\s+liệu\s+tham\s+khảo|Tiếng\s+Việt|Tiếng\s+Anh|Tiếng\s+Pháp)\s*[:.]?\s*$",
                "",
                piece,
                flags=re.IGNORECASE,
            ).strip()
            if len(piece) > 20 or is_vn_legal_reference(piece):
                for mp in _MLA_INLINE_SPLIT_RE.split(piece):
                    if len(mp.strip()) > 20 or is_vn_legal_reference(mp.strip()):
                        sub_entries.append(mp.strip())

        return sub_entries

    def _split_by_year_boundary(self, text: str) -> list[str]:
        """Tach entries bang URL/DOI boundaries va inline APA/legal entry starts.

        Algorithm:
            1. Rejoin hyphen-broken line wraps (PDF splits long URLs as
               ".../how-to-develop-\\nhealthcare-...") WITHOUT inserting a
               space, so the URL stays a single token.
            2. Flatten remaining whitespace to single spaces and repair space-broken URLs.
            3. Tim URL/DOI boundaries (http/https/www/doi.org), split tai do.
            4. Split each chunk further on inline APA / Vietnamese legal entry boundaries.
            5. Neu 2+ entries -> tra ve. Fallback -> newline/year markers.
        """
        # Step 1+2: Rejoin hyphen-broken wraps, flatten to a single line, repair broken URLs.
        flat = re.sub(r"-\s*\n\s*", "-", text)
        flat = re.sub(r"\s+", " ", flat).strip()
        flat = re.sub(r"%\s+([0-9A-Fa-f]{2})", r"%\1", flat)
        flat = re.sub(
            r"(%[0-9A-Fa-f]{2}[0-9A-Za-z_%~:-]*)\s+(%[0-9A-Fa-f]{2})",
            r"\1\2",
            flat,
        )
        flat = re.sub(r"\.(p)\s+(df)\b", r".\1\2", flat, flags=re.IGNORECASE)
        flat = re.sub(r"\.(ht)\s+(ml?)\b", r".\1\2", flat, flags=re.IGNORECASE)
        flat = re.sub(
            r"([a-z0-9_])_([a-z]{1,4})\s+([a-z0-9_]+\.html?)\b",
            r"\1_\2\3",
            flat,
            flags=re.IGNORECASE,
        )
        # Only join a broken URL after '/' or '-' when the next token starts with lowercase/digit
        # and is NOT the start of a new bibliography entry (never glue capitalized author surnames!).
        flat = re.sub(
            r"(https?://[^\s/]+(?:/[^\s/]+)*[/\-])\s+([a-z0-9_~%#][^\s]*)",
            r"\1\2",
            flat,
        )
        flat = re.sub(
            r"\b(10\.\d{4,9}/[A-Za-z0-9._;()/-]+[-/])\s+(\d+[A-Za-z0-9._;()/-]*)",
            r"\1\2",
            flat,
        )
        flat = re.sub(
            r"\b(10\.\d{4,9}/[A-Za-z0-9._;()/-]+\.)\s+(\d+[A-Za-z0-9._;()/-]*)",
            r"\1\2",
            flat,
        )

        # Step 3: Split at every URL/DOI terminator.
        matches = list(_URL_BOUNDARY_RE.finditer(flat))
        url_chunks: list[str] = []
        if len(matches) >= 1:
            start = 0
            for m in matches:
                end = m.end()
                chunk = flat[start:end].strip()
                if len(chunk) > 20 or is_vn_legal_reference(chunk):
                    url_chunks.append(chunk)
                start = end
            last_chunk = flat[start:].strip()
            if len(last_chunk) > 20 or is_vn_legal_reference(last_chunk):
                url_chunks.append(last_chunk)
        else:
            url_chunks = [flat]

        # Step 4: Split each URL-bounded chunk on inline APA / legal entry boundaries.
        entries: list[str] = []
        for chunk in url_chunks:
            sub = self._split_inline_entries(chunk)
            if sub:
                entries.extend(sub)
            elif len(chunk) > 20 or is_vn_legal_reference(chunk):
                entries.append(chunk)

        if len(entries) >= 2:
            return entries

        # Step 5: Fallback - split on newline / year markers
        return self._split_by_year_fallback(text)

    @staticmethod
    def _strip_running_headers(text: str) -> str:
        """Remove page furniture from a bibliography section.

        PDF page text repeats running headers (e.g. the essay title) and
        standalone page numbers on every page. When the bibliography spans
        several pages those lines end up glued to the front of the first entry
        on each page, corrupting its author/year metadata. Drop:
          - standalone page numbers ("43"),
          - standalone bibliography headers ("References"),
          - short lines that repeat at least twice (running headers),
          - running headers with page numbers (e.g. "TITLE...  28").
        """
        lines = text.splitlines()
        counts = Counter(line.strip() for line in lines if line.strip())

        # Pattern to match running headers with page numbers
        # e.g. "EMOTIONAL INTELLIGENCE AND HEART RATE VARIABILITY... 28"
        running_header_re = re.compile(r"^[\w\s]+?\s{3,}\d{1,3}\s*$")
        running_head_prefix_re = re.compile(r"^\s*Running\s+head\s*:.*$", re.IGNORECASE)
        allcaps_header_page_re = re.compile(r"^[A-Z0-9\s,'\-:]{4,70}\s+\d{1,3}\s*$")

        cleaned: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned.append("")
                continue
            # Skip standalone page numbers
            if re.fullmatch(r"\d{1,4}", stripped):
                continue
            # Skip bibliography header lines
            if _BIB_HEADER_LINE_RE.match(stripped):
                continue
            # Skip running headers with page numbers (TITLE...  28 or Running head: ...)
            if (
                running_header_re.match(stripped)
                or running_head_prefix_re.match(stripped)
                or allcaps_header_page_re.match(stripped)
            ):
                continue
            # Skip short repeated lines without year/URL (typical running headers)
            if (
                counts[stripped] >= 2
                and len(stripped) < 100  # Increased from 80 to catch more headers
                and not re.search(r"(?:19|20)\d{2}", stripped)
                and "http" not in stripped.lower()
            ):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    def _split_by_year_fallback(self, text: str) -> list[str]:
        """Fallback: split reference list by newline boundaries.

        This method is called when DOI/URL-based splitting fails.
        Each reference entry is on its own line (or separated by blank lines).
        Returns list of entries.
        """
        # Split by blank lines first (paragraph-style)
        parts = re.split(r"\n\s*\n", text)
        if len(parts) >= 2:
            expanded_parts: list[str] = []
            for p in parts:
                p_strip = p.strip()
                if not p_strip:
                    continue
                # If a paragraph chunk spans a page break and glues two complete entries
                # separated by a newline (where the first line ends with ", YYYY." or a URL),
                # split them cleanly.
                sub_lines = [ln.strip() for ln in p_strip.splitlines() if ln.strip()]
                if len(sub_lines) >= 2 and all(
                    re.search(r"(?:,\s*(?:19|20)\d{2}\.?|https?://\S+)\s*$", ln)
                    for ln in sub_lines
                ):
                    expanded_parts.extend(sub_lines)
                else:
                    expanded_parts.append(p_strip)
            result = [
                p
                for p in expanded_parts
                if len(p) > 20 or is_vn_legal_reference(p)
            ]
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
            elif re.match(
                r"^(?:\d+\s*[\.\)]\s*)?(?:[A-ZÀ-ÝĂÂĐÊÔƠƯĨŨẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ][a-zA-ZÀ-ỹ]|[\u2014\u2013\u2012―—–_-]{2,}\.)",
                stripped,
            ) and (
                not current
                or bool(re.match(r"^(?:\d+\s*[\.\)]\s+|[\u2014\u2013\u2012―—–_-]{2,}\.)", stripped))
                or (
                    bool(re.search(r'(?:[.)"\u201d]|https?://\S+|doi\.org/\S+)\s*$', current, re.IGNORECASE))
                    and bool(re.search(r"(?:19|20)\d{2}|\bn\.?d\.?\b|https?://", current, re.IGNORECASE))
                )
            ):
                # Line starts with uppercase or numbered legal item - new entry
                if current:
                    entries.append(current.strip())
                current = stripped
            else:
                # Continuation line (wrapped text) - append to current
                current = (current + " " + stripped).strip()

        # Don't forget the last entry
        if current.strip():
            entries.append(current.strip())

        # Filter out very short entries (likely not citations), keeping valid legal documents
        result = [e for e in entries if len(e) > 20 or is_vn_legal_reference(e)]

        return result if len(result) >= 2 else []

    def _parse_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Parse 1 entry. Try format modules first, then fallback to legacy patterns.

        Strategy:
            1. Normalize: replace newlines with spaces
            2. Extract numeric_index if entry starts with [N] prefix
            3. Try format modules from registry
            4. Fallback to legacy patterns (_parse_apa_entry, _parse_ieee_entry, etc.)
            5. Fallback to _parse_fallback_entry if numeric_index available
        """
        # Normalize: replace newlines with spaces (wrapped lines) and repair line-wrapped URLs
        entry = entry.replace("\n", " ").replace("  ", " ")
        entry = entry.replace("\u2018\u2018", "\u201c").replace("\u2019\u2019", "\u201d")
        entry = re.sub(r"\b(https?)\s*:\s*//\s*", r"\1://", entry, flags=re.IGNORECASE)
        entry = re.sub(r"\.(p)\s+(df)\b", r".\1\2", entry, flags=re.IGNORECASE)
        for _ in range(3):
            entry = re.sub(r"(https?://\S*[/_\-~])\s+([a-z0-9_\-~])", r"\1\2", entry)
            entry = re.sub(r"(https?://\S*\.)\s+([a-z0-9_\-~])", r"\1\2", entry)

        # FIX: Extract numeric_index first if entry starts with [N] prefix
        numeric_index = None
        idx_match = re.match(r"^\[\s*(\d+)\s*\]", entry)
        if idx_match:
            numeric_index = int(idx_match.group(1))

        # TDTU §2.6.1 Vietnamese legal document entry
        legal_citation = parse_vn_legal_reference(entry)
        if legal_citation is not None:
            legal_citation.page_num = page_num
            legal_citation.order_index = order_index
            if numeric_index and legal_citation.numeric_index is None:
                legal_citation.numeric_index = numeric_index
            return legal_citation

        # Scriptural / Bible edition entry (e.g. "The Bible. ESV ed., Crossway, 2022.",
        # "English Standard Version Bible. Crossway Bibles, 2016.",
        # "The ESV Study Bible, Wheaton, IL: Crossway, 2008.")
        bible_m = re.match(
            r"^The\s+Bible\.\s*(?:([A-Z]{2,6})\s+ed\.,\s*)?([^,]+),\s*((?:19|20)\d{2})\.?$",
            entry.strip(),
            re.IGNORECASE,
        )
        if bible_m:
            ed_code = (bible_m.group(1) or "Bible").upper()
            pub = bible_m.group(2).strip()
            yr = bible_m.group(3)
            return Citation(
                raw_text=entry.strip(),
                citation_type=CitationType.REFERENCE_LIST,
                style=CitationStyle.MLA,
                page_num=page_num,
                order_index=order_index,
                matched_pattern="mla_bible_edition",
                authors=[ed_code],
                title=f"The Bible ({ed_code} ed.)" if bible_m.group(1) else "The Bible",
                year=yr,
                venue=pub,
                confidence=0.9,
            )

        bible_named_m = re.match(
            r"^(?P<btitle>(?:The\s+)?(?:English\s+Standard\s+Version|ESV(?:\s+Study)?|King\s+James|New\s+International\s+Version|NIV|NKJV|NASB|RSV|NRSV|Holy)\s+Bible)[.,]\s*(?:(?P<city>[A-Za-z.\s]+,\s*[A-Z]{2}):\s*)?(?P<pub>[^,]+),\s*(?P<yr>(?:19|20)\d{2})\.?$",
            entry.strip(),
            re.IGNORECASE,
        )
        if bible_named_m:
            btitle = bible_named_m.group("btitle").strip()
            pub = bible_named_m.group("pub").strip()
            yr = bible_named_m.group("yr")
            return Citation(
                raw_text=entry.strip(),
                citation_type=CitationType.REFERENCE_LIST,
                style=CitationStyle.MLA,
                page_num=page_num,
                order_index=order_index,
                matched_pattern="mla_bible_edition",
                authors=[btitle],
                title=btitle,
                year=yr,
                venue=pub,
                confidence=0.9,
            )

        # Unquoted book/chapter entry: ``Surname, Initials, Title (Year) venue``.
        # Must run BEFORE the format registry — ``nature_book`` claims these
        # entries with a one-letter "title" and provably wrong authors.
        book_citation = self._parse_unquoted_book_entry(entry, order_index, page_num)
        if book_citation:
            if numeric_index and book_citation.numeric_index is None:
                book_citation.numeric_index = numeric_index
            return book_citation

        # Try format modules from registry first (Two-pass: strict patterns before fallbacks)
        # Require title for a meaningful match (year alone is not enough)
        # IEEE entries with [N] prefix are an exception - they should be accepted with just year
        all_formats = get_all_formats()
        is_ama_specific = bool(
            re.match(r"^\s*\d+\.\s+", entry)
            and (
                re.search(r"\bdoi:\s*10\.\d{4,9}/", entry, re.IGNORECASE)
                or re.search(r"[^.:]+:\s*[^;]+;\s*(?:19|20)\d{2}\b", entry)
            )
        )
        is_cse_nameyear_specific = bool(
            not re.match(r"^\s*(?:\[\s*\d+\s*\]|\d+\.)", entry)
            and re.match(
                r"^[A-ZÀ-Ý][a-zA-ZÀ-ÿ'-]+\s+[A-Z]{1,3}(?:,\s+[A-ZÀ-Ý][a-zA-ZÀ-ÿ'-]+\s+[A-Z]{1,3})*\.\s+(?:19|20)\d{2}\.\s+",
                entry,
            )
        )

        for allow_fallback in (False, True):
            for fmt in all_formats:
                if not allow_fallback:
                    if is_ama_specific and fmt.name in ("Vancouver", "CSE", "ACS"):
                        continue
                    if is_cse_nameyear_specific and fmt.name in ("Vancouver", "Chicago", "Harvard"):
                        continue
                citation = fmt.parse_reference_entry(entry)
                if not citation:
                    continue
                is_fallback = "fallback" in (citation.matched_pattern or "")
                if is_fallback != allow_fallback:
                    continue
                has_title = bool(citation.title)
                has_year = bool(citation.year)
                has_numeric_index = citation.numeric_index is not None
                # Never let the short-title book pattern (``nature_book``)
                # claim an entry whose title is a stray token: it drops the
                # year and turns the title's words into fake authors.
                if (
                    citation.matched_pattern == "nature_book"
                    and (not has_year or len((citation.title or "").strip()) < 8)
                ):
                    continue
                # Accept if: (has title AND (has year OR doi OR url)), OR (has year AND has numeric_index)
                if (has_title and (has_year or citation.doi or citation.url)) or (
                    has_year and has_numeric_index
                ):
                    # Set common fields
                    citation.page_num = page_num
                    citation.order_index = order_index
                    citation.citation_type = CitationType.REFERENCE_LIST
                    # Set numeric_index if found and not already set
                    if numeric_index and citation.numeric_index is None:
                        citation.numeric_index = numeric_index
                    return citation

        # Fallback to legacy patterns if format modules didn't match
        # IEEE first (vì có marker [N] đặc trưng)
        if re.match(r"^\s*\[\d+\]", entry):
            citation = self._parse_ieee_entry(entry, order_index, page_num)
            if citation:
                if numeric_index and citation.numeric_index is None:
                    citation.numeric_index = numeric_index
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

    def _parse_unquoted_book_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Parse ``Surname, Initials, Title (Year) venue`` (no quoted title).

        Example: ``Settles, B, Active Learning (2012) Synthesis Lectures on …``.

        The comma that ends the author list is ambiguous when the title
        itself starts with ``Word, Word`` (``Settles, B, Learning, Active
        (2012)``): several split points are valid, so every split is tried and
        the longest author list whose pieces all look like ``Surname,
        Initials`` wins. A piece such as ``John`` (full first name) is never
        accepted as initials, so ``Smith, John, Title (2020)`` falls through.
        """
        year_m = _YEAR_PAREN_SEARCH.search(entry)
        if not year_m:
            return None
        head = entry[: year_m.start()].strip()
        rest = entry[year_m.end():]

        # Standard APA entries have a period right after (Year): "Authors (Year). Title."
        # Unquoted book entries here have the title BEFORE (Year) and venue after (Year)
        # without a leading period, and do not contain author conjunctions (& / and) in head.
        if rest.lstrip().startswith("."):
            return None
        if "&" in head or re.search(r"\band\b", head, re.IGNORECASE):
            return None

        pieces = [p.strip() for p in head.split(",")]

        raw_authors: str | None = None
        title = ""
        # pieces[0] is the surname; pairs are (surname, initials).
        for n_pairs in range(len(pieces) // 2, 0, -1):
            pair_pieces = pieces[: n_pairs * 2]
            surname, initials = pair_pieces[0], pair_pieces[1]
            if len(surname) < 2 or _INITIALS_FULLMATCH.fullmatch(surname):
                continue
            if any(
                not _INITIALS_FULLMATCH.fullmatch(pair_pieces[i])
                for i in range(1, len(pair_pieces), 2)
            ):
                continue
            rem_pieces = [p.strip() for p in pieces[n_pairs * 2:] if p.strip()]
            if not rem_pieces:
                continue
            # If any remaining piece looks like author initials (e.g. "R. L."),
            # then head is a multi-author APA list, not an unquoted book title.
            if any(
                _INITIALS_FULLMATCH.fullmatch(p) or re.search(r"\b[A-ZÀ-Ý]\.", p)
                for p in rem_pieces
            ):
                continue
            if len(rem_pieces) == 2 and all(
                re.fullmatch(r"[A-ZÀ-Ý][a-zà-ỹ]+", p) for p in rem_pieces
            ):
                # GROBID sometimes inverts a 2-word book title into "Surname, Forename"
                # (e.g. "Active Learning" -> "Learning, Active").
                candidate_title = f"{rem_pieces[1]} {rem_pieces[0]}"
            else:
                candidate_title = ", ".join(rem_pieces).strip()
            if len(candidate_title) < 5 or not candidate_title[0].isupper():
                continue
            raw_authors = ", ".join(pair_pieces)
            title = candidate_title
            break
        if raw_authors is None:
            return None

        title = title.rstrip(",;: ").strip()
        doi_m = _DOI_RE.search(entry)
        return Citation(
            raw_text=entry.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            page_num=page_num,
            matched_pattern="unquoted_book_entry",
            order_index=order_index,
            title=title,
            title_normalized=_normalize_title(title),
            year=year_m.group(0)[1:-1].rstrip("abcdefghijklmnopqrstuvwxyz"),
            year_suffix=(suffix if (suffix := year_m.group(0)[-2:-1]).isalpha() else None),
            authors=parse_authors(raw_authors),
            venue=(rest.strip(" .,") or None),
            doi=doi_m.group(0).rstrip(".,") if doi_m else None,
            confidence=0.75,
        )

    def _parse_apa_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Legacy APA entry parser (fallback when format module doesn't match)."""
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
        if not citation.year:
            ym = _YEAR_RE.search(m.group("venue") or "")
            if ym:
                citation.year = ym.group(1)
        suffix = m.group("suffix")
        citation.year_suffix = suffix if suffix else None
        title = m.group("title").strip().rstrip(".")
        citation.title = title
        citation.title_normalized = _normalize_title(title)
        citation.venue = m.group("venue").strip().rstrip(".")
        authors_raw = re.sub(r"^\[\s*\d+\s*\]\s*", "", m.group("authors")).strip()
        citation.authors = parse_authors(authors_raw)
        # DOI
        doi_m = _DOI_RE.search(entry)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip(".")
        citation.confidence = _estimate_reference_confidence(citation)
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

        # Support both straight and curly quotes from PDF extractors
        quote_chars_open = '"\u201c\u2018'
        quote_chars_close = '"\u201d\u2019'

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
        title_raw = remainder[first_q + 1:close_q].strip().rstrip(",").rstrip().lstrip('\u2018\u2019"\'')
        venue_year = remainder[close_q + 1:].strip().lstrip(",").strip()

        # Extract year: for arXiv entries (e.g., arXiv:1911.09339, 2019), prefer the
        # publication year (after comma) over the arXiv ID year or access year.
        year_matches = list(_YEAR_RE.finditer(venue_year))
        pub_after_arxiv = re.search(
            r'arxiv:\s*\d{4}\.\d+[^\d]+((?:19|20)\d{2})\b',
            venue_year,
            re.IGNORECASE,
        )
        if pub_after_arxiv:
            year_m = pub_after_arxiv
        elif year_matches:
            year_m = year_matches[0]
        else:
            year_m = None
        year = year_m.group(1) if year_m else None
        suffix = (
            year_m.group(2)
            if year_m and year_m.lastindex and year_m.lastindex >= 2 and year_m.group(2)
            else None
        )

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
        citation.confidence = _estimate_reference_confidence(citation)
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
        authors_part = ""
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
                # Unquoted IEEE book entries: ``[N] B. Settles, Active Learning.``
                # Keep the author initials out of the title by using the comma
                # immediately before the first sentence-ending period.
                book_title_m = re.match(
                    r"^.+?,\s+(?P<title>[^.]{5,})\.\s+",
                    remaining,
                )
                if book_title_m:
                    title_raw = book_title_m.group("title").strip()
                    authors_part = remaining[: book_title_m.start("title")].rstrip(", ")

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
        if not authors_part:
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
        # Try Vancouver year-first variant first (BERT paper format: "Authors. Year. Title.")
        m_year_first = _VANCOUVER_YEAR_FIRST_RE.search(entry)
        if m_year_first:
            return self._parse_vancouver_year_first_match(m_year_first, entry, order_index, page_num)

        # Try standard Vancouver second
        m = _VANCOUVER_ENTRY_RE.search(entry)
        if m:
            return self._parse_vancouver_match(m, entry, order_index, page_num)

        return None

    def _parse_vancouver_match(
        self, m: re.Match, entry: str, order_index: int, page_num: int
    ) -> Citation:
        """Parse a standard Vancouver match."""
        # Extract numeric_index if entry starts with [N] prefix
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
            numeric_index=numeric_index,
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
        citation.confidence = _estimate_reference_confidence(citation)
        return citation

    def _parse_vancouver_year_first_match(
        self, m: re.Match, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Parse Vancouver format with year after authors: 'Authors. Year. Title. Venue.'"""
        try:
            citation = Citation(
                raw_text=entry.strip(),
                citation_type=CitationType.REFERENCE_LIST,
                style=CitationStyle.VANCOUVER,
                page_num=page_num,
                matched_pattern="vancouver_year_first_entry",
                order_index=order_index,
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
            citation.confidence = _estimate_reference_confidence(citation)
            return citation
        except Exception:
            return None


# =============================================================================
# TDTU Bibliography Ordering & Language Compliance Checker (§2.6.1 – §2.6.3)
# =============================================================================

_VN_ALPHABET_GROUPS: list[str] = [
    " ",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "aàảãáạ",
    "ăằẳẵắặ",
    "âầẩẫấậ",
    "b",
    "c",
    "d",
    "đ",
    "eèẻẽéẹ",
    "êềểễếệ",
    "f",
    "g",
    "h",
    "iìỉĩíị",
    "j",
    "k",
    "l",
    "m",
    "n",
    "oòỏõóọ",
    "ôồổỗốộ",
    "ơờởỡớợ",
    "p",
    "q",
    "r",
    "s",
    "t",
    "uùủũúụ",
    "ưừửữứự",
    "v",
    "w",
    "x",
    "yỳỷỹýỵ",
    "z",
]

_VN_CHAR_COLLATE_MAP: dict[str, tuple[int, int]] = {}
for _group_idx, _chars in enumerate(_VN_ALPHABET_GROUPS):
    for _tone_idx, _ch in enumerate(_chars):
        _VN_CHAR_COLLATE_MAP[_ch] = (_group_idx, _tone_idx)

_VN_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]",
    re.IGNORECASE,
)


def vn_alphabetical_sort_key(text: str) -> tuple[list[int], list[int]]:
    """Return a Vietnamese ABC collation key (base letters first, tones second)."""
    import unicodedata

    s = unicodedata.normalize("NFC", (text or "").strip().lower())
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    base_ranks: list[int] = []
    tone_ranks: list[int] = []
    for ch in s:
        b_rank, t_rank = _VN_CHAR_COLLATE_MAP.get(ch, (len(_VN_ALPHABET_GROUPS) + ord(ch), 0))
        base_ranks.append(b_rank)
        tone_ranks.append(t_rank)
    return base_ranks, tone_ranks


def classify_tdtu_reference_group(citation: Citation) -> str:
    """Classify a reference into ``'legal'``, ``'vi'``, or ``'foreign'`` per TDTU §2.6."""
    raw = citation.raw_text or ""
    if citation.matched_pattern == "vn_legal_document" or is_vn_legal_reference(raw):
        return "legal"
    combined = f"{raw} {citation.title or ''} {citation.venue or ''}"
    if _VN_DIACRITIC_RE.search(combined):
        return "vi"
    return "foreign"


def _legal_hierarchy_rank(citation: Citation) -> int:
    """Return TDTU §2.6.1 legal hierarchy rank: 1=Hiến pháp, 2=Bộ luật/Luật, 3=Văn bản dưới luật."""
    title = (citation.title or citation.raw_text or "").strip()
    title_clean = re.sub(r"^\s*\d+\s*[\.\)]\s*", "", title)
    if re.match(r"^Hiến\s+pháp\b", title_clean, re.IGNORECASE):
        return 1
    if re.match(r"^(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\b", title_clean, re.IGNORECASE):
        return 2
    return 3


def _reference_primary_sort_label(citation: Citation) -> str:
    """Return the author surname or corporate author name used for ABC sorting (§2.6.2b)."""
    if citation.authors:
        first = citation.authors[0]
        if hasattr(first, "last_name") and first.last_name:
            return first.last_name.strip()
        if isinstance(first, str) and first.strip():
            return first.strip()
    return (citation.title or citation.raw_text or "").strip()


class TDTUBibliographyComplianceResult:
    """Result of checking a reference list against TDTU §2.6 ordering and grouping rules."""

    def __init__(
        self,
        is_compliant: bool,
        groups: list[str],
        violations: list[str],
    ) -> None:
        self.is_compliant = is_compliant
        self.groups = groups
        self.violations = violations


def check_tdtu_bibliography_compliance(
    citations: list[Citation],
) -> TDTUBibliographyComplianceResult:
    """Check TDTU §2.6 reference list compliance (legal hierarchy, language grouping, ABC order)."""
    groups = [classify_tdtu_reference_group(c) for c in citations]
    violations: list[str] = []

    # 1. Check section ordering: legal -> vi -> foreign (no interleaving)
    group_order = {"legal": 0, "vi": 1, "foreign": 2}
    seen_groups: set[str] = set()
    prev_group: str | None = None
    for idx, grp in enumerate(groups):
        if prev_group is not None and grp != prev_group:
            if grp in seen_groups:
                violations.append(
                    f"Language/section groups are interleaved at entry #{idx + 1} ('{grp}' appears after '{prev_group}')."
                )
            elif group_order[grp] < group_order[prev_group]:
                violations.append(
                    f"Section '{grp}' at entry #{idx + 1} should appear before '{prev_group}'."
                )
        seen_groups.add(grp)
        prev_group = grp

    # 2. Check legal hierarchy within legal documents (Hiến pháp -> Luật/Bộ luật -> Văn bản dưới luật)
    legal_cits = [c for c, g in zip(citations, groups) if g == "legal"]
    for i in range(len(legal_cits) - 1):
        r1 = _legal_hierarchy_rank(legal_cits[i])
        r2 = _legal_hierarchy_rank(legal_cits[i + 1])
        if r1 > r2:
            violations.append(
                f"Legal hierarchy violation: '{legal_cits[i].title}' appears before '{legal_cits[i + 1].title}'."
            )

    # 3. Check ABC alphabetical sorting within each academic language group ('vi' and 'foreign')
    for target_grp in ("vi", "foreign"):
        grp_cits = [c for c, g in zip(citations, groups) if g == target_grp]
        for i in range(len(grp_cits) - 1):
            label_a = _reference_primary_sort_label(grp_cits[i])
            label_b = _reference_primary_sort_label(grp_cits[i + 1])
            if vn_alphabetical_sort_key(label_a) > vn_alphabetical_sort_key(label_b):
                violations.append(
                    f"Alphabetical order violation in '{target_grp}': '{label_a}' appears before '{label_b}'."
                )

    return TDTUBibliographyComplianceResult(
        is_compliant=len(violations) == 0,
        groups=groups,
        violations=violations,
    )
