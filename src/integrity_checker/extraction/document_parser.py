"""DocumentParser — orchestrator fuse 3 nguồn: PyMuPDF + GROBID + SectionSegmenter.

Tuần 8 (v1.2 §3.4) — Pipeline:
    1. ``_load_pdf_text(pdf_path)`` — PyMuPDF → Document (text + pages).
    2. ``_load_grobid_tei(pdf_path)`` — GROBID HTTP → GrobidOutput (header, sections,
       citations, bibliography). Graceful fail nếu GROBID không available.
    3. ``_merge(text_doc, grobid)`` — ưu tiên GROBID bibliography (chuẩn hoá từ
       TEI XML), dùng regex parser fallback cho text-only. Trả unified ``Document``
       với body/bibliography/appendix + citations + sections.

References:
    v1.2 §3.4 (Full-text extraction + GROBID)
    v1.2 §5.2 (DocumentParser scaffold — tuần 8)
    config.extraction.grobid.{enabled, url, timeout_seconds}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from integrity_checker.config import Settings, get_settings
from integrity_checker.extraction.base import Document, Page
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.extraction.grobid_parser import (
    GrobidOutput,
    call_grobid_fulltext,
    parse_tei,
)
from integrity_checker.extraction.grobid_service import get_grobid_manager
from integrity_checker.extraction.mupdf_parser import MuPdfParser
from integrity_checker.extraction.reference_parser import ReferenceListParser
from integrity_checker.extraction.section_segmenter import (
    DocumentSection,
    SectionSegmenter,
    SectionType,
)
from integrity_checker.models.citation import Citation

logger = logging.getLogger(__name__)


def _set_fallback_warning(
    grobid_manager, grobid_status: str, warnings: list[str]
) -> str:
    """Set fallback warning and update grobid_status."""
    if grobid_manager:
        status = grobid_manager.check_health()
        if status.value == "unhealthy":
            grobid_status = "unhealthy"
            warnings.append("GROBID unhealthy — container running but API not responding")
        elif status.value == "stopped":
            grobid_status = "stopped"
            warnings.append("GROBID container stopped — fallback to regex")
        else:
            grobid_status = "unknown"
            warnings.append(f"GROBID status: {status.value} — fallback to regex")
    else:
        grobid_status = "unavailable"
        warnings.append("GROBID not available — fallback to regex")
    return grobid_status


@dataclass
class ParsedDocument:
    """Document đã được parse + segment + extract — output chính của DocumentParser.

    Attributes:
        document: raw ``Document`` (text + pages + metadata) từ PyMuPDF.
        sections: ``DocumentSection[]`` từ SectionSegmenter (body / bibliography /
            appendix). Rỗng nếu segment fail.
        body_citations: citation in-text ở body sections (Citation[]).
        references: citation ở bibliography section (Citation[]).
        appendix_citations: citation ở appendix section (Citation[]) — out-of-scope
            MVP nhưng vẫn track.
        grobid: GrobidOutput nếu GROBID available; None nếu fail/disabled.
        parser_warnings: list[str] các vấn đề phát hiện (fallback chain, v.v.).
        parser_used: str — 'grobid', 'regex', 'hybrid' tùy parser nào được dùng.
        grobid_status: str — 'available', 'unavailable', 'disabled', 'unknown'.
    """

    document: Document
    sections: list[DocumentSection] = field(default_factory=list)
    body_citations: list[Citation] = field(default_factory=list)
    references: list[Citation] = field(default_factory=list)
    appendix_citations: list[Citation] = field(default_factory=list)
    grobid: Optional[GrobidOutput] = None
    parser_warnings: list[str] = field(default_factory=list)
    parser_used: str = "unknown"
    grobid_status: str = "unknown"

    @property
    def has_grobid(self) -> bool:
        """True nếu GROBID thành công (không phải fallback)."""
        return self.grobid is not None and self.grobid.is_available

    @property
    def body_text(self) -> str:
        """Ghép text từ body sections (để downstream pipeline đọc)."""
        return "\n\n".join(
            s.text for s in self.sections if s.section_type == SectionType.BODY
        )

    @property
    def bibliography_text(self) -> str:
        """Ghép text từ bibliography section."""
        return "\n\n".join(
            s.text
            for s in self.sections
            if s.section_type == SectionType.BIBLIOGRAPHY
        )


class DocumentParser:
    """Orchestrator fuse PyMuPDF + GROBID + SectionSegmenter → ParsedDocument.

    Strategy (v1.2 §3.4):
        1. PyMuPDF ALWAYS chạy (text layer fallback).
        2. GROBID nếu enabled — ưu tiên cho bibliography (TEI XML chuẩn hoá).
        3. SectionSegmenter dùng text từ PyMuPDF (GROBID section text là bonus).
        4. CitationExtractor chạy trên body sections → body_citations.
        5. ReferenceListParser chạy trên bibliography:
            - ưu tiên GROBID bibliography (nếu có)
            - fallback regex parser trên PyMuPDF text
        6. Nếu cả 2 fail → trả ParsedDocument với warnings + section rỗng.
    """

    def __init__(
        self,
        config: Settings | None = None,
        *,
        mupdf_parser: MuPdfParser | None = None,
        grobid_post_fn=None,
    ) -> None:
        """Khởi tạo DocumentParser.

        Args:
            config: Settings instance; mặc định lấy từ ``get_settings()``.
            mupdf_parser: optional MuPdfParser instance (cho test injection).
            grobid_post_fn: optional HTTP POST callable (cho test injection).
        """
        self.config = config or get_settings()
        self._mupdf_parser = mupdf_parser or MuPdfParser()
        self._grobid_post_fn = grobid_post_fn
        self._section_segmenter = SectionSegmenter()
        self._citation_extractor = CitationExtractor()
        self._reference_parser = ReferenceListParser()

    # ---------- Public API ----------

    def parse(self, pdf_path: str, use_service_manager: bool = True) -> ParsedDocument:
        """Parse PDF end-to-end → ParsedDocument.

        Args:
            pdf_path: absolute path tới PDF.
            use_service_manager: Nếu True, sử dụng GrobidServiceManager để check
                                 health và sử dụng cache.

        Returns:
            ParsedDocument với sections + citations + grobid (optional).
            Không raise — fail chain được ghi vào ``parser_warnings``.
        """
        warnings: list[str] = []
        parser_used = "unknown"
        grobid_status = "unknown"

        # 1. PyMuPDF (always)
        try:
            text_doc = self._load_pdf_text(pdf_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PyMuPDF parse failed: %s", exc)
            warnings.append(f"PyMuPDF failed: {exc}")
            text_doc = Document(
                file_path=pdf_path,
                num_pages=0,
                pages=[],
                parser_used="mupdf_fallback_empty",
                errors=[str(exc)],
            )
            parser_used = "regex"  # Fallback to regex since PyMuPDF failed

        # 2. GROBID (optional)
        grobid_out: Optional[GrobidOutput] = None

        # Try to use GrobidServiceManager for better integration
        grobid_manager = None
        if use_service_manager and self.config.extraction.grobid.enabled:
            try:
                grobid_manager = get_grobid_manager()
            except Exception as exc:
                logger.debug("GrobidServiceManager not available: %s", exc)

        if self.config.extraction.grobid.enabled:
            try:
                # Check if GROBID is available (via service manager)
                grobid_available = (
                    grobid_manager and grobid_manager.check_health().value == "available"
                )

                if grobid_available:
                    grobid_status = "available"
                    parser_used = "grobid"

                    # Try to get from cache first
                    cached_tei = grobid_manager.get_from_cache(pdf_path)

                    if cached_tei:
                        logger.info("Using cached TEI XML for: %s", pdf_path)
                        grobid_out = parse_tei(cached_tei)
                    else:
                        # Call GROBID via service manager
                        grobid_out = self._load_grobid_tei(pdf_path, grobid_manager)

                    # Save to cache if successful
                    if grobid_out and grobid_out.is_available:
                        tei_xml = grobid_out.raw_tei_xml
                        if tei_xml:
                            grobid_manager.save_to_cache(pdf_path, tei_xml)

                else:
                    # GROBID not available via service manager
                    # Still try via injected grobid_post_fn (for tests/mock)
                    if self._grobid_post_fn is not None:
                        # Use injected mock/test function
                        grobid_out = self._load_grobid_tei(pdf_path)
                        if grobid_out and grobid_out.is_available:
                            grobid_status = "available"
                            parser_used = "grobid"
                        else:
                            grobid_status = _set_fallback_warning(grobid_manager, grobid_status, warnings)
                            parser_used = "regex"
                    else:
                        grobid_status = _set_fallback_warning(grobid_manager, grobid_status, warnings)
                        parser_used = "regex"

                if grobid_out is None or not grobid_out.is_available:
                    if not grobid_out:
                        grobid_out = GrobidOutput(is_available=False, error_message="GROBID processing failed")
                    elif not grobid_out.is_available:
                        warnings.append(f"GROBID processing failed: {grobid_out.error_message or 'unknown error'}")

            except Exception as exc:  # noqa: BLE001
                logger.warning("GROBID failed: %s", exc)
                warnings.append(f"GROBID failed: {exc}")
                grobid_out = None
                parser_used = "regex"
                grobid_status = "error"
        else:
            warnings.append("GROBID disabled in config")
            parser_used = "regex"
            grobid_status = "disabled"

        # 3. Merge
        parsed = self._merge(text_doc, grobid_out)
        parsed.parser_warnings = warnings
        parsed.parser_used = parser_used
        parsed.grobid_status = grobid_status
        return parsed

    # ---------- Step 1: PyMuPDF ----------

    def _load_pdf_text(self, pdf_path: str) -> Document:
        """Load PDF qua PyMuPDF → Document (text + pages + metadata)."""
        return self._mupdf_parser.parse(pdf_path)

    # ---------- Step 2: GROBID ----------

    def _load_grobid_tei(
        self,
        pdf_path: str,
        grobid_manager=None,
    ) -> Optional[GrobidOutput]:
        """Gọi GROBID → parse TEI XML → GrobidOutput.

        Args:
            pdf_path: Path to PDF file.
            grobid_manager: Optional GrobidServiceManager for caching.

        Returns:
            GrobidOutput nếu thành công (``is_available=True``).
            ``None`` nếu GROBID không enabled / fail / empty TEI.
        """
        if not self.config.extraction.grobid.enabled:
            return None

        # Use grobid_manager if provided
        if grobid_manager:
            tei_xml = grobid_manager.process_pdf(pdf_path)
        else:
            tei_xml = call_grobid_fulltext(
                pdf_path,
                self.config.extraction.grobid,
                http_post_fn=self._grobid_post_fn,
            )

        if not tei_xml:
            return GrobidOutput(
                is_available=False,
                error_message="empty TEI XML from GROBID",
            )

        out = parse_tei(tei_xml)
        if not out.is_available:
            return None
        return out

    # ---------- Step 3: Merge ----------

    def _merge(
        self,
        text_doc: Document,
        grobid: Optional[GrobidOutput],
    ) -> ParsedDocument:
        """Fuse text + GROBID → ParsedDocument.

        Sections: dùng SectionSegmenter trên text_doc (consistent với sections
        body/bibliography/appendix).
        Citations: CitationExtractor trên body sections.
        References: ưu tiên GROBID bibliography → fallback regex.
        """
        # 3.1 Sections từ text_doc
        sections = self._section_segmenter.segment(text_doc)

        # 3.2 Body citations (regex trên body sections)
        body_citations = self._extract_body_citations(sections)

        # 3.3 References (ưu tiên GROBID, fallback regex)
        references = self._extract_references(sections, grobid)

        # 3.4 Appendix citations (chỉ track, không analyse)
        appendix_citations = self._extract_appendix_citations(sections)

        return ParsedDocument(
            document=text_doc,
            sections=sections,
            body_citations=body_citations,
            references=references,
            appendix_citations=appendix_citations,
            grobid=grobid,
        )

    # ---------- Helpers ----------

    def _extract_body_citations(
        self, sections: list[DocumentSection]
    ) -> list[Citation]:
        """Run CitationExtractor trên body sections."""
        citations: list[Citation] = []
        for section in sections:
            if section.section_type != SectionType.BODY:
                continue
            # Build a temporary Document for this section
            try:
                # Page numbers from section.start_page..end_page
                section_text = section.text
                if not section_text:
                    continue
                # Tạo fake Document để CitationExtractor chạy
                doc = Document(
                    file_path="",
                    num_pages=section.end_page - section.start_page + 1,
                    pages=[
                        Page(
                            page_num=section.start_page + i,
                            text=section_text,
                            has_text_layer=True,
                        )
                        for i in range(
                            max(1, section.end_page - section.start_page + 1)
                        )
                    ],
                )
                # Chỉ lấy citations từ page đầu của section (đơn giản hoá)
                citations.extend(self._citation_extractor.extract_from_document(doc))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Body citation extraction failed: %s", exc)
        return citations

    def _extract_references(
        self,
        sections: list[DocumentSection],
        grobid: Optional[GrobidOutput],
    ) -> list[Citation]:
        """Trích references — ưu tiên GROBID bibliography, fallback regex."""
        # Ưu tiên 1: GROBID bibliography (đã chuẩn hoá từ TEI XML)
        if grobid is not None and grobid.is_available and grobid.bibliography:
            return self._grobid_to_citations(grobid)

        # Ưu tiên 2: regex parser trên bibliography section
        # Bug fix: parse_reference_section gọi find_reference_section để tìm ref header,
        # nhưng Document đã chỉ chứa bibliography text rồi (không tìm thấy header).
        # Fix: gọi trực tiếp _split_entries và _parse_entry thay vì parse_reference_section.
        for section in sections:
            if section.section_type == SectionType.BIBLIOGRAPHY and section.text:
                try:
                    # Light normalize — KHÔNG qua _fix_broken_lines
                    pp = self._citation_extractor.preprocessor
                    section_text = pp._normalize_unicode(pp._fix_ligatures(section.text))

                    entries = self._reference_parser._split_entries(section_text)
                    citations: list[Citation] = []
                    for idx, entry in enumerate(entries, start=1):
                        if len(entry) < 20:
                            continue
                        citation = self._reference_parser._parse_entry(
                            entry, order_index=idx, page_num=section.start_page
                        )
                        if citation:
                            citations.append(citation)
                    if citations:
                        logger.info(f"Extracted {len(citations)} references from bibliography section")
                        return citations
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Reference parser failed: %s", exc)
        return []

    def _extract_appendix_citations(
        self, sections: list[DocumentSection]
    ) -> list[Citation]:
        """Trích citations ở appendix (out-of-scope MVP, nhưng track)."""
        citations: list[Citation] = []
        for section in sections:
            if section.section_type != SectionType.APPENDIX:
                continue
            if not section.text:
                continue
            doc = Document(
                file_path="",
                num_pages=section.end_page - section.start_page + 1,
                pages=[
                    Page(page_num=section.start_page, text=section.text, has_text_layer=True)
                ],
            )
            citations.extend(self._citation_extractor.extract_from_document(doc))
        return citations

    @staticmethod
    def _grobid_to_citations(grobid: GrobidOutput) -> list[Citation]:
        """Convert GrobidOutput.bibliography → Citation[]."""
        from integrity_checker.models.citation import (
            Citation,
            CitationStyle,
            CitationType,
        )

        citations: list[Citation] = []
        for idx, bib in enumerate(grobid.bibliography, start=1):
            authors_raw = [a.full_name for a in bib.authors if a.full_name]
            year = bib.year
            # Suffix nếu year có 4-char
            year_suffix = None
            if year and len(year) > 4:
                year_suffix = year[4:]
                year = year[:4]

            # Build human-readable raw_text from structured fields (not raw XML!)
            raw_parts = []
            if authors_raw:
                raw_parts.append(", ".join(authors_raw))
            raw_parts.append(f"({year or 'n.d.'})" if year else "")
            if bib.title:
                raw_parts.append(bib.title)
            if bib.venue:
                raw_parts.append(bib.venue)
            if bib.doi:
                raw_parts.append(f"DOI: {bib.doi}")
            raw_text = " ".join(raw_parts) or f"{bib.title or ''} ({year or 'n.d.'})"

            c = Citation(
                raw_text=raw_text,
                citation_type=CitationType.REFERENCE_LIST,
                # GROBID mặc định trả APA-like format
                style=CitationStyle.APA if not authors_raw else CitationStyle.APA,
                authors=authors_raw,
                year=year,
                title=bib.title,
                venue=bib.venue,
                doi=bib.doi,
                order_index=idx,
                # GROBID bibliography entries are structured and may not
                # retain the printed ``[N]`` marker.  Their document order is
                # the numeric reference index used by IEEE/Vancouver in-text
                # citations.
                numeric_index=idx,
                year_suffix=year_suffix,
                confidence=0.9,  # GROBID quality thường cao
            )
            citations.append(c)
        return citations
