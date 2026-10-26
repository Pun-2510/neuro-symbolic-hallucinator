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
from integrity_checker.matching.author_parser import Author, parse_authors
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# =============================================================================
# APA Pattern Definitions
# =============================================================================

# --- In-text APA patterns ---

_UPPER_VN = r"[A-ZÀ-ÝĂÂĐÊÔƠƯĨŨẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ]"
_STOPWORDS_AHEAD = (
    r"(?!(?:Theo|Trong|Tại|Với|Như|Của|Bởi|Qua|Từ|Khi|Nếu|Vì|Do|Ở|Hoặc|Và"
    r"|In|For|By|From|See|As|With|According|However|Although)\s+)"
)
_AUTHOR_TOKEN = rf"(?:(?:van|de|der|von)\s+)*{_UPPER_VN}[a-zA-ZÀ-ỹ'\-]+"
_CORP_AUTHOR_NARRATIVE = (
    r"(?:Bộ|Tổng\s+cục|Ủy\s+ban|Uỷ\s+ban|Ngân\s+hàng\s+Nhà\s+nước|Tổ\s+chức|Hiệp\s+hội)(?:\s+[A-Za-zÀ-ỹ&]+){1,8}"
    r"|(?:Chính\s+phủ|Quốc\s+hội|Hiến\s+pháp)(?:\s+[A-Za-zÀ-ỹ&]+){0,6}"
    r"|(?:Bộ\s+luật|Luật|Pháp\s+lệnh)(?:\s+[A-Za-zÀ-ỹ]+){1,6}"
    r"|(?:Nghị\s+định|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định|Nghị\s+quyết|Chỉ\s+thị)(?:\s+số)?\s+\d+[A-Za-zĐđ0-9/\-]+"
    r"|(?:Department|Ministry|World\s+Health\s+Organization|United\s+Nations|Reserve\s+Bank)"
    rf"(?:\s+(?:of|for|and|the|&|{_UPPER_VN}[a-zA-ZÀ-ỹ\-]*)){{1,8}}"
)
_PAGE_OR_SECONDARY_SUFFIX = (
    r"(?:\s*,\s*(?:"
    r"(?:dẫn\s+theo|trích\s+dẫn\s+(?:trong|từ)|as\s+cited\s+in|cited\s+in)\s+[^)]+"
    r"|(?:pp?\.?|tr\.?|trang)\s*\d+(?:\s*[-–]\s*\d+)?"
    r"))?"
)

# Parenthetical: (Author, 2020), (Author et al., 2020), (Author và cộng sự, 2020),
# (Author A và Author B, 2020), (Author, 2020, tr. 15), (Author, 2005, dẫn theo B, 2016)
_APA_INTEXT_PARENTHETICAL = CompiledPattern.create(
    name="apa_intext_parenthetical",
    pattern=rf"\(([^)]+),\s*(\d{{4}}[a-z]?){_PAGE_OR_SECONDARY_SUFFIX}\)",
    pattern_type=PatternType.IN_TEXT,
    description="APA in-text parenthetical: (Author, 2020) | (Author et al., 2020) | (Author và cộng sự, 2020)",
)

# Narrative: Author (2020), Author et al. (2020), Author và cộng sự (2020),
# Author A và Author B (2020), Corporate Author (2020)
_APA_INTEXT_NARRATIVE = CompiledPattern.create(
    name="apa_intext_narrative",
    pattern=(
        rf"({_CORP_AUTHOR_NARRATIVE}|{_STOPWORDS_AHEAD}{_AUTHOR_TOKEN}"
        rf"(?:(?:\s*,\s*(?:và|and|&)\s+|\s+(?:và|and|&)\s+|\s*,\s*){_STOPWORDS_AHEAD}{_AUTHOR_TOKEN})*"
        rf"(?:\s*,?\s*(?:et\s+al\.?|và\s+cộng\s+sự|và\s+cs\.?))?"
        rf"(?:[\s,]{_UPPER_VN}[a-zA-ZÀ-ỹ'\-]*)*)"
        rf"\s+\((\d{{4}}[a-z]?){_PAGE_OR_SECONDARY_SUFFIX}\)"
    ),
    pattern_type=PatternType.IN_TEXT,
    description="APA narrative: Author (2020) | Author et al. (2020) | Author và cộng sự (2020)",
)

# --- Reference list APA patterns ---

