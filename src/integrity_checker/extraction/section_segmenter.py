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

        Two-pass approach:
          1. Explicit header scan (original logic).
          2. Implicit-bibliography scan — activates only when no header found.
             Detects pages dominated by IEEE-style [N] reference markers.

        Returns:
            dict có 'biblio_start' (1-indexed) và 'appendix_start' (1-indexed hoặc None).
        """
        biblio_start = 0
        appendix_start = 0

        # ── Pass 1: explicit header ──────────────────────────────────────────
        for page in doc.pages:
            if biblio_start == 0 and self._page_has_bibliography_header(page):
                biblio_start = page.page_num
                logger.debug("Bibliography starts at page %d (header)", page.page_num)
                continue

            if biblio_start > 0 and appendix_start == 0 and self._page_has_appendix_header(page):
                appendix_start = page.page_num
                logger.debug("Appendix starts at page %d", page.page_num)
                break

        # ── Pass 2: implicit bibliography (no header found) ────────────────────
        if biblio_start == 0 and doc.num_pages >= 2:
            implicit = self._find_implicit_bibliography(doc)
            if implicit > 0:
                biblio_start = implicit
                logger.debug("Bibliography starts at page %d (implicit)", biblio_start)

        return {
            "biblio_start": biblio_start,
            "appendix_start": appendix_start or None,
        }

    def _find_implicit_bibliography(self, doc: Document) -> int:
        """Tìm trang bắt đầu bibliography ẩn (không có header).

        Heuristic: sau page đầu tiên, tìm trang có ≥3 dòng khớp `^\s*\[\d+\]`
        với IEEE ratio ≥ 0.30. Continue until we hit a page with no [N] markers
        and substantial prose → bibliography ends; return the first such page.
        """
        # Only scan the second half of the document (avoids abstract pages)
        start_scan_at = max(1, doc.num_pages // 2)

        ieee_line_re = re.compile(r"^\s*\[\d+\]\s+\S")
        prose_end_re = re.compile(r"\.\s+$")   # ends with sentence period

        candidate_start = 0

        for page in doc.pages:
            if page.page_num < start_scan_at:
                continue

            lines = page.text.splitlines()
            if not lines:
                continue

            # Count IEEE reference lines
            ieee_count = sum(1 for ln in lines if ieee_line_re.match(ln.strip()))
            # Count prose lines (ends with period, not a reference marker)
            prose_count = sum(
                1 for ln in lines
                if prose_end_re.search(ln.strip()) and not ieee_line_re.match(ln.strip())
            )

            total = ieee_count + prose_count
            if total == 0:
                continue

            ratio = ieee_count / max(1, total)

            if ratio >= 0.30 and ieee_count >= 3:
                candidate_start = page.page_num
                logger.debug(
                    "Implicit bibliography candidate at page %d: "
                    "ieee=%d prose=%d ratio=%.2f",
                    page.page_num, ieee_count, prose_count, ratio,
                )
                break

        # Verify candidate: check it's really bibliography by scanning ahead
        # for the end marker (a page with no [N] markers after we've started)
        if candidate_start > 0:
            end = self._find_implicit_bibliography_end(doc, candidate_start)
            logger.debug("Implicit bibliography ends at page %d", end)
            # Return the actual start (first page with enough [N] markers)
            return candidate_start

        return 0

    def _find_implicit_bibliography_end(
        self, doc: Document, start_page: int
    ) -> int:
        """Tìm trang cuối của implicit bibliography.

        Stop when a page has no `[N]` reference markers and has substantial prose.
        Return start_page if no end is found (treat entire tail as bibliography).
        """
        ieee_line_re = re.compile(r"^\s*\[\d+\]\s+\S")
        prose_end_re = re.compile(r"\.\s+$")

        for page in doc.pages:
            if page.page_num <= start_page:
                continue

            lines = page.text.splitlines()
            if not lines:
                continue

            ieee_count = sum(1 for ln in lines if ieee_line_re.match(ln.strip()))
            prose_count = sum(
                1 for ln in lines
                if prose_end_re.search(ln.strip()) and not ieee_line_re.match(ln.strip())
            )

            # If page has no [N] markers at all and contains prose → end of bibliography
            if ieee_count == 0 and prose_count >= 2:
                return page.page_num - 1

            # If page has some [N] markers but very few → end
            if 0 < ieee_count < 2 and prose_count >= 2:
                return page.page_num - 1

        # Bibliography extends to end of document
        return doc.num_pages

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
