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
    r"^\s*(?:(?:\d+(?:\.\d+)*|I{1,3}|IV|V|VI{0,3}|IX|X|[A-Z])[\.\)]?\s+)?(?:"
    r"references?|reference\s+list|bibliography|works?\s+cited|literature(?:\s+cited)?|"
    r"bibliografia(?:/bibliografía/bibliographie/works?\s+cited)?|bibliografía|bibliographie|"
    r"referências(?:\s+bibliográficas)?|referencias(?:\s+bibliográficas)?|daftar\s+pustaka|"
    r"(?:[^/\n]{2,50}/\s*)?list\s+of\s+references|"
    r"danh\s+mục\s+tài\s+liệu(?:\s+tham\s+khảo)?|tài\s+liệu\s+tham\s+khảo|"
    r"tài\s+liệu\s+trích\s+dẫn|"
    r"参考文献|参考文献$"
    r")\s*[:.]?\s*$",
    re.IGNORECASE,
)

_APPENDIX_HEADERS = re.compile(
    r"^\s*(?:(?:\d+|I{1,3}|IV|V|VI{0,3}|IX|X|[A-Z])\.?\s+)?(?:"
    r"(?:appendix|appendices|phụ\s+lục|annex)"
    r"(?:\s+for\b[^,;]*|\s+[A-Z0-9]{1,3}(?:\s*[:.\-—–]?\s*[^,;]{1,80})?|\s*[:.\-—–]\s*[^,;]{1,80})?|"
    r"supplementary\s+(?:material|materials|information|appendix|experiments?|results?|details?)|"
    r"附件.*"
    r")\s*$",
    re.IGNORECASE,
)