# Standard APA reference entry:
# Author, A. A., & Author, B. B. (Year). Title of work. Publisher/DOI.
_APA_REFERENCE_ENTRY = CompiledPattern.create(
    name="apa_reference_entry",
    pattern=(
        r"^"
        r"(?P<authors>.+?)"
        r"\s+\(\s*(?:(?P<year>\d{4})(?P<suffix>[a-z])?(?:\s*,\s*[^)]+)?|(?P<nd>n\.?\s*d\.?)(?:-(?P<nd_suffix>[a-z]))?)\s*\)"
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
# Vietnamese Legal Document Helpers (TDTU §2.6.1)
# =============================================================================

_VN_LEGAL_LIST_PREFIX_RE = re.compile(
    r"^\s*(?:\[\s*(?P<b_idx>\d+)\s*\]|\d+\s*[\.\)]|[a-z]\s*\)|[-•–])\s*"
)

_VN_CONSTITUTION_RE = re.compile(
    r"^Hiến\s+pháp(?:\s+nước\s+Cộng\s+hòa\s+xã\s+hội\s+chủ\s+nghĩa\s+Việt\s+Nam)?"
    r"(?:\s+năm)?\s*\(?(?P<year>(?:19|20)\d{2})\)?[.,;\s]*$",
    re.IGNORECASE,
)

_VN_LAW_RE = re.compile(
    r"^(?P<law_prefix>Bộ\s+luật|Luật|Pháp\s+lệnh)\s+(?P<rest>.+)$",
    re.IGNORECASE,
)

_VN_SUBLAW_RE = re.compile(
    r"^(?P<doc_type>Nghị\s+định|Thông\s+tư(?:\s+liên\s+tịch)?|Quyết\s+định"
    r"|Nghị\s+quyết(?:\s+liên\s+tịch)?|Chỉ\s+thị)\s+(?:số\s+)?(?P<doc_code>\d+[\d/A-ZĐa-z\-–]+)",
    re.IGNORECASE,
)

_SUBLAW_AGENCY_SUFFIX_MAP = {
    "NĐ-CP": "Chính phủ",
    "NQ-CP": "Chính phủ",
    "QĐ-TTG": "Thủ tướng Chính phủ",
    "CT-TTG": "Thủ tướng Chính phủ",
    "NQ-QH": "Quốc hội",
    "UBTVQH": "Ủy ban Thường vụ Quốc hội",
    "TT-BTC": "Bộ Tài chính",
    "TT-NHNN": "Ngân hàng Nhà nước",
    "TT-BGDĐT": "Bộ Giáo dục và Đào tạo",
    "TT-BCT": "Bộ Công Thương",
    "TT-BKHĐT": "Bộ Kế hoạch và Đầu tư",
    "TT-BTNMT": "Bộ Tài nguyên và Môi trường",
    "TT-BLĐTBXH": "Bộ Lao động - Thương binh và Xã hội",
    "TT-BTP": "Bộ Tư pháp",
    "TT-BYT": "Bộ Y tế",
    "TT-BXD": "Bộ Xây dựng",
    "TT-BGTVT": "Bộ Giao thông vận tải",
    "TT-BNNPTNT": "Bộ Nông nghiệp và Phát triển nông thôn",
}


def _make_corp_author(name: str) -> Author:
    clean = re.sub(r"\s+", " ", (name or "").strip().rstrip(".,;")).strip()
    low = clean.lower()
    return Author(last_name=low, initials=[], full_first_names=[], normalized=low, raw=clean)


def parse_vn_legal_reference(text: str) -> Optional[Citation]:
    """Parse a Vietnamese legal document reference entry per TDTU §2.6.1.

    Supports:
        1. Hiến pháp: ``Hiến pháp 2013.``
        2. Đạo luật / Bộ luật: ``Luật Doanh nghiệp (Luật số 68/2014/QH13) ngày 26/12/2014.``
        3. Văn bản dưới luật: ``Nghị định số 23/2015/NĐ-CP của Chính phủ ngày 16/02/2015 về ...``
    """
    if not text:
        return None
    normalized_text = re.sub(r"\s+", " ", text.strip())
    lead_m = _VN_LEGAL_LIST_PREFIX_RE.match(normalized_text)
    numeric_index = (
        int(lead_m.group("b_idx"))
        if lead_m and lead_m.group("b_idx")
        else None
    )
    cleaned = normalized_text[lead_m.end():].strip() if lead_m else normalized_text
    if not cleaned:
        return None
    clean_title = cleaned.rstrip(".,; ").strip()
    title_norm = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", clean_title.lower())).strip()

    # 1. Hiến pháp
    const_m = _VN_CONSTITUTION_RE.match(cleaned)
    if const_m:
        year = const_m.group("year")
        return Citation(
            raw_text=normalized_text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="vn_legal_document",
            numeric_index=numeric_index,
            title=clean_title,
            title_normalized=title_norm,
            year=year,
            venue="Quốc hội",
            authors=[
                _make_corp_author("Hiến pháp"),
                _make_corp_author("Quốc hội"),
            ],
            confidence=0.95,
        )

    # 2. Đạo luật / Bộ luật / Pháp lệnh
    law_m = _VN_LAW_RE.match(cleaned)
    if law_m and not re.match(r"^(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s*\(\s*\d{4}\s*\)\.", cleaned, re.IGNORECASE):
        has_legal_marker = bool(
            re.search(
                r"\((?:Bộ\s+luật|Luật|Pháp\s+lệnh)?\s*(?:số\s*)?\d+[\d/A-ZĐa-z\-–]+\)"
                r"|\bsố\s+\d+[\d/A-ZĐa-z\-–]+"
                r"|\bngày\s+\d{1,2}\s*(?:[/-]|tháng)\s*\d{1,2}\s*(?:[/-]|năm)\s*(?:19|20)\d{2}"
                r"|\bnăm\s+(?:19|20)\d{2}\b",
                cleaned,
                re.IGNORECASE,
            )
        )
        if has_legal_marker:
            # Extract short law name before (Luật số ...), số ..., ngày ..., or năm YYYY
            name_m = re.match(
                r"^(?P<name>(?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s+[^().\n]+?)"
                r"(?=\s*\(|\s+số\s+\d|\s+ngày\s+\d|\s+năm\s+(?:19|20)\d{2}|[.,;]|$)",
                cleaned,
                re.IGNORECASE,
            )
            law_name = name_m.group("name").strip().rstrip(",") if name_m else clean_title

            # Extract year: prefer enactment date, then code /YYYY/, then any 4-digit year
            date_y = re.search(
                r"\bngày\s+\d{1,2}\s*(?:[/-]|tháng)\s*\d{1,2}\s*(?:[/-]|năm)\s*((?:19|20)\d{2})\b",
                cleaned,
                re.IGNORECASE,
            )
            code_y = re.search(r"/((?:19|20)\d{2})/", cleaned)
            any_y = re.search(r"\b((?:19|20)\d{2})\b", cleaned)
            year = (
                date_y.group(1)
                if date_y
                else (code_y.group(1) if code_y else (any_y.group(1) if any_y else None))
            )

            authors = [_make_corp_author(law_name), _make_corp_author("Quốc hội")]
            code_full_m = re.search(
                r"((?:Bộ\s+luật|Luật|Pháp\s+lệnh)\s+số\s+[\d/A-ZĐa-z\-–]+)",
                cleaned,
                re.IGNORECASE,
            )
            if code_full_m:
                authors.append(_make_corp_author(code_full_m.group(1)))

            return Citation(
                raw_text=normalized_text,
                citation_type=CitationType.REFERENCE_LIST,
                style=CitationStyle.APA,
                matched_pattern="vn_legal_document",
                numeric_index=numeric_index,
                title=clean_title,
                title_normalized=title_norm,
                year=year,
                venue="Quốc hội",
                authors=authors,
                confidence=0.95,
            )

    # 3. Văn bản dưới luật (Nghị định, Thông tư, Quyết định, Nghị quyết, Chỉ thị)
    sublaw_m = _VN_SUBLAW_RE.match(cleaned)
    if sublaw_m:
        doc_type = re.sub(r"\s+", " ", sublaw_m.group("doc_type")).strip()
        doc_code = sublaw_m.group("doc_code").strip().rstrip(".,;")

        # Extract issuing agency after "của ..."
        agency: Optional[str] = None
        agency_m = re.search(
            r"\bcủa\s+(?P<agency>[^,.\n]+?)"
            r"(?=\s+ngày\s+\d|\s+về\s+|\s+ban\s+hành|\s+quy\s+định|\s+hướng\s+dẫn|\s+sửa\s+đổi|[.,]|$)",
            cleaned,
            re.IGNORECASE,
        )
        if agency_m:
            agency = agency_m.group("agency").strip()
        else:
            code_upper = doc_code.upper()
            for suffix_key, mapped_agency in _SUBLAW_AGENCY_SUFFIX_MAP.items():
                if suffix_key in code_upper:
                    agency = mapped_agency
                    break

        date_y = re.search(
            r"\bngày\s+\d{1,2}\s*(?:[/-]|tháng)\s*\d{1,2}\s*(?:[/-]|năm)\s*((?:19|20)\d{2})\b",
            cleaned,
            re.IGNORECASE,
        )
        code_y = re.search(r"/((?:19|20)\d{2})/", doc_code)
        any_y = re.search(r"\b((?:19|20)\d{2})\b", cleaned)
        year = (
            date_y.group(1)
            if date_y
            else (code_y.group(1) if code_y else (any_y.group(1) if any_y else None))
        )

        authors: list[Author] = []
        if agency:
            authors.append(_make_corp_author(agency))
        authors.append(_make_corp_author(f"{doc_type} số {doc_code}"))
        authors.append(_make_corp_author(f"{doc_type} {doc_code}"))

        return Citation(
            raw_text=normalized_text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="vn_legal_document",
            numeric_index=numeric_index,
            title=clean_title,
            title_normalized=title_norm,
            year=year,
            venue=agency or doc_type,
            authors=authors,
            confidence=0.95,
        )

    return None


def is_vn_legal_reference(text: str) -> bool:
    """Return True if ``text`` is a Vietnamese legal document reference entry."""
    return parse_vn_legal_reference(text) is not None


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

        # Normalize whitespace and repair broken URLs with space after slash
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r"(https?://[^\s/]+(?:/[^\s/]+)*/)\s+([A-Za-z0-9_\-]+)", r"\1\2", text)

        # Check for TDTU Vietnamese legal document entry (§2.6.1)
        legal_cit = parse_vn_legal_reference(text)
        if legal_cit is not None:
            return legal_cit

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

    def _is_non_apa_structure(self, authors_str: str, title: str, text: str) -> bool:
        """Return True if matched groups actually belong to Harvard/ACM/Nature/Chicago."""
        clean_auth = re.sub(r"^\[\s*\d+\s*\]\s*", "", (authors_str or "")).strip()
        # Authors block in APA cannot contain quoted titles, volume/issue markers, or trailing numbers
        if re.search(r'["\u201c\u201d]|\b(?:vol|no|pp)\.\s*\d|\d+\s*,\s*\d+\s*$|:\s*\d+\s*$', clean_auth, re.IGNORECASE):
            return True
        if re.search(r"\d\s*$", clean_auth) and not re.search(r"\b(?:19|20)\d{2}\b", clean_auth):
            return True
        # Title in APA cannot start with punctuation like ',' or ':'
        if not title or title[0] in ",:;":
            return True
        # Harvard check: no period after (Year) AND (quoted title or Harvard edition/pp./Place:Publisher)
        no_dot_after_year = bool(
            re.search(r"\(\s*(?:19|20)\d{2}[a-z]?\s*\)\s+(?!\.)", text)
        )
        if no_dot_after_year:
            if title[0] in "'\"‘“" or re.search(
                r"\b\d+(?:st|nd|rd|th)\s+edn?\.?\b|,\s*pp?\.\s*\d", text, re.IGNORECASE
            ):
                return True
        return False

    def _parse_apa_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse standard APA reference entry."""
        authors_raw = match.group("authors") or ""
        title_raw = (match.group("title") or "").strip()
        if self._is_non_apa_structure(authors_raw, title_raw, text):
            return None

        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_reference_entry",
        )

        # Extract authors (strip any leading [N] marker before parsing)
        authors_str = match.group("authors")
        if authors_str:
            authors_str = re.sub(r"^\[\s*\d+\s*\]\s*", "", authors_str).strip()
            citation.authors = self._parse_authors(authors_str)

        # Extract year (for "(n.d.)" entries, only fallback to explicit Retrieved/Accessed year, not URL path years)
        citation.year = match.group("year")
        if not citation.year and not match.group("nd"):
            venue_no_url = re.sub(r"https?://\S+", "", match.group("venue") or "")
            venue_year_m = re.search(r"\b((?:19|20)\d{2})\b", venue_no_url)
            if venue_year_m:
                citation.year = venue_year_m.group(1)
        suffix = match.group("suffix") or match.groupdict().get("nd_suffix")
        citation.year_suffix = suffix if suffix else None

        # Extract title and venue (rest of the text after title)
        title = match.group("title").strip()
        venue = match.group("venue").strip()

        # Rejoin title if it was split at an abbreviation, middle initial, or decimal (e.g. "Tp. HCM.", "fMRI vs. SPECT", "Dr. Amen", "Daniel G. Amen", "Version 24.12")
        while (
            re.search(
                r"(?:\b(?:Tp|TP|ThS|TS|PGS|GS|vs|Dr|Mr|Mrs|Ms|St|Jr|Sr|U\.S|U\.K|No|Vol|Ed|Fig|al|Inc|Ltd|Co|Corp|[A-Z][a-z]{2,}\s+[A-Z])|\d)$",
                title,
            )
            and ". " in venue
        ):
            next_part, rest_venue = venue.split(". ", 1)
            if next_part.strip().lower().startswith(("http://", "https://")):
                break
            title = f"{title}. {next_part.strip()}"
            venue = rest_venue.strip()

        # Detect Title-first anonymous APA entry where the article title precedes (Year)/(n.d.)
        # and only the site/publisher name + URL follow (Year):
        # e.g. "CAC payback period vs LTV: CAC ratio. (2022). MetricHQ. https://..."
        venue_without_url = re.sub(r"\s*(?:https?://|www\.)\S+\s*", "", venue).strip().rstrip(".")
        if (
            not venue_without_url
            and authors_str
            and not re.search(r"[A-Z][a-z]+,\s*[A-Z]\.", authors_str)
            and (
                any(ch in authors_str for ch in (":", "?", "|"))
                or authors_str[0].islower()
                or re.search(
                    r"\b(?:what\s+is|how\s+to|metrics\s+for|state\s+of|top\s+\d+|top\s+fitness|growth|statistics|payback\s+period)\b",
                    authors_str,
                    re.I,
                )
            )
        ):
            real_title = authors_str.strip().rstrip(".")
            real_site = title.strip().rstrip(".")
            title = real_title
            venue = real_site
            citation.authors = [_make_corp_author(real_site)]

        # TDTU Vietnamese thesis format uses a comma after (Luận án ...), e.g.:
        # "Title (Luận án Tiến sĩ kinh tế), Trường Đại học Kinh tế Tp. HCM, Việt Nam."
        combined_tv = f"{title}. {venue}"
        thesis_comma_m = re.match(
            r"^(?P<t>.+?\((?:(?:Luận\s+án|Luận\s+văn|Khóa\s+luận|Đồ\s+án|Tiểu\s+luận)[^)]*"
            r"|[^)]*(?:thesis|dissertation)[^)]*)\))\s*,\s*(?P<v>.+)$",
            combined_tv,
            flags=re.IGNORECASE,
        )
        if thesis_comma_m:
            title = thesis_comma_m.group("t").strip()
            venue = thesis_comma_m.group("v").strip()

        citation.title = title
        citation.title_normalized = self._normalize_title(title)

        self._parse_venue(citation, venue)

        # Extract DOI if present
        doi_match = re.search(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s\]\)\,;]+)", text, re.IGNORECASE)
        if doi_match:
            citation.doi = doi_match.group(1).rstrip(".,;")
        else:
            doi_match = re.search(r"(10\.\d{4,9}/[^\s\]\)\,;]+)", text)
            if doi_match:
                citation.doi = doi_match.group(1).rstrip(".,;")

        # Extract URL if present (non-DOI internet reference, including line-wrapped URLs)
        self._extract_url_into(citation, text)

        citation.confidence = self._estimate_confidence(citation)
        return citation

    @staticmethod
    def _extract_url_into(citation: Citation, text: str) -> None:
        """Extract non-DOI URL into citation.url, handling line-break spaces after https://."""
        if citation.url:
            return
        url_match = re.search(r"(https?://\s*[^\s\]\)\,;]+)", text, re.IGNORECASE)
        if url_match:
            raw_url = re.sub(r"\s+", "", url_match.group(1)).rstrip(".,;")
            if not re.search(r"doi\.org/10\.\d{4,9}/", raw_url, re.IGNORECASE):
                citation.url = raw_url

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

        # Extract authors (strip any leading [N] marker before parsing)
        authors_str = match.group("authors")
        if authors_str:
            authors_str = re.sub(r"^\[\s*\d+\s*\]\s*", "", authors_str).strip()
            citation.authors = self._parse_authors(authors_str)

        # Extract year (for "(n.d.)" entries, fallback to retrieval/access year in venue)
        citation.year = match.group("year")
        if not citation.year:
            venue_year_m = re.search(r"\b((?:19|20)\d{2})\b", match.group("venue") or "")
            if venue_year_m:
                citation.year = venue_year_m.group(1)
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

        self._extract_url_into(citation, text)
        citation.confidence = self._estimate_confidence(citation)
        return citation

    def _parse_apa_simple_entry(
        self, match: re.Match, text: str
    ) -> Optional[Citation]:
        """Parse simple APA reference entry."""
        authors_raw = match.group("authors") or ""
        title_raw = (match.group("title") or "").strip()
        if self._is_non_apa_structure(authors_raw, title_raw, text):
            return None

        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_simple_entry",
        )

        # Extract authors (strip any leading [N] marker before parsing)
        authors_str = match.group("authors")
        if authors_str:
            authors_str = re.sub(r"^\[\s*\d+\s*\]\s*", "", authors_str).strip()
            citation.authors = self._parse_authors(authors_str)

        # Extract year (for "(n.d.)" entries, fallback to retrieval/access year in venue)
        citation.year = match.group("year")
        if not citation.year:
            venue_year_m = re.search(r"\b((?:19|20)\d{2})\b", match.group("venue") or "")
            if venue_year_m:
                citation.year = venue_year_m.group(1)
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

        self._extract_url_into(citation, text)
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
            before_year = text[:year_match.start()].strip()
            after_year = text[year_match.end():].strip()
            # Reject if (Year) is at the end of a Nature/ACM/Chicago entry or preceded by quotes/numbers
            if re.search(r'["\u201c\u201d]|\d\s*$', before_year):
                return None
            if after_year.startswith((":", ",")) or after_year in ("", "."):
                return None
            citation.year = year_match.group(1)
            if year_match.group(2):
                citation.year_suffix = year_match.group(2)
            clean_auth = re.sub(r"^\[\s*\d+\s*\]\s*", "", before_year).strip()
            if clean_auth:
                citation.authors = self._parse_authors(clean_auth)

        # Try to extract title (text between year and period after it)
        if year_match:
            after_year = text[year_match.end():]
            title_match = re.search(r"\.?\s*(.+?)(?:\.|$)", after_year)
            if title_match:
                title = title_match.group(1).strip()
                if title and len(title) > 5:
                    citation.title = title
                    citation.title_normalized = self._normalize_title(title)

        # Try to extract DOI
        doi_match = re.search(r"(10\.\d{4,9}/[^\s\]\)\,;]+)", text)
        if doi_match:
            citation.doi = doi_match.group(1).rstrip(".,;")

        self._extract_url_into(citation, text)
        citation.confidence = self._estimate_confidence(citation)
        # Only return if we have meaningful data (title OR year with some other field)
        return citation if citation.title or citation.year else None

    def _parse_authors(self, authors_str: str) -> list[str]:
        """Parse author string into list of authors.

        Args:
            authors_str: Author string like "Smith, J., & Jones, A."

        Returns:
            List of author strings (via parse_authors)
        """
        return parse_authors(authors_str)

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

        # Web retrieval clause (TDTU §2.6.2: "Retrieved March 21, 2011, from ..." / "Truy cập 21/7/2016, từ ...")
        # Do not mistake the retrieval date's year for a journal volume number.
        if re.match(r"^(?:Retrieved|Truy\s+cập|Accessed)\b", venue_text, flags=re.IGNORECASE):
            citation.venue = venue_text.rstrip(".,")
            return

        # Book chapter / conference proceedings page range: "(pp. 29-43)" or "(tr. 29-43)"
        chapter_pages_m = re.search(
            r"\((?:pp?\.?|tr\.?|trang)\s*(?P<pages>\d+\s*[-–]\s*\d+|\d+)\)",
            venue_text,
            flags=re.IGNORECASE,
        )
        if chapter_pages_m and not citation.pages:
            citation.pages = re.sub(r"\s+", "", chapter_pages_m.group("pages"))

        # Extract volume and issue: "Journal, 10(2)" or "Journal, 126(5D)"
        vol_issue_match = re.search(
            r"(?P<journal>.+?),\s*(?P<vol>\d+[A-Za-z0-9\-]*)\((?P<issue>[A-Za-z0-9\-]+)\)",
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

        # Check for author name pattern (capitalized word, including Vietnamese uppercase)
        author_pattern = rf"{_UPPER_VN}[a-zA-ZÀ-ỹ]"
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
        narrative_pattern = rf"{_UPPER_VN}[a-zA-ZÀ-ỹ]*(?:[\s,&]+(?:và|and|et\s+al\.?|cộng\s+sự|cs\.?|{_UPPER_VN}[a-zA-ZÀ-ỹ]*))*\s+\(\d{{4}}"
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
