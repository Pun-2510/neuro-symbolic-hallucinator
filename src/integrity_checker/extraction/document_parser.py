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
import re
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
from integrity_checker.models.citation import Citation, CitationStyle, CitationType

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
        # Preserve every in-text occurrence for report counts.  The pipeline
        # still deduplicates retrieval/verification work separately.
        self._citation_extractor = CitationExtractor(preserve_occurrences=True)
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

        total_chars = sum(len((p.text or "").strip()) for p in (text_doc.pages or []))
        is_scanned_empty_pdf = bool(
            text_doc.num_pages > 0
            and total_chars == 0
            and self._grobid_post_fn is None
        )
        if is_scanned_empty_pdf:
            warnings.append(
                "SCANNED_PDF_NO_TEXT_LAYER: Document has pages but 0 extractable text characters; OCR is required."
            )
            parser_used = "regex"
            grobid_status = "unavailable"

        # 2. GROBID (optional)
        grobid_out: Optional[GrobidOutput] = None

        # Try to use GrobidServiceManager for better integration
        grobid_manager = None
        if not is_scanned_empty_pdf and use_service_manager and self.config.extraction.grobid.enabled:
            try:
                grobid_manager = get_grobid_manager()
            except Exception as exc:
                logger.debug("GrobidServiceManager not available: %s", exc)

        if not is_scanned_empty_pdf and self.config.extraction.grobid.enabled:
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
                    if not any("GROBID" in w for w in warnings):
                        warnings.append(f"GROBID processing failed: {grobid_out.error_message or 'unknown error'}")
                    if grobid_status == "available":
                        grobid_status = "fallback"
                    parser_used = "regex"

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
        body_citations = self._extract_body_citations(sections, text_doc)

        # 3.3 References (ưu tiên GROBID, fallback regex)
        references = self._extract_references(sections, grobid, text_doc)

        # 3.3b MLA reference-guided in-text extraction (for MLA documents with page-less
        # parentheticals like "(Felson)", "(Goodreads)", or narrative "George Athas ... (260)")
        if references and any(c.style == CitationStyle.MLA for c in body_citations):
            guided = self._extract_mla_reference_guided_citations(
                sections, text_doc, body_citations, references
            )
            if guided:
                body_citations.extend(guided)

        # 3.3c Chicago Notes & Bibliography footnote extraction (BUG-02 & BUG-18)
        if references:
            body_citations = self._extract_chicago_footnote_citations(
                sections, text_doc, body_citations, references
            )

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
        self,
        sections: list[DocumentSection],
        source_doc: Document,
    ) -> list[Citation]:
        """Run CitationExtractor trên body sections, PAGE BY PAGE.

        ``DocumentSection`` only stores concatenated text, so we rebuild a
        per-page ``Document`` from ``source_doc`` to keep every citation's
        TRUE page number.  A section-wide synthetic page (the previous
        behaviour) reported every body citation as living on page 1, which
        made "cited on pages …" meaningless.  Each real page is passed through
        once, so an occurrence is still emitted once per literal appearance.
        """
        citations: list[Citation] = []
        by_page = {p.page_num: p for p in source_doc.pages}
        for section in sections:
            if section.section_type != SectionType.BODY:
                continue
            try:
                page_nums = [
                    n
                    for n in sorted(by_page)
                    if section.start_page <= n <= section.end_page
                    and by_page[n].text
                ]
                if not page_nums:
                    continue
                doc = Document(
                    file_path="",
                    num_pages=max(page_nums),
                    pages=[by_page[n] for n in page_nums],
                )
                citations.extend(self._citation_extractor.extract_from_document(doc))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Body citation extraction failed: %s", exc)
        return citations

    def _extract_mla_reference_guided_citations(
        self,
        sections: list[DocumentSection],
        source_doc: Document,
        existing_body: list[Citation],
        references: list[Citation],
    ) -> list[Citation]:
        """Extract MLA page-less parentheticals and narrative author citations guided by bibliography."""
        def _norm_key(s: str) -> str:
            s = s.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'").lower().strip()
            s = re.sub(r"\s*&\s*", " and ", s)
            s = re.sub(r"\s+", " ", s).strip(" .,;:\"'")
            return s

        key_to_ref_author: dict[str, str] = {}
        initial_surname_to_ref_author: dict[tuple[str, str], str] = {}
        narrative_patterns: list[tuple[re.Pattern[str], str, str]] = []

        for ref in references:
            if not ref.authors:
                continue
            first_a = ref.authors[0]
            first_raw = (
                getattr(first_a, "raw", None)
                or getattr(first_a, "last_name", None)
                or str(first_a)
            ).strip()
            if not first_raw:
                continue

            surname = first_raw.split(",", 1)[0].strip()
            given = first_raw.split(",", 1)[1].strip() if "," in first_raw else ""
            norm_surname = _norm_key(surname)
            if len(norm_surname) >= 3:
                key_to_ref_author.setdefault(norm_surname, first_raw)
                if norm_surname == "barnes" and given.lower().startswith("noble"):
                    key_to_ref_author.setdefault("barnes and noble", first_raw)

            if given and len(norm_surname) >= 3:
                given_first = given.split()[0].rstrip(".")
                if len(given_first) >= 1 and given_first[0].isalpha():
                    initial_surname_to_ref_author.setdefault(
                        (given_first[0].lower(), norm_surname), first_raw
                    )
                if len(given_first) >= 2:
                    full_norm = _norm_key(f"{given_first} {surname}")
                    key_to_ref_author.setdefault(full_norm, first_raw)
                    # Also handle inverted corporate name like "Goblin, Bookish" -> "bookish goblin"
                    inv_norm = _norm_key(f"{given} {surname}")
                    key_to_ref_author.setdefault(inv_norm, first_raw)
                    key_to_ref_author.setdefault(f"the {inv_norm}", first_raw)
                    pat = re.compile(
                        rf"\b{re.escape(given_first)}\s+(?:[A-Z]\.\s+)?{re.escape(surname).replace(chr(39), r'[' + chr(39) + chr(8217) + r']')}\b",
                        re.IGNORECASE,
                    )
                    narrative_patterns.append((pat, norm_surname, first_raw))

            if len(ref.authors) >= 2:
                sec_a = ref.authors[1]
                sec_raw = (
                    getattr(sec_a, "raw", None)
                    or getattr(sec_a, "last_name", None)
                    or str(sec_a)
                ).strip()
                sec_surname = _norm_key(sec_raw.split(",", 1)[0].strip())
                if len(sec_surname) >= 4:
                    key_to_ref_author.setdefault(sec_surname, first_raw)

            if ref.venue:
                v_norm = _norm_key(ref.venue.split(".")[0])
                if 4 <= len(v_norm) <= 45:
                    key_to_ref_author.setdefault(v_norm, first_raw)
                    key_to_ref_author.setdefault(v_norm.removeprefix("the "), first_raw)

            if ref.title and "penguin random house" in ref.title.lower():
                key_to_ref_author.setdefault("prh editors", first_raw)
                key_to_ref_author.setdefault("penguin random house", first_raw)

        by_page = {p.page_num: p for p in source_doc.pages}
        existing_by_page: dict[int, set[str]] = {}
        matched_ref_authors: set[str] = set()
        for c in existing_body:
            existing_by_page.setdefault(c.page_num or 0, set()).add((c.raw_text or "").strip())

        added: list[Citation] = []
        body_page_nums: list[int] = []
        for section in sections:
            if section.section_type != SectionType.BODY:
                continue
            for n in sorted(by_page):
                if section.start_page <= n <= section.end_page and by_page[n].text:
                    if n not in body_page_nums:
                        body_page_nums.append(n)

        for p_num in body_page_nums:
            p_text = re.sub(r"\s+", " ", by_page[p_num].text)
            page_existing = existing_by_page.get(p_num, set())
            for m in re.finditer(r"\(([^()]{2,260})\)", p_text):
                full_paren = m.group(0).strip()
                if full_paren in page_existing:
                    continue
                inside = m.group(1).strip()
                parts = [pt.strip() for pt in inside.split(";") if pt.strip()]
                for pt in parts:
                    pt_key = _norm_key(pt)
                    ref_auth = key_to_ref_author.get(pt_key) or key_to_ref_author.get(
                        pt_key.removeprefix("the ")
                    )
                    if not ref_auth:
                        pt_words = pt_key.split()
                        if len(pt_words) == 2 and pt_words[0]:
                            ref_auth = initial_surname_to_ref_author.get(
                                (pt_words[0][0], pt_words[1])
                            )
                    if ref_auth:
                        raw_cit = f"({pt})"
                        if raw_cit not in page_existing:
                            added.append(
                                Citation(
                                    raw_text=raw_cit,
                                    citation_type=CitationType.IN_TEXT,
                                    style=CitationStyle.MLA,
                                    page_num=p_num,
                                    authors=[ref_auth],
                                    matched_pattern="mla_ref_guided",
                                    confidence=0.85,
                                )
                            )
                            page_existing.add(raw_cit)
                            matched_ref_authors.add(_norm_key(ref_auth.split(",", 1)[0]))

        # Also check narrative "FirstName [M.] LastName" mentions for bibliography authors not yet matched
        for pat, norm_sn, ref_auth in narrative_patterns:
            if norm_sn in matched_ref_authors:
                continue
            for p_num in body_page_nums:
                if pat.search(by_page[p_num].text):
                    raw_cit = f"({ref_auth.split(',', 1)[0].strip()})"
                    added.append(
                        Citation(
                            raw_text=raw_cit,
                            citation_type=CitationType.IN_TEXT,
                            style=CitationStyle.MLA,
                            page_num=p_num,
                            authors=[ref_auth],
                            matched_pattern="mla_ref_guided",
                            confidence=0.85,
                        )
                    )
                    matched_ref_authors.add(norm_sn)
                    break

        return added

    def _extract_chicago_footnote_citations(
        self,
        sections: list[DocumentSection],
        source_doc: Document,
        existing_body: list[Citation],
        references: list[Citation],
    ) -> list[Citation]:
        """Extract Chicago Notes & Bibliography bottom-of-page footnotes and linkable citations."""
        import unicodedata

        if len(existing_body) >= 20 or sum(1 for c in existing_body if c.citation_type == CitationType.NUMERIC) >= 3:
            return existing_body

        def _fold(s: str) -> str:
            if not s:
                return ""
            s = s.replace("\u2019", "'").replace("\u2018", "'").replace("`", "'")
            s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
            return re.sub(r"\s+", " ", s.lower()).strip()

        by_page = {p.page_num: p for p in source_doc.pages}
        body_page_nums: list[int] = []
        for section in sections:
            if section.section_type != SectionType.BODY:
                continue
            for n in sorted(by_page):
                if section.start_page <= n <= section.end_page and by_page[n].text:
                    if n not in body_page_nums:
                        body_page_nums.append(n)
        if not body_page_nums:
            return existing_body

        # Build reference profiles for footnote matching
        _STOP = {"the", "and", "for", "with", "from", "into", "that", "this", "what", "when", "where", "how", "why"}
        ref_profiles = []
        surname_counts: dict[str, int] = {}
        for idx, ref in enumerate(references):
            first_raw = ""
            if ref.authors:
                a0 = ref.authors[0]
                first_raw = (getattr(a0, "raw", None) or getattr(a0, "last_name", None) or str(a0)).strip()
            surname = first_raw.split(",", 1)[0].strip() if first_raw else ""
            given = first_raw.split(",", 1)[1].strip() if "," in first_raw else ""
            sn_fold = _fold(surname)
            gv_fold = _fold(given.split()[0].rstrip(".")) if given else ""
            if sn_fold:
                surname_counts[sn_fold] = surname_counts.get(sn_fold, 0) + 1
            t_fold = _fold(ref.title or "")
            t_words = [
                w for w in re.findall(r"[a-z0-9]{4,}", t_fold)
                if w not in _STOP
            ]
            ref_profiles.append({
                "idx": idx,
                "ref": ref,
                "first_raw": first_raw or (ref.title or ""),
                "surname": surname or (ref.title or ""),
                "sn_fold": sn_fold,
                "gv_fold": gv_fold,
                "t_fold": t_fold,
                "t_words": t_words[:8],
                "url": (ref.url or "").strip().lower(),
                "doi": (ref.doi or "").strip().lower(),
            })

        # Extract numbered footnote blocks from body pages
        fn_blocks: list[tuple[int, int, str]] = []
        fn_starter_re = re.compile(
            r"^\s*(\d{1,3})(?:[\s\u00a0\u202f]+|(?=[A-Z\u201c\"]))(Ibid\.?.*|[A-Z\u201c\"].*)$"
        )
        has_ibid = False
        has_pub_city = 0

        for p_num in body_page_nums:
            lines = [ln.strip() for ln in by_page[p_num].text.splitlines() if ln.strip()]
            in_fn_zone = False
            curr_num: Optional[int] = None
            curr_lines: list[str] = []

            for l_idx, ln in enumerate(lines):
                if re.search(r"\.{4,}", ln):
                    continue
                m = fn_starter_re.match(ln)
                if m:
                    num_val = int(m.group(1))
                    rest_txt = m.group(2).strip()
                    is_ibid_line = bool(re.match(r"^Ibid\b", rest_txt, re.I))
                    looks_like_fn = (
                        is_ibid_line
                        or in_fn_zone
                        or l_idx >= max(2, len(lines) // 3)
                        or "," in rest_txt
                        or "\u201c" in rest_txt
                        or '"' in rest_txt
                        or "http" in rest_txt
                    )
                    if looks_like_fn and not re.match(r"^(?:Introduction|Conclusion|Chapter|Section|Abstract|Methodology|Results|Discussion|Bibliography|References)\b", rest_txt, re.I):
                        if curr_num is not None and curr_lines:
                            fn_blocks.append((p_num, curr_num, " ".join(curr_lines)))
                        in_fn_zone = True
                        curr_num = num_val
                        curr_lines = [rest_txt]
                        if is_ibid_line:
                            has_ibid = True
                        if re.search(r"\([^()]+:\s+[^()]+,\s*(?:18|19|20)\d{2}\)", rest_txt):
                            has_pub_city += 1
                        continue
                if in_fn_zone and curr_num is not None:
                    if re.match(r"^\d{1,3}$", ln):
                        continue
                    curr_lines.append(ln)
                    if re.search(r"\([^()]+:\s+[^()]+,\s*(?:18|19|20)\d{2}\)", ln):
                        has_pub_city += 1

            if curr_num is not None and curr_lines:
                fn_blocks.append((p_num, curr_num, " ".join(curr_lines)))

        if not (has_ibid or has_pub_city >= 2 or len(fn_blocks) >= 5):
            return existing_body

        def _match_fn_text(fn_txt: str) -> list[dict]:
            f_fold = _fold(fn_txt)
            f_low = fn_txt.lower()
            matched: list[dict] = []
            for prof in ref_profiles:
                if prof["doi"] and prof["doi"] in f_low:
                    matched.append(prof)
                    continue
                if prof["url"] and len(prof["url"]) >= 18 and prof["url"][:36] in f_low:
                    matched.append(prof)
                    continue
                sn = prof["sn_fold"]
                tw = prof["t_words"]
                tf = prof["t_fold"]
                sn_in = bool(sn and len(sn) >= 3 and re.search(rf"\b{re.escape(sn)}\b", f_fold))
                if not sn_in and sn and " " in sn:
                    last_tok = sn.split()[-1]
                    if len(last_tok) >= 4 and re.search(rf"\b{re.escape(last_tok)}\b", f_fold):
                        sn_in = True
                tw_hits = sum(1 for w in tw[:5] if re.search(rf"\b{re.escape(w)}\b", f_fold))
                if sn_in and (
                    tw_hits >= 1
                    or (surname_counts.get(sn, 0) == 1 and len(sn) >= 4)
                    or (prof["gv_fold"] and len(prof["gv_fold"]) >= 2 and re.search(rf"\b{re.escape(prof['gv_fold'])}\b", f_fold))
                ):
                    matched.append(prof)
                    continue
                if tf and len(tf) >= 12:
                    prefix_tf = tf[:min(len(tf), 38)].strip()
                    if len(prefix_tf) >= 12 and prefix_tf in f_fold:
                        matched.append(prof)
                        continue
                    if len(tw) >= 3 and tw_hits >= min(3, len(tw)):
                        matched.append(prof)
                        continue
            return matched

        chicago_cits: list[Citation] = []
        matched_ref_indices: set[int] = set()
        last_matched: list[dict] = []

        for p_num, _fn_num, fn_txt in fn_blocks:
            if re.match(r"^Ibid\b", fn_txt, re.I):
                curr_matched = last_matched[:1]
            else:
                curr_matched = _match_fn_text(fn_txt)
                if curr_matched:
                    last_matched = curr_matched
            for prof in curr_matched:
                ref = prof["ref"]
                matched_ref_indices.add(prof["idx"])
                sn_disp = prof["surname"]
                raw_cit = f"({sn_disp}, {ref.year})" if ref.year else f"({sn_disp})"
                chicago_cits.append(
                    Citation(
                        raw_text=raw_cit,
                        citation_type=CitationType.IN_TEXT,
                        style=CitationStyle.CHICAGO,
                        page_num=p_num,
                        authors=[prof["first_raw"]],
                        year=ref.year,
                        year_suffix=ref.year_suffix,
                        title=ref.title,
                        title_normalized=ref.title_normalized,
                        matched_pattern="chicago_footnote",
                        confidence=0.90,
                    )
                )

        # Fallback page scan for bibliography entries whose footnote wrapped across pages or lost its leading number
        for prof in ref_profiles:
            if prof["idx"] in matched_ref_indices:
                continue
            sn = prof["sn_fold"]
            tw = prof["t_words"]
            tf = prof["t_fold"]
            for p_num in body_page_nums:
                p_fold = _fold(by_page[p_num].text)
                sn_in = bool(sn and len(sn) >= 3 and re.search(rf"\b{re.escape(sn)}\b", p_fold))
                if not sn_in and sn and " " in sn:
                    last_tok = sn.split()[-1]
                    if len(last_tok) >= 4 and re.search(rf"\b{re.escape(last_tok)}\b", p_fold):
                        sn_in = True
                tw_hits = sum(1 for w in tw[:5] if re.search(rf"\b{re.escape(w)}\b", p_fold))
                prefix_tf = tf[:min(len(tf), 35)].strip() if tf else ""
                if (
                    (sn_in and (tw_hits >= 1 or (prof["gv_fold"] and len(prof["gv_fold"]) >= 3 and prof["gv_fold"] in p_fold) or (surname_counts.get(sn, 0) == 1 and len(sn) >= 5)))
                    or (len(prefix_tf) >= 14 and prefix_tf in p_fold)
                    or (len(tw) >= 3 and tw_hits >= 3)
                ):
                    ref = prof["ref"]
                    matched_ref_indices.add(prof["idx"])
                    sn_disp = prof["surname"]
                    raw_cit = f"({sn_disp}, {ref.year})" if ref.year else f"({sn_disp})"
                    chicago_cits.append(
                        Citation(
                            raw_text=raw_cit,
                            citation_type=CitationType.IN_TEXT,
                            style=CitationStyle.CHICAGO,
                            page_num=p_num,
                            authors=[prof["first_raw"]],
                            year=ref.year,
                            year_suffix=ref.year_suffix,
                            title=ref.title,
                            title_normalized=ref.title_normalized,
                            matched_pattern="chicago_footnote",
                            confidence=0.88,
                        )
                    )
                    break

        if not chicago_cits:
            return existing_body

        # Keep only existing_body citations that match a known bibliography author surname
        valid_existing = [
            c for c in existing_body
            if any(
                prof["sn_fold"] and len(prof["sn_fold"]) >= 3 and prof["sn_fold"] in _fold(c.raw_text)
                for prof in ref_profiles
            )
        ]
        return valid_existing + chicago_cits

    def _extract_references(
        self,
        sections: list[DocumentSection],
        grobid: Optional[GrobidOutput],
        source_doc: Optional[Document] = None,
    ) -> list[Citation]:
        """Trích references — GROBID + regex merge với deduplication.

        Phase 3 (GROBID adapter): Ưu tiên GROBID bibliography (structured),
        bổ sung regex entries bị GROBID bỏ sót. Deduplicate theo DOI →
        title+author+year → raw text similarity.

        Returns:
            list[Citation] với merged references và provenance tracking.
        """
        from integrity_checker.extraction.reference_parser import _is_fake_entry

        # Lấy references từ GROBID (primary) và lọc bỏ fake/appendix entries + gộp các entry
        # bị GROBID tách đôi TRƯỚC khi đánh lại order_index / numeric_index.
        bib_text_norm = " ".join(
            (s.text or "") for s in sections if s.section_type == SectionType.BIBLIOGRAPHY
        ).lower()
        appendix_text_norm = " ".join(
            (s.text or "") for s in sections if s.section_type == SectionType.APPENDIX
        ).lower()

        # If a multi-page document (3+ pages) has no BIBLIOGRAPHY section at all (e.g. 3.pdf screenplay),
        # ignore any GROBID-hallucinated references from body text.
        has_no_bib_section = bool(
            source_doc is not None
            and len(source_doc.pages or []) >= 3
            and not bib_text_norm.strip()
        )

        grobid_refs: list[Citation] = []
        if not has_no_bib_section and grobid is not None and grobid.is_available and grobid.bibliography:
            raw_grobid_refs = self._grobid_to_citations(grobid)
            for ref in raw_grobid_refs:
                if _is_fake_entry(ref.raw_text):
                    logger.debug(
                        f"Filtered fake GROBID entry before indexing: {ref.raw_text[:50]}..."
                    )
                    continue

                # Filter out yearless/DOI-less/URL-less GROBID entries extracted from APPENDIX
                if (
                    ref.year is None
                    and not ref.doi
                    and not ref.url
                    and appendix_text_norm
                    and bib_text_norm
                ):
                    probe = (ref.title or ref.venue or ref.raw_text or "").strip().lower()
                    probe_snip = probe[:35] if len(probe) >= 15 else ""
                    if (
                        probe_snip
                        and probe_snip in appendix_text_norm
                        and probe_snip not in bib_text_norm
                    ):
                        logger.debug(
                            f"Filtered APPENDIX GROBID entry before indexing: {ref.raw_text[:50]}..."
                        )
                        continue

                # Coalesce consecutive split GROBID entries where the first half has only
                # authors + year (no title/venue/doi/url) and the second half has no authors
                # but carries the title/venue (e.g. when title contains a year like "Europe PMC in 2020").
                if (
                    grobid_refs
                    and grobid_refs[-1].authors
                    and grobid_refs[-1].title is None
                    and grobid_refs[-1].venue is None
                    and not grobid_refs[-1].doi
                    and not grobid_refs[-1].url
                    and not ref.authors
                    and (ref.title or ref.venue)
                    and (
                        ref.year is None
                        or grobid_refs[-1].year is None
                        or str(ref.year) in (ref.title or "")
                        or str(ref.year) in (ref.venue or "")
                    )
                ):
                    prev_ref = grobid_refs[-1]
                    prev_ref.title = ref.title
                    prev_ref.title_normalized = ref.title_normalized
                    prev_ref.venue = ref.venue
                    prev_ref.doi = prev_ref.doi or ref.doi
                    prev_ref.url = prev_ref.url or ref.url
                    prev_ref.year = prev_ref.year or ref.year
                    parts = [
                        ", ".join(str(a) for a in prev_ref.authors),
                        f"({prev_ref.year})" if prev_ref.year else "",
                        prev_ref.title or "",
                        prev_ref.venue or "",
                    ]
                    prev_ref.raw_text = " ".join(p for p in parts if p).strip()
                    logger.debug(
                        f"Coalesced split GROBID bibliography fragment into: {prev_ref.raw_text[:70]}..."
                    )
                    continue

                grobid_refs.append(ref)
            for idx, ref in enumerate(grobid_refs, start=1):
                ref.order_index = idx
                ref.numeric_index = idx

        # Lấy references từ regex (secondary/supplemental)
        regex_refs = self._extract_references_from_sections(sections)

        # Merge: GROBID primary + regex supplemental
        merged_refs = self._merge_reference_lists(grobid_refs, regex_refs)

        # FIX v1.11: Filter out fake/non-citation entries from merged references
        filtered_refs = []
        for ref in merged_refs:
            if not _is_fake_entry(ref.raw_text):
                filtered_refs.append(ref)
            else:
                logger.debug(f"Filtered fake entry from merged refs: {ref.raw_text[:50]}...")

        if len(filtered_refs) < len(merged_refs):
            logger.info(f"Filtered {len(merged_refs) - len(filtered_refs)} fake entries from merged references")

        return filtered_refs

    def _extract_references_from_sections(
        self,
        sections: list[DocumentSection],
    ) -> list[Citation]:
        """Trích references từ bibliography section bằng regex.

        Used as secondary/supplemental extraction khi GROBID available
        nhưng bỏ sót một số entries.
        """
        from integrity_checker.extraction.reference_parser import (
            _is_essay_title_entry,
            is_vn_legal_reference,
        )

        all_citations: list[Citation] = []
        for section in sections:
            if section.section_type == SectionType.BIBLIOGRAPHY and section.text:
                try:
                    pp = self._citation_extractor.preprocessor
                    section_text = pp._normalize_unicode(pp._fix_ligatures(section.text))

                    entries = self._reference_parser._split_entries(section_text)
                    for idx, entry in enumerate(entries, start=len(all_citations) + 1):
                        if len(entry) < 20 and not is_vn_legal_reference(entry.strip()):
                            continue
                        if _is_essay_title_entry(entry):
                            continue
                        citation = self._reference_parser._parse_entry(
                            entry, order_index=idx, page_num=section.start_page
                        )
                        if citation:
                            # Mark as regex source
                            citation.source = "regex"
                            citation.source_confidence = citation.confidence
                            all_citations.append(citation)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Reference parser failed: %s", exc)
        if all_citations:
            logger.info(f"Extracted {len(all_citations)} references from regex")
        return all_citations

    def _merge_reference_lists(
        self,
        grobid_refs: list[Citation],
        regex_refs: list[Citation],
    ) -> list[Citation]:
        """Merge GROBID và regex references với deduplication.

        Strategy:
            1. GROBID refs primary (structured, reliable)
            2. Regex refs bổ sung entries không trùng
            3. Mark merged entries với provenance

        Args:
            grobid_refs: References từ GROBID (primary)
            regex_refs: References từ regex (secondary)

        Returns:
            list[Citation] merged với deduplication
        """
        from integrity_checker.extraction.grobid_adapter import _is_duplicate_reference

        def _enrich_grobid_ref(target: Citation, donor: Citation) -> None:
            """Fill in missing fields on a GROBID reference from its regex counterpart."""
            donor_first_author = (
                (getattr(donor.authors[0], "raw", None) or str(donor.authors[0]))
                if donor.authors
                else ""
            )
            if not target.authors and donor.authors:
                target.authors = [
                    getattr(a, "raw", None) or str(a) for a in donor.authors
                ]
            elif (
                donor.authors
                and len(donor.authors) == 1
                and "," not in donor_first_author
                and (
                    len(target.authors) > 1
                    or (
                        len(target.authors) == 1
                        and "," in (getattr(target.authors[0], "raw", None) or str(target.authors[0]))
                    )
                )
                and any(
                    kw in donor_first_author.lower()
                    for kw in (
                        "institute", "foundation", "association", "organization",
                        "ministry", "department", "committee", "commission",
                        "council", "society", "team", "center", "centre",
                        "university", "group", "bank", "health", "archive",
                        "library", "corporation", "company", "inc", "ltd",
                        "project", "consortium", "press", "agency", "bureau",
                        "office", "board", "authority", "laboratory", "labs",
                    )
                )
            ):
                old_auth_str = ", ".join(
                    getattr(a, "raw", None) or str(a) for a in target.authors
                )
                target.authors = [donor_first_author]
                if old_auth_str and old_auth_str in (target.raw_text or ""):
                    target.raw_text = (target.raw_text or "").replace(
                        old_auth_str, donor_first_author, 1
                    )

            # Fix bleeding co-author into target.title (e.g. Welling, L., & Thomson, L., [2008]
            # where GROBID sets title=", & Thomson, L" and venue="PHP and MySQL Web Development...")
            if (
                target.title
                and donor.title
                and len(donor.title.strip()) >= 5
                and re.match(r"^[,;\s]*(?:&\s*|and\b)", target.title.strip(), re.IGNORECASE)
            ):
                target.title = donor.title
                target.title_normalized = donor.title_normalized
                if donor.authors:
                    target.authors = [
                        getattr(a, "raw", None) or str(a) for a in donor.authors
                    ]
                if donor.venue:
                    target.venue = donor.venue
                parts = []
                if target.authors:
                    parts.append(", ".join(str(a) for a in target.authors))
                if target.year:
                    parts.append(f"({target.year})")
                if target.title:
                    parts.append(target.title)
                if target.venue:
                    parts.append(target.venue)
                target.raw_text = " ".join(parts)

            # Fix GROBID dropping main title before bracketed section tag (e.g. "Docker [IT infrastructure]"
            # where GROBID sets title="IT infrastructure") or hallucinating Appendix code into title
            if target.title and donor.title and len(donor.title.strip()) >= 5:
                t_clean = target.title.strip()
                d_clean = donor.title.strip()
                if (
                    f"[{t_clean.lower()}]" in d_clean.lower()
                    or re.search(r"',\s*'", t_clean)
                ):
                    old_t = target.title
                    target.title = donor.title
                    target.title_normalized = donor.title_normalized
                    if old_t and old_t in (target.raw_text or ""):
                        target.raw_text = (target.raw_text or "").replace(old_t, donor.title, 1)

            # Fix GROBID concatenating "Title. Venue" into target.title when target.venue is None
            # (e.g. Settles (2012): title="Active learning. Synthesis Lectures on...")
            if (
                not target.venue
                and donor.venue
                and target.title
                and donor.title
                and len(donor.title.strip()) >= 8
            ):
                d_title_clean = donor.title.strip().rstrip(".")
                t_title_clean = target.title.strip()
                if (
                    t_title_clean.lower().startswith(d_title_clean.lower() + ".")
                    and len(t_title_clean) > len(d_title_clean) + 3
                ):
                    target.title = donor.title
                    target.title_normalized = donor.title_normalized

            donor_is_multi_chunk = len(donor.raw_text or "") > max(
                len(target.raw_text or "") * 2.2, 320
            )
            # Restore dropped leading authors when GROBID missed the first author(s) on a page/column break (e.g. 9.pdf [14, 20])
            if (
                donor.authors
                and target.authors
                and len(donor.authors) > len(target.authors)
                and not donor_is_multi_chunk
            ):
                first_d = (getattr(donor.authors[0], "raw", None) or str(donor.authors[0])).strip().rstrip(".").lower()
                t_last = (getattr(target.authors[-1], "last_name", None) or str(target.authors[-1])).split(",")[0].strip().lower()
                d_last = (getattr(donor.authors[-1], "last_name", None) or str(donor.authors[-1])).split(",")[0].strip().lower()
                if t_last and t_last == d_last and first_d not in {"iii", "ii", "iv", "jr", "sr"}:
                    target.authors = [
                        getattr(a, "raw", None) or str(a) for a in donor.authors
                    ]

            if donor.doi and not donor_is_multi_chunk:
                if (
                    not target.doi
                    or target.doi.endswith("-")
                    or (donor.doi.lower().startswith(target.doi.lower()) and len(donor.doi) > len(target.doi))
                ):
                    target.doi = donor.doi
            if not target.url and donor.url and not donor_is_multi_chunk:
                target.url = donor.url
            if not target.venue and donor.venue:
                target.venue = donor.venue
            if not target.year and donor.year:
                target.year = donor.year
            if not target.title and donor.title:
                target.title = donor.title
                target.title_normalized = donor.title_normalized
                if donor.title not in (target.raw_text or ""):
                    target.raw_text = f"{(target.raw_text or '').rstrip('. ')}. {donor.title}"
                    if target.venue and target.venue not in target.raw_text:
                        target.raw_text = f"{target.raw_text.rstrip('. ')}. {target.venue}"
            if donor.numeric_index is not None:
                target.numeric_index = donor.numeric_index
            if donor.style and donor.style.value != "unknown":
                target.style = donor.style
            if donor.matched_pattern and not target.matched_pattern:
                target.matched_pattern = donor.matched_pattern
            if donor.raw_text and re.match(r"^\s*\[\s*\d+\s*\]", donor.raw_text):
                if not re.match(r"^\s*\[\s*\d+\s*\]", target.raw_text or ""):
                    idx_label = donor.numeric_index or target.numeric_index
                    if idx_label is not None:
                        target.raw_text = f"[{idx_label}] {target.raw_text}"
            if donor.raw_text:
                arxiv_m = re.search(
                    r"\barXiv\s*:\s*\d{4}\.\d{4,5}(?:v\d+)?\b",
                    donor.raw_text,
                    re.IGNORECASE,
                )
                if arxiv_m and arxiv_m.group(0).lower() not in (target.raw_text or "").lower():
                    target.raw_text = f"{target.raw_text}. {arxiv_m.group(0)}"
                if target.url and target.url not in (target.raw_text or ""):
                    target.raw_text = f"{target.raw_text}. Retrieved from {target.url}"

        merged: list[Citation] = []

        # Track GROBID ref IDs để avoid duplicate
        grobid_by_doi: dict[str, Citation] = {
            c.doi.lower(): c for c in grobid_refs if c.doi
        }
        grobid_by_key: dict[tuple, Citation] = {}
        grobid_by_num: dict[int, Citation] = {}

        for c in grobid_refs:
            key = self._citation_key(c)
            grobid_by_key[key] = c
            if c.numeric_index is not None and c.numeric_index not in grobid_by_num:
                grobid_by_num[c.numeric_index] = c
            merged.append(c)

        # Add regex entries không trùng với GROBID
        for c in regex_refs:
            key = self._citation_key(c)

            # Check DOI match
            if c.doi and c.doi.lower() in grobid_by_doi:
                _enrich_grobid_ref(grobid_by_doi[c.doi.lower()], c)
                logger.debug(f"Skipping regex duplicate by DOI: {c.raw_text[:50]}")
                continue

            # Check key match
            if key in grobid_by_key:
                _enrich_grobid_ref(grobid_by_key[key], c)
                logger.debug(f"Skipping regex duplicate by key: {c.raw_text[:50]}")
                continue

            # Check GROBID refs directly
            dup_match = next(
                (g for g in grobid_refs if _is_duplicate_reference(c, [g])),
                None,
            )
            if dup_match is not None:
                _enrich_grobid_ref(dup_match, c)
                logger.debug(f"Skipping regex duplicate: {c.raw_text[:50]}")
                continue

            # Check same numeric_index slot (e.g. [10] in GROBID vs [10] in regex
            # when GROBID and regex parsed slightly different title/author boundaries
            # from the exact same numbered bibliography entry)
            if c.numeric_index is not None and c.numeric_index in grobid_by_num:
                g_num = grobid_by_num[c.numeric_index]
                if g_num.year == c.year or (g_num.doi and c.doi and g_num.doi.lower() == c.doi.lower()):
                    _enrich_grobid_ref(g_num, c)
                    logger.debug(
                        f"Skipping regex duplicate at same numeric_index={c.numeric_index}: {c.raw_text[:50]}"
                    )
                    continue

            # Check URL match or title/raw_text substring overlap against GROBID entries (BUG-15)
            c_url_norm = (c.url or "").strip().rstrip("/.,;").lower()
            c_title_norm = re.sub(r"[^\w\s]", " ", (c.title or "").lower())
            c_title_norm = re.sub(r"\s+", " ", c_title_norm).strip()
            overlap_g: Optional[Citation] = None
            for g in grobid_refs:
                g_url_norm = (g.url or "").strip().rstrip("/.,;").lower()
                if c_url_norm and g_url_norm and (c_url_norm == g_url_norm or c_url_norm in g_url_norm or g_url_norm in c_url_norm):
                    overlap_g = g
                    break
                if c.doi and g.doi and (c.doi.lower().startswith(g.doi.lower()) or g.doi.lower().startswith(c.doi.lower())):
                    overlap_g = g
                    break
                g_title_norm = re.sub(r"[^\w\s]", " ", (g.title or "").lower())
                g_title_norm = re.sub(r"\s+", " ", g_title_norm).strip()
                g_raw_norm = re.sub(r"[^\w\s]", " ", (g.raw_text or "").lower())
                g_raw_norm = re.sub(r"\s+", " ", g_raw_norm).strip()
                c_raw_norm = re.sub(r"[^\w\s]", " ", (c.raw_text or "").lower())
                c_raw_norm = re.sub(r"\s+", " ", c_raw_norm).strip()
                if len(c_title_norm) >= 12 and (c_title_norm in g_title_norm or c_title_norm in g_raw_norm):
                    overlap_g = g
                    break
                if len(g_title_norm) >= 12 and (g_title_norm in c_title_norm or g_title_norm in c_raw_norm):
                    overlap_g = g
                    break
            if overlap_g is not None:
                _enrich_grobid_ref(overlap_g, c)
                logger.debug(f"Skipping overlapping regex entry: {c.raw_text[:50]}")
                continue

            # When GROBID has already extracted a substantive bibliography (>= 5 entries),
            # do not append noisy cross-style fallback fragments or unsplit multi-entry chunks.
            if len(grobid_refs) >= 5:
                if (c.matched_pattern or "") in {
                    "harvard_article",
                    "harvard_book",
                    "apa_fallback",
                    "chicago_fallback",
                    "mla_fallback",
                    "vancouver_reference_entry",
                    "nature_book",
                    "acm_fallback",
                    "unquoted_book_entry",
                } or len(c.raw_text or "") > 420:
                    logger.debug(
                        f"Skipping noisy regex fallback ({c.matched_pattern}) when GROBID is present: {c.raw_text[:50]}"
                    )
                    continue

            # Mark as merged source
            c.source = "merged"
            c.source_confidence = c.confidence
            merged.append(c)

        # If all merged references have unique numeric_index values (e.g. when
        # regex filled in a numbered entry [16] that GROBID skipped), sort by
        # numeric_index so the bibliography order matches the paper's [1]..[N].
        if (
            merged
            and all(c.numeric_index is not None for c in merged)
            and len({c.numeric_index for c in merged}) == len(merged)
        ):
            merged.sort(key=lambda c: c.numeric_index or 0)

        # Re-index order_index
        for idx, c in enumerate(merged, start=1):
            c.order_index = idx

        logger.info(
            f"Merged references: {len(grobid_refs)} GROBID + "
            f"{len(regex_refs)} regex → {len(merged)} unique"
        )
        return merged

    @staticmethod
    def _citation_key(c: Citation) -> tuple:
        """Tạo deduplication key từ citation."""
        title_norm = (c.title or "").lower().strip() if c.title else ""
        year = c.year or ""

        # Handle both string authors and Author objects
        first_author = ""
        if c.authors:
            first = c.authors[0]
            if isinstance(first, str):
                first_author = first.split(",")[0].strip().lower()
            elif hasattr(first, "last_name") and first.last_name:
                first_author = first.last_name.lower()
            elif hasattr(first, "full_name") and first.full_name:
                first_author = first.full_name.split(",")[0].strip().lower()

        return (title_norm, year, first_author)

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
        """Convert GrobidOutput.bibliography → Citation[] với provenance tracking.

        Sử dụng grobid_adapter để chuẩn hóa structured extraction,
        với provenance fields cho downstream tracking.
        """
        from integrity_checker.extraction.grobid_adapter import grobid_to_references

        citations = grobid_to_references(grobid)

        # Set provenance fields on each citation (canonical fields from Citation model)
        for c in citations:
            c.source = "grobid"
            c.source_confidence = c.confidence
            # grobid_ref_id is already set by grobid_adapter (canonical field)
            # Check if this ref is linked from in-text citations
            if grobid.is_available and grobid.citations:
                linked_refs = {cit.ref_id for cit in grobid.citations if cit.ref_id}
                c.is_grobid_linked = c.grobid_ref_id in linked_refs if c.grobid_ref_id else False

        return citations