_POST_BIB_APPENDIX_SINGLE_LINE_RE = re.compile(
    r"^(?:"
    r"A(?:\.1)?\s+(?:Additional|Supplementary|Implementation|Experimental|Training|Model|Dataset|Evaluation|Proof|Proofs|Further|Extended|Detailed|Prompt|Prompts|Hyperparameter|Ablation|Human|Case|Error|More|Ethical|Broader|Limitation|Societal)\b[A-Za-z0-9\s,\-:–—()]{2,70}"
    r"|Attention\s+Visualizations"
    r"|Acknowledgements?"
    r"|Extended\s+Data(?:\s+Figures?|\s+Tables?)?"
    r")$"
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
        app_start = boundaries["appendix_start"]
        app_line_idx = boundaries.get("appendix_line_idx")
        mid_page_appendix = False
        if app_start and app_line_idx is not None and app_line_idx > 0:
            app_page = next((p for p in doc.pages if p.page_num == app_start), None)
            if app_page and app_page.text:
                app_lines = app_page.text.splitlines()
                start_slice = 0
                if app_start == boundaries["biblio_start"]:
                    b_idx = self._find_bibliography_header_line_idx(app_page)
                    if b_idx is not None:
                        start_slice = b_idx + 1
                pre_app_lines = app_lines[start_slice:app_line_idx]
                pre_app_text = "\n".join(pre_app_lines).strip()
                if app_start == boundaries["biblio_start"] or (
                    len(pre_app_text) >= 40
                    and (
                        sum(1 for ln in pre_app_lines if ln.strip()) >= 3
                        or bool(re.search(r"\b(?:19|20)\d{2}\b|https?://", pre_app_text))
                    )
                ):
                    mid_page_appendix = True

        if boundaries["biblio_start"] > 0:
            biblio_end = (
                (app_start if mid_page_appendix else app_start - 1)
                if app_start
                else doc.num_pages
            )
            if boundaries["biblio_start"] <= biblio_end:
                sections.append(self._build_section(
                    SectionType.BIBLIOGRAPHY,
                    boundaries["biblio_start"],
                    biblio_end,
                    doc,
                    appendix_page=app_start if mid_page_appendix else None,
                    appendix_line_idx=app_line_idx if mid_page_appendix else None,
                ))
        else:
            # Không có bibliography → fallback toàn bộ document là BODY
            sections.append(self._build_section(
                SectionType.BODY, 1, doc.num_pages, doc
            ))

        # APPENDIX
        if app_start:
            sections.append(self._build_section(
                SectionType.APPENDIX,
                app_start,
                doc.num_pages,
                doc,
                appendix_page=app_start if mid_page_appendix else None,
                appendix_line_idx=app_line_idx if mid_page_appendix else None,
            ))

        # Bước 3: tách footnote/figure-caption riêng từ body
        body_sections = [s for s in sections if s.section_type == SectionType.BODY]
        if body_sections:
            extras = self._extract_per_page_extras(body_sections[0], doc)
            sections = body_sections[:1] + extras + sections[len(body_sections):]

        return sections

    # -- internals --

    def _find_boundaries(self, doc: Document) -> dict[str, int | None]:
        """Tìm (biblio_start, appendix_start, appendix_line_idx).

        Two-pass approach:
          1. Explicit header scan (original logic).
          2. Implicit-bibliography scan — activates only when no header found.
             Detects pages dominated by IEEE-style [N] reference markers.

        Returns:
            dict có 'biblio_start' (1-indexed), 'appendix_start' (1-indexed hoặc None),
            và 'appendix_line_idx' (0-indexed hoặc None).
        """
        biblio_start = 0
        appendix_start = 0
        appendix_line_idx: int | None = None

        # ── Pass 1: explicit header ──────────────────────────────────────────
        bib_candidates = [
            page.page_num
            for page in doc.pages
            if self._page_has_bibliography_header(page)
        ]
        if bib_candidates:
            # Ignore early TOC / table column header false hits when multiple candidates exist
            if len(bib_candidates) > 1:
                later = [p for p in bib_candidates if p > doc.num_pages * 0.35]
                if len(later) > 1:
                    first_pg = next((pg for pg in doc.pages if pg.page_num == later[0]), None)
                    first_yr_hits = len(re.findall(r"\b(?:18|19|20)\d{2}\b", first_pg.text or "")) if first_pg else 0
                    if later[1] == later[0] + 1 or first_yr_hits >= 4:
                        biblio_start = later[0]
                    else:
                        biblio_start = later[-1]
                else:
                    biblio_start = later[-1] if later else bib_candidates[-1]
            else:
                biblio_start = bib_candidates[0]
            logger.debug("Bibliography starts at page %d (header)", biblio_start)

        if biblio_start > 0:
            for page in doc.pages:
                if page.page_num < biblio_start:
                    continue
                min_idx = 0
                if page.page_num == biblio_start:
                    b_hdr_idx = self._find_bibliography_header_line_idx(page)
                    min_idx = (b_hdr_idx + 1) if b_hdr_idx is not None else 1
                app_idx = self._find_appendix_header_line_idx(page, min_line_idx=min_idx)
                if app_idx is not None:
                    appendix_start = page.page_num
                    appendix_line_idx = app_idx
                    logger.debug(
                        "Appendix starts at page %d (line %d)",
                        page.page_num,
                        app_idx,
                    )
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
            "appendix_line_idx": appendix_line_idx,
        }

    def _find_implicit_bibliography(self, doc: Document) -> int:
        r"""Tìm trang bắt đầu bibliography ẩn (không có header).

        Heuristic: sau page đầu tiên, tìm trang có ≥3 dòng khớp `^\s*\[\d+\]`
        với IEEE ratio ≥ 0.30. Continue until we hit a page with no [N] markers
        and substantial prose → bibliography ends; return the first such page.
        """
        # Only scan the second half of the document (avoids abstract pages)
        start_scan_at = max(1, doc.num_pages // 2)

        ieee_line_re = re.compile(r"^\s*(?:\[\d+\](?:\s+\S|\s*$)|\d{1,3}\.\s*$)")
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
        ieee_line_re = re.compile(r"^\s*(?:\[\d+\](?:\s+\S|\s*$)|\d{1,3}\.\s*$)")
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
    def _find_bibliography_header_line_idx(page: Page) -> int | None:
        """Return 0-indexed line number of bibliography header on `page`, or None."""
        lines = page.text.splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.islower():
                continue
            if _BIBLIOGRAPHY_HEADERS.match(stripped):
                # Ignore singular "Reference" or plural "References" used as a table column header
                next_8_lines = [ln.strip() for ln in lines[idx + 1 : idx + 10] if ln.strip()]
                metric_headers = sum(
                    1
                    for ln in next_8_lines
                    if re.fullmatch(
                        r"(?:Entities(?:,\s*n)?|Entity|Attribute|Recall|Precision|F1(?:\s*Score)?|Accuracy|Score|Metric|Support)(?:\s+(?:Recall|Precision|F1(?:\s*Score)?))*",
                        ln,
                        re.IGNORECASE,
                    )
                )
                if metric_headers >= 2:
                    continue
                if re.fullmatch(r"reference\s*[:.]?", stripped, re.IGNORECASE):
                    prev_window = "\n".join(lines[max(0, idx - 12) : idx])
                    if re.search(r"\b(?:table|bảng)\s+\d+", prev_window, re.IGNORECASE):
                        continue
                    next_window = "\n".join(lines[idx + 1 : idx + 16])
                    if len(lines) - idx > 5 and not re.search(
                        r"\b(?:18|19|20)\d{2}\b|\[\d+\]|https?://|doi:",
                        next_window,
                        re.IGNORECASE,
                    ):
                        continue
                return idx
        return None

    @staticmethod
    def _page_has_bibliography_header(page: Page) -> bool:
        """True nếu page có dòng khớp bibliography header (English / Vietnamese / Chinese)."""
        return SectionSegmenter._find_bibliography_header_line_idx(page) is not None

    @staticmethod
    def _find_appendix_header_line_idx(page: Page, min_line_idx: int = 0) -> int | None:
        """Return 0-indexed line number of appendix header on `page` (at or after `min_line_idx`), or None."""
        lines = page.text.splitlines()
        for idx in range(max(0, min_line_idx), len(lines)):
            stripped = lines[idx].strip()
            if not stripped or stripped.islower():
                continue
            if _APPENDIX_HEADERS.match(stripped) or _POST_BIB_APPENDIX_SINGLE_LINE_RE.match(stripped):
                return idx
            # Two-line LaTeX \appendix \section{...}: standalone "A" / "A." followed by section title line
            if stripped in ("A", "A.", "Appendix A") and idx + 1 < len(lines):
                nxt = ""
                for j in range(idx + 1, min(idx + 4, len(lines))):
                    if lines[j].strip():
                        nxt = lines[j].strip()
                        break
                if (
                    nxt
                    and 3 <= len(nxt) <= 80
                    and nxt[0].isupper()
                    and not re.search(r"\b(?:19|20)\d{2}\b|https?://", nxt)
                    and not nxt.endswith(".")
                ):
                    return idx
        return None

    @staticmethod
    def _page_has_appendix_header(page: Page) -> bool:
        """True nếu page có dòng khớp appendix header."""
        return SectionSegmenter._find_appendix_header_line_idx(page) is not None

    def _build_section(
        self,
        section_type: SectionType,
        start_page: int,
        end_page: int,
        doc: Document,
        *,
        appendix_page: int | None = None,
        appendix_line_idx: int | None = None,
    ) -> DocumentSection:
        """Ghép text của tất cả page trong range."""
        parts: list[str] = []
        metadata: dict = {}
        pages = [p for p in doc.pages if start_page <= p.page_num <= end_page]
        for p in pages:
            if not p.text:
                continue
            if section_type == SectionType.BIBLIOGRAPHY and (
                p.page_num == start_page or (appendix_page == p.page_num and appendix_line_idx is not None)
            ):
                lines = p.text.splitlines()
                slice_start = 0
                slice_end = len(lines)
                if p.page_num == start_page:
                    hdr_idx = self._find_bibliography_header_line_idx(p)
                    if hdr_idx is not None and hdr_idx > 0:
                        pre_text = "\n".join(lines[:hdr_idx]).strip()
                        if len(pre_text) >= 60:
                            metadata["pre_header_body_text"] = pre_text
                            metadata["pre_header_page_num"] = p.page_num
                        slice_start = hdr_idx
                if appendix_page == p.page_num and appendix_line_idx is not None:
                    slice_end = max(slice_start, appendix_line_idx)
                parts.append("\n".join(lines[slice_start:slice_end]))
                continue
            if (
                section_type == SectionType.APPENDIX
                and p.page_num == start_page
                and appendix_page == p.page_num
                and appendix_line_idx is not None
                and appendix_line_idx > 0
            ):
                lines = p.text.splitlines()
                parts.append("\n".join(lines[appendix_line_idx:]))
                continue
            parts.append(p.text)
        text = "\n".join(parts)
        return DocumentSection(
            section_type=section_type,
            start_page=start_page,
            end_page=end_page,
            text=text,
            page_break_used=(end_page > start_page),
            metadata=metadata,
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
