"""CitationExtractor — regex + heuristics, trích xuất Citation[] từ Document."""

from __future__ import annotations

import re
from typing import Iterable

from integrity_checker.extraction.base import Document
from integrity_checker.extraction.regex_patterns import CITATION_PATTERNS, CitationPattern
from integrity_checker.extraction.text_preprocessor import TextPreprocessor
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


# Header / footer keywords để phát hiện reference section
_REFERENCE_HEADERS = re.compile(
    r"^\s*(references?|bibliography|works\s+cited|tài\s+liệu\s+tham\s+khảo)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class CitationExtractor:
    """Trích xuất citation từ Document đã parse.

    # TODO(user): tuần 6–7 — thêm:
        - Author NER (spaCy en_core_web_lg) để bắt author list chính xác
        - English-Vietnamese citation handling
        - Author override khi apa_reference_entry đã parse sẵn
    """

    def __init__(self, patterns: Iterable[CitationPattern] | None = None) -> None:
        self.patterns = list(patterns) if patterns is not None else list(CITATION_PATTERNS)
        self._compiled = [(p, re.compile(p.pattern)) for p in self.patterns]
        self.preprocessor = TextPreprocessor()

    # -- public API --

    def extract_from_document(self, doc: Document) -> list[Citation]:
        """Trích xuất tất cả citation từ Document. Dedup theo (raw_text, page)."""
        citations: list[Citation] = []
        for page in doc.pages:
            text = self.preprocessor.normalize(page.text)
            page_citations = self._extract_from_text(text, page.page_num)
            citations.extend(page_citations)

        citations = self._dedupe(citations)
        for c in citations:
            c.confidence = self._estimate_confidence(c)
        return citations

    def find_reference_section(self, doc: Document) -> tuple[int, int] | None:
        """Trả về (start_page, end_page) của reference section. None nếu không thấy."""
        for i, page in enumerate(doc.pages):
            if _REFERENCE_HEADERS.search(page.text):
                start = i + 1  # 1-indexed
                # Thường reference list kéo dài 1–5 trang
                end = min(i + 5, doc.num_pages)
                return (start, end)
        return None

    # -- internals --

    def _extract_from_text(self, text: str, page_num: int) -> list[Citation]:
        results: list[Citation] = []
        for pattern_def, compiled in self._compiled:
            for m in compiled.finditer(text):
                citation = Citation(
                    raw_text=m.group(0).strip(),
                    citation_type=pattern_def.type,
                    style=pattern_def.style,
                    page_num=page_num,
                    matched_pattern=pattern_def.name,
                )
                # Parse các field con
                self._populate_fields(citation, m.group(0))
                results.append(citation)
        return results

    def _populate_fields(self, citation: Citation, raw: str) -> None:
        """Best-effort trích DOI / URL / year từ raw text."""
        if not citation.doi:
            m = re.search(r"10\.\d{4,9}/[^\s\]\)\,;]+", raw)
            if m:
                citation.doi = m.group(0).rstrip(".")
        if not citation.url:
            m = re.search(r"https?://[^\s\]\)\,;]+", raw)
            if m:
                citation.url = m.group(0).rstrip(".")
        if not citation.year:
            m = re.search(r"\b(19|20)\d{2}[a-z]?\b", raw)
            if m:
                citation.year = m.group(0)

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