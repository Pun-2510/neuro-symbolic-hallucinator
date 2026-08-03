"""Section segmenter — phân vùng Document thành body / bibliography / appendix.

Mục đích (v1.2 §3.4):
    Phân vùng PDF trước khi trích citation & detect style. Cần để:
        - CitationLinker loại trừ in-text ở reference section.
        - StyleDetector phân tích tín hiệu trong body vs bibliography tách biệt.
        - ReferenceListParser chỉ chạy trên bibliography section.

Chiến lược:
    1. Tìm header "References / Bibliography / Tài liệu tham khảo" đánh dấu
       bắt đầu bibliography section.
    2. Tìm header "Appendix / Phụ lục" (nếu có) đánh dấu appendix.
    3. Footnote tách riêng (Page footer chứa số footnote).
    4. Figure caption tách riêng (regex "Figure N:" / "Hình N:").
    5. Phần còn lại = body.

Output: list[DocumentSection] có section_type + (start_page, end_page) + text.

References:
    v1.2 §3.4 (Phân vùng tài liệu)
    v1.2 §3.5 (tín hiệu style từ body vs bibliography)
    config.linking.exclude_sections (để CitationLinker dùng)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

from integrity_checker.extraction.base import Document, Page

logger = logging.getLogger(__name__)


class SectionType(str, Enum):
    """Loại section trong Document.

    Cố ý string Enum để serialize/UI. ORDERING ổn định nhưng không quan trọng.
    """

    BODY = "body"
    BIBLIOGRAPHY = "bibliography"
    APPENDIX = "appendix"
    FOOTNOTE = "footnote"
    FIGURE_CAPTION = "figure_caption"
    UNKNOWN = "unknown"

    @property
    def is_citable(self) -> bool:
        """True nếu CitationExtractor nên chạy trên section này.

        - BODY: có
        - BIBLIOGRAPHY: KHÔNG (chỉ ReferenceListParser chạy)
        - APPENDIX: KHÔNG (out-of-scope MVP)
        - FOOTNOTE: CÓ (footnote có thể trích citation — tuỳ chọn, mặc định False)
        - FIGURE_CAPTION: KHÔNG
        - UNKNOWN: CÓ (mặc định an toàn)
        """
        return self in {
            SectionType.BODY,
            SectionType.UNKNOWN,
        }


# --- Header patterns ---
# Pattern ở ĐẦU dòng (line-start), case-insensitive, cho phép số + whitespace trước.

_BIBLIOGRAPHY_HEADERS = re.compile(
    r"^\s*(?:\d+\.?\s+)?(?:"
    r"references?|bibliography|works?\s+cited|"
    r"tài\s+liệu\s+tham\s+khảo|danh\s+mục\s+tài\s+liệu|"
    r"参考文献|参考文献$"
    r")\s*[:.]?\s*$",
    re.IGNORECASE,
)

_APPENDIX_HEADERS = re.compile(
    r"^\s*(?:\d+\.?\s+)?(?:appendix|phụ\s+lục|annex|附件)\b",
    re.IGNORECASE,
)

_FOOTNOTE_PATTERN = re.compile(r"^\s*\d{1,3}\.\s+\S")   # "1. Text..."
_FIGURE_CAPTION_PATTERN = re.compile(
    r"^\s*(?:figure|fig\.?|hình|ảnh|table|bảng)\s+\d+",
    re.IGNORECASE,
)


@dataclass
class DocumentSection:
    """Một vùng văn bản trong Document đã được phân loại.

    Attributes:
        section_type: SectionType enum.
        start_page, end_page: 1-indexed inclusive.
        text: ghép text từ tất cả page trong range (đã qua preprocessing nhẹ).
        page_break_used: True nếu section gộp nhiều page, False nếu chỉ 1 page.
    """

    section_type: SectionType
    start_page: int
    end_page: int
    text: str = ""
    page_break_used: bool = False
    metadata: dict = field(default_factory=dict)


class SectionSegmenter:
    """Phân vùng Document thành các DocumentSection.

    Strategy:
        1. Tìm header "References" / "Tài liệu tham khảo" — đánh dấu BIBLIOGRAPHY.
        2. Tìm header "Appendix" / "Phụ lục" — đánh dấu APPENDIX (chỉ khi SAU bibliography).
        3. Các page giữa cover → bibliography = BODY.
        4. Các page giữa bibliography → appendix = BODY (chỉ chứa reference list còn lại).
        5. Footnote / figure caption: tách RIÊNG ở cuối mỗi page nếu regex match.
    """

    def __init__(self) -> None:
        # Có thể config sau; hiện tại dùng hardcoded regex (an toàn)
        pass

    def segment(self, doc: Document) -> list[DocumentSection]:
        """Phân vùng Document.

        Returns:
            list[DocumentSection] theo thứ tự xuất hiện trong Document.
        """
        if not doc.pages:
            return []

        # Bước 1: xác định ranh giới page
        boundaries = self._find_boundaries(doc)

        # Bước 2: tạo sections từ boundaries
        sections: list[DocumentSection] = []

        # BODY từ đầu đến bibliography
        if boundaries["biblio_start"] > 1:
            sections.append(self._build_section(
                SectionType.BODY, 1, boundaries["biblio_start"] - 1, doc
            ))

        # BIBLIOGRAPHY — chỉ tạo nếu thực sự tìm thấy header
        if boundaries["biblio_start"] > 0:
            biblio_end = (
                boundaries["appendix_start"] - 1
                if boundaries["appendix_start"]
                else doc.num_pages
            )
            if boundaries["biblio_start"] <= biblio_end:
                sections.append(self._build_section(
                    SectionType.BIBLIOGRAPHY,
                    boundaries["biblio_start"],
                    biblio_end,
                    doc,
                ))
        else:
            # Không có bibliography → fallback toàn bộ document là BODY
            sections.append(self._build_section(
                SectionType.BODY, 1, doc.num_pages, doc
            ))

        # APPENDIX
        if boundaries["appendix_start"]:
            sections.append(self._build_section(
                SectionType.APPENDIX,
                boundaries["appendix_start"],
                doc.num_pages,
                doc,
            ))

        # Bước 3: tách footnote/figure-caption riêng từ body
        body_sections = [s for s in sections if s.section_type == SectionType.BODY]
        if body_sections:
            extras = self._extract_per_page_extras(body_sections[0], doc)
            sections = body_sections[:1] + extras + sections[len(body_sections):]

        return sections

    # -- internals --

    def _find_boundaries(self, doc: Document) -> dict[str, int]:
        """Tìm (biblio_start, appendix_start).

        Returns:
            dict có 'biblio_start' (1-indexed) và 'appendix_start' (1-indexed hoặc None).
        """
        biblio_start = 0
        appendix_start = 0

        for page in doc.pages:
            # Tìm dòng đầu tiên khớp bibliography header
            if biblio_start == 0 and self._page_has_bibliography_header(page):
                biblio_start = page.page_num
                logger.debug("Bibliography starts at page %d", page.page_num)
                continue

            # Tìm appendix header — chỉ SAU bibliography
            if biblio_start > 0 and appendix_start == 0 and self._page_has_appendix_header(page):
                appendix_start = page.page_num
                logger.debug("Appendix starts at page %d", page.page_num)
                break

        return {
            "biblio_start": biblio_start,
            "appendix_start": appendix_start or None,
        }

    @staticmethod
    def _page_has_bibliography_header(page: Page) -> bool:
        """True nếu page có dòng khớp bibliography header (English / Vietnamese / Chinese)."""
        for line in page.text.splitlines()[:5]:  # chỉ check 5 dòng đầu
            if _BIBLIOGRAPHY_HEADERS.match(line):
                return True
        return False

    @staticmethod
    def _page_has_appendix_header(page: Page) -> bool:
        """True nếu page có dòng khớp appendix header."""
        for line in page.text.splitlines()[:5]:
            if _APPENDIX_HEADERS.match(line):
                return True
        return False

    def _build_section(
        self,
        section_type: SectionType,
        start_page: int,
        end_page: int,
        doc: Document,
    ) -> DocumentSection:
        """Ghép text của tất cả page trong range."""
        parts: list[str] = []
        pages = [p for p in doc.pages if start_page <= p.page_num <= end_page]
        for p in pages:
            if p.text:
                parts.append(p.text)
        text = "\n".join(parts)
        return DocumentSection(
            section_type=section_type,
            start_page=start_page,
            end_page=end_page,
            text=text,
            page_break_used=(end_page > start_page),
        )

    @staticmethod
    def _extract_per_page_extras(
        body_section: DocumentSection, doc: Document
    ) -> list[DocumentSection]:
        """Tách footnote / figure-caption RIÊNG từ body.

        Mỗi page trong body: các dòng khớp footnote/figure-caption pattern
        → tách thành section riêng (để CitationExtractor KHÔNG chạy trên đó).

        Hiện tại: trả về 1 placeholder section rỗng nếu có extras,
        hoặc [] nếu không. Full implementation sẽ tách dòng ở tuần 6–7 tiếp
        (cần Page-level extras).
        """
        # TODO: implement per-page extras khi CitationExtractor hỗ trợ
        #       per-section extraction. Hiện tại body đã gộp hết, không cần
        #       tách thêm.
        return []
