"""ReferenceListParser — parse các entry ở cuối bài (References section)."""

from __future__ import annotations

import re
from typing import Iterable

from integrity_checker.extraction.base import Document
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.models.citation import Citation


class ReferenceListParser:
    """Parse danh sách References ở cuối tiểu luận.

    # TODO(user): tuần 7 — thêm:
        - MLA / Chicago / IEEE parsers
        - Author parsing chuẩn (visa, "Smith, J., & Jones, A.")
        - Title trong ngoặc kép vs. italics
    """

    APA_ENTRY_RE = re.compile(
        r"""
        (?P<authors>^[\w\.\-\s,À-ž&]+?)        # authors block
        \s*\(\s*(?P<year>\d{4}[a-z]?)\s*\)    # (YYYY)
        \.?\s*
        (?P<title>[^\.]+?)                    # title (up to first period)
        \.?\s*
        (?P<venue>[^\.]+?)                    # venue (up to next period)
        """,
        re.VERBOSE | re.MULTILINE,
    )

    def __init__(self, extractor: CitationExtractor | None = None) -> None:
        self.extractor = extractor or CitationExtractor()

    def parse_reference_section(self, doc: Document) -> list[Citation]:
        """Trích và parse các entry ở reference section.

        Returns:
            List[Citation] với citation_type = REFERENCE_LIST.
        """
        ref_range = self.extractor.find_reference_section(doc)
        if ref_range is None:
            return []
        start, end = ref_range
        section_text = "\n".join(p.text for p in doc.pages if start <= p.page_num <= end)
        section_text = self.extractor.preprocessor.normalize(section_text)

        entries = self._split_entries(section_text)
        citations: list[Citation] = []
        for entry in entries:
            citation = self._parse_apa_entry(entry, page_num=start)
            if citation:
                citations.append(citation)
        return citations

    def _split_entries(self, text: str) -> list[str]:
        """Tách các entry riêng (heuristic: xuống dòng + viết hoa đầu dòng)."""
        raw_lines = [l.strip() for l in text.splitlines() if l.strip()]
        entries: list[str] = []
        current: list[str] = []
        for line in raw_lines:
            # Entry mới bắt đầu bằng chữ hoa sau 1 dòng citation hoàn chỉnh
            if current and re.match(r"^[A-ZÀ-Ž]", line):
                entries.append(" ".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            entries.append(" ".join(current))
        return [e for e in entries if len(e) > 20]

    def _parse_apa_entry(self, entry: str, page_num: int) -> Citation | None:
        """Parse 1 APA entry. Trả None nếu không match."""
        m = self.APA_ENTRY_RE.search(entry)
        if not m:
            return None
        citation = Citation(
            raw_text=entry.strip(),
            page_num=page_num,
            matched_pattern="apa_reference_entry",
        )
        citation.year = m.group("year")
        citation.title = m.group("title").strip().rstrip(".")
        citation.venue = m.group("venue").strip().rstrip(".")
        citation.authors = self._parse_authors(m.group("authors"))
        # DOI có thể nằm ở cuối entry
        doi_m = re.search(r"10\.\d{4,9}/[^\s\]\)\,;]+", entry)
        if doi_m:
            citation.doi = doi_m.group(0).rstrip(".")
        return citation

    def _parse_authors(self, raw: str) -> list[str]:
        """Parse 'Smith, J., & Jones, A.' → ['Smith, J.', 'Jones, A.']"""
        if not raw:
            return []
        # Split trên '&' hoặc ', and'
        raw = re.sub(r"\s+and\s+", ", ", raw, flags=re.IGNORECASE)
        raw = raw.replace("&", ",")
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        # Ghép "Họ, Tên" thành 1 token
        authors: list[str] = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and re.match(r"^[A-Z]\.?$", parts[i + 1].strip()):
                authors.append(f"{parts[i]}, {parts[i + 1]}")
                i += 2
            else:
                authors.append(parts[i])
                i += 1
        return authors