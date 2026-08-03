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
    re.VERBOSE,
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
            citation = self._parse_entry(entry, order_index=idx, page_num=start)
            if citation:
                citations.append(citation)
        return citations

    def _split_entries(self, text: str) -> list[str]:
        """Tách các entry riêng.

        Heuristic:
            1. Bỏ prefix "References" / "Tài liệu tham khảo" / "Bibliography" ở
               đầu text.
            2. Nếu có dòng bắt đầu bằng `[N]` → đó là IEEE entry boundaries.
            3. APA/Vancouver: tách bằng cách tìm marker "(YYYY[a-z]?)" — mỗi
               marker mở đầu entry mới. Author block của entry mới bắt đầu
               ngay sau `. ` kết thúc entry trước (tìm `. ` gần nhất phía
               TRƯỚC marker).
            4. Trường hợp đặc biệt: chỉ 1 entry trong toàn text → trả nguyên.
        """
        # 1. Strip header prefix ở đầu text
        header_strip_re = re.compile(
            r"^\s*(?:references?|bibliography|tài\s+liệu\s+tham\s+khảo"
            r"|danh\s+mục\s+tài\s+liệu|works?\s+cited)\s*[:.]?\s*",
            flags=re.IGNORECASE,
        )
        text = header_strip_re.sub("", text, count=1).strip()

        if not text:
            return []

        # 2. IEEE: dòng [N] phân cách entries
        if re.search(r"^\s*\[\d+\]", text, flags=re.MULTILINE):
            entries: list[str] = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^\[\d+\]", line):
                    if entries and entries[-1]:
                        # (handled below — entries là list từng dòng IEEE)
                        pass
                    entries.append(line)
                else:
                    if entries:
                        entries[-1] = entries[-1] + " " + line
            return [e for e in entries if len(e) > 20]

        # 3. APA/Vancouver: dùng year marker
        # Tìm tất cả positions của "(YYYY[a-z]?)"
        year_re = re.compile(r"\(\s*(?:19|20)\d{2}[a-z]?\s*\)")
        markers = list(year_re.finditer(text))

        if len(markers) <= 1:
            # Chỉ 1 entry
            return [text] if len(text) > 20 else []

        # Tách entry bằng marker ", [A-Z]\.\s*\(YYYY\)" — điểm cuối author block
        # của entry mới. Entry mới bắt đầu từ VỊ TRÍ TRƯỚC ", [A-Z]\." (tức là
        # lùi thêm 1 prefix chứa "LastName" + particle).
        # Quy tắc: trong "Smith, J. (2020)" → initial_end = pos(sau "J. ").
        # Sau marker thứ 2, tìm ", [A-Z]\." cuối cùng trước marker thứ 2 → đó
        # là end of entry 1. Entry 2 bắt đầu từ đó.
        boundary_re = re.compile(r",\s+[A-ZÀ-Ý]\.\s*")
        entries: list[str] = []
        prev_start = 0
        for i in range(1, len(markers)):
            m = markers[i]
            # Tìm last ", [A-Z]\." trước marker — boundary HỢP LỆ có
            # khả năng là end of entry 1.
            candidates = list(boundary_re.finditer(text, prev_start, m.start()))
            if not candidates:
                continue
            # Lấy candidate cuối cùng có vị trí cuối (end pos) < m.start()
            last = candidates[-1]
            # Sanity: candidate phải gần marker (cách marker < 5 chars)
            if m.start() - last.end() > 5:
                # Có thể là author block giữa → skip
                continue
            boundary = last.end()
            entries.append(text[prev_start:boundary].strip())
            prev_start = boundary

        entries.append(text[prev_start:].strip())
        return [e for e in entries if len(e) > 20]

    def _parse_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        """Parse 1 entry. Thử lần lượt APA, IEEE, Vancouver."""
        # IEEE first (vì có marker [N] đặc trưng)
        if re.match(r"^\s*\[\d+\]", entry):
            return self._parse_ieee_entry(entry, order_index, page_num)

        citation = self._parse_apa_entry(entry, order_index, page_num)
        if citation:
            return citation

        # Vancouver last — heuristic loose
        return self._parse_vancouver_entry(entry, order_index, page_num)

    # -- per-style parsers --

    def _parse_apa_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        m = _APA_ENTRY_RE.search(entry)
        if not m:
            return None
        citation = Citation(
            raw_text=entry.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            page_num=page_num,
            matched_pattern="apa_reference_entry",
            order_index=order_index,
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

    def _parse_vancouver_entry(
        self, entry: str, order_index: int, page_num: int
    ) -> Citation | None:
        m = _VANCOUVER_ENTRY_RE.search(entry)
        if not m:
            return None
        citation = Citation(
            raw_text=entry.strip(),
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.VANCOUVER,
            page_num=page_num,
            matched_pattern="vancouver_reference_entry",
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
        return citation