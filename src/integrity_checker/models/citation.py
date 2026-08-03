"""Citation data model — output của extraction module."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CitationType(str, Enum):
    """Phân loại citation theo vị trí / format."""

    IN_TEXT = "in_text"               # (Smith, 2020), Smith et al. (2020)
    NUMERIC = "numeric"               # [1], [1,2], [1-5]
    REFERENCE_LIST = "reference_list"  # entry ở cuối bài
    DOI = "doi"                       # chỉ có DOI
    URL = "url"                       # chỉ có URL
    UNKNOWN = "unknown"


class CitationStyle(str, Enum):
    """Citation style — dùng cho format consistency check."""

    APA = "APA"
    MLA = "MLA"
    CHICAGO = "Chicago"
    IEEE = "IEEE"
    VANCOUVER = "Vancouver"
    UNKNOWN = "unknown"


_YEAR_RE = re.compile(r"\b(19|20)\d{2}[a-z]?\b")
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\]\)\,;]+")
_URL_RE = re.compile(r"https?://[^\s\]\)\,;]+")


def parse_year_safe(raw: str) -> Optional[str]:
    """Trích xuất năm (4 chữ số, 19xx hoặc 20xx) từ chuỗi. Trả None nếu không có."""
    if not raw:
        return None
    m = _YEAR_RE.search(raw)
    return m.group(0) if m else None


@dataclass
class Citation:
    """Một citation được trích xuất từ PDF.

    Attributes:
        raw_text: chuỗi gốc lấy từ text (giữ nguyên để debug/audit).
        citation_type: loại citation.
        style: style (APA/MLA/...) nếu nhận diện được.
        authors: danh sách tác giả (best-effort từ NER / heuristics).
        year: năm xuất bản (nếu parse được).
        title: tiêu đề (chỉ có ở reference list, in-text thường không có).
        venue: tên tạp chí / hội nghị.
        doi, url, volume, issue, pages: metadata khác.
        page_num, paragraph_num: vị trí trong PDF (1-indexed).
        matched_pattern: tên regex pattern đã match (để debug).
        raw_in_text_citation: đối với reference-list entry, lưu cả citation
            in-text tương ứng nếu match được (dùng cho in-text ↔ bib consistency).
        confidence: 0.0–1.0, do extractor tự ước lượng (heuristic).
    """

    raw_text: str
    citation_type: CitationType = CitationType.UNKNOWN
    style: CitationStyle = CitationStyle.UNKNOWN

    authors: list[str] = field(default_factory=list)
    year: Optional[str] = None
    title: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

    # NEW v1.2 — cho bidirectional linker + duplicate detector
    title_normalized: Optional[str] = None
    year_suffix: Optional[str] = None
    order_index: int = 0
    numeric_index: Optional[int] = None

    page_num: int = 0
    paragraph_num: int = 0

    matched_pattern: Optional[str] = None
    raw_in_text_citation: Optional[str] = None
    confidence: float = 0.0

    # NEW v1.2 — optional reference_id cho bidirectional linker output.
    # None trước khi chạy CitationLinker; được set thành str ('ref-0007')
    # sau khi linker match occurrence ↔ reference entry.
    # Backward compatible: callers cũ không truyền field này vẫn chạy bình thường.
    reference_id: Optional[str] = None

    def to_search_query(self) -> str:
        """Ghép chuỗi truy vấn để gọi API theo title + author + year.

        Ưu tiên: title > author (last-name) > year > raw_text.

        Lưu ý: 'Vaswani, A.' → last name là 'Vaswani' (token đầu, vì APA format
        là "Họ, Tên viết tắt"). Hàm này cố gắng lấy last-name heuristic — cần
        được tinh chỉnh khi parse author chuẩn hơn.
        """
        parts: list[str] = []
        if self.title:
            parts.append(self.title)
        if self.authors:
            first = self.authors[0].strip()
            if first:
                # APA: "Lastname, F." → token trước dấu phẩy là last-name
                # MLA / raw: "First Last" → token cuối là last-name
                if "," in first:
                    parts.append(first.split(",")[0].strip())
                else:
                    parts.append(first.split()[-1])
        if self.year:
            parts.append(self.year)
        if not parts:
            parts.append(self.raw_text[:120])
        return " ".join(parts)

    @classmethod
    def from_raw(cls, raw: str) -> "Citation":
        """Constructor tiện dụng — trích DOI/URL/year từ raw text."""
        c = cls(raw_text=raw.strip())
        c.doi = _DOI_RE.search(raw).group(0) if _DOI_RE.search(raw) else None
        c.url = _URL_RE.search(raw).group(0) if _URL_RE.search(raw) else None
        c.year = parse_year_safe(raw)
        return c