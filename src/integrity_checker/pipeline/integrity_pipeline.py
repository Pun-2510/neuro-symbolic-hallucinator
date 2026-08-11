"""IntegrityPipeline — end-to-end PDF → AnalysisReport.

Flow v1.2 (tuần 8, task #25):
    PDF → DocumentParser (PyMuPDF + GROBID + SectionSegmenter)
        → ParsedDocument (body_citations + references + appendix_citations)
        → RetrievalOrchestrator (per citation)
        → NeuroSymbolicChecker
        → CISCalculator
        → AnalysisReport

Backward compatible:
    Nếu DocumentParser disabled, fallback to legacy flow:
        PDF → BasePDFParser → CitationExtractor + ReferenceListParser
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from integrity_checker.config import get_settings
from integrity_checker.extraction import (
    CitationExtractor,
    DocumentParser,
    MuPdfParser,
    PdfPlumberParser,
    ReferenceListParser,
)
from integrity_checker.extraction.base import BasePDFParser, Document, chain_parsers
from integrity_checker.extraction.document_parser import ParsedDocument
from integrity_checker.linking.citation_linker import CitationLinker
from integrity_checker.linking.statuses import (
    CitationLink,
    CitationMappingStatus,
    CitationOccurrence,
    LinkingResult,
    ReferenceEntry,
    StyleProfile,
)
from integrity_checker.logging import configure_logging, get_logger
from integrity_checker.logic.cis import CISCalculator
from integrity_checker.logic.explanation import ExplanationGenerator
from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
from integrity_checker.models.citation import Citation, CitationType
from integrity_checker.models.validation import (
    CitationIntegrityScore,
    CitationVerdict,
)
from integrity_checker.retrieval import RetrievalOrchestrator

logger = get_logger(__name__)


@dataclass
class AnalysisReport:
    """Đầu ra cuối cùng của pipeline.

    v1.2 §3.2.2 — output schema TÁCH 2 lớp:
        - ``verdicts[].label`` (ValidationLabel) — source verification.
        - ``verdicts[].mapping_status`` (CitationMappingStatus) — in-text ↔ reference
          integrity.
        - ``linking_summary`` — counts per CitationMappingStatus (cho Web UI dashboard).
    """

    essay_id: int = 0
    filename: str = ""
    num_pages: int = 0
    num_citations: int = 0
    verdicts: list[CitationVerdict] = field(default_factory=list)
    cis: CitationIntegrityScore | None = None
    linking_summary: dict[str, int] = field(default_factory=dict)  # NEW v1.2 — mapping counts
    style_profile: dict[str, Any] | None = None  # NEW v1.2 — style profile summary
    disclaimer: str = ""
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize sang JSON-friendly dict."""
        return {
            "essay_id": self.essay_id,
            "filename": self.filename,
            "num_pages": self.num_pages,
            "num_citations": self.num_citations,
            "verdicts": [
                {
                    # Lớp 1: source verification (nhãn 4 chiều)
                    "citation_raw": v.citation.raw_text,
                    "label": v.label.value,
                    "confidence": v.confidence,
                    # Lớp 2: integrity mapping (7 trạng thái v1.2 §3.2.2)
                    "mapping_status": (
                        v.mapping_status.value
                        if v.mapping_status is not None
                        else None
                    ),
                    "mapping_confidence": v.mapping_confidence,
                    "citation_link": (
                        _serialize_citation_link(v.citation_link)
                        if v.citation_link is not None
                        else None
                    ),
                    # Bằng chứng
                    "reasoning": v.reasoning,
                    "triggered_rules": v.triggered_rules,
                    "mismatched_fields": v.mismatched_fields,
                    "features": {
                        "title_sim_fuzzy": v.features.title_sim_fuzzy,
                        "title_sim_semantic": v.features.title_sim_semantic,
                        "author_jaccard": v.features.author_jaccard,
                        "year_distance": v.features.year_distance,
                        "doi_exact_match": v.features.doi_exact_match,
                        "source_consensus": v.features.source_consensus,
                    },
                    "suggestions": ExplanationGenerator.suggestions(v),
                }
                for v in self.verdicts
            ],
            "linking_summary": self.linking_summary,
            "style_profile": self.style_profile,
            "cis": (
                {
                    "score": self.cis.score,
                    "components": self.cis.components.to_dict(),
                    "weights_used": self.cis.weights_used,
                    "num_citations": self.cis.num_citations,
                    "num_unresolved": self.cis.num_unresolved,
                }
                if self.cis
                else None
            ),
            "disclaimer": self.disclaimer,
            "generated_at": self.generated_at,
        }


class IntegrityPipeline:
    """End-to-end pipeline: PDF → AnalysisReport.

    v1.2 (tuần 8) — sử dụng DocumentParser làm entry point chính (PyMuPDF +
    GROBID + SectionSegmenter). Fallback về legacy flow nếu DocumentParser
    disabled qua config.

    # TODO(user): tuần 9 — thêm:
        - Batch processing nhiều PDF cùng lúc
        - Persistent cache của verdicts (key = SHA256 của citation + PDF content)
    """

    def __init__(
        self,
        parser: BasePDFParser | None = None,
        extractor: CitationExtractor | None = None,
        ref_parser: ReferenceListParser | None = None,
        orchestrator: RetrievalOrchestrator | None = None,
        checker: NeuroSymbolicChecker | None = None,
        cis_calc: CISCalculator | None = None,
        document_parser: DocumentParser | None = None,
        use_document_parser: bool | None = None,
        linker: CitationLinker | None = None,
    ) -> None:
        # Legacy components (fallback path)
        self.parser = parser or self._build_default_parser()
        self.extractor = extractor or CitationExtractor()
        self.ref_parser = ref_parser or ReferenceListParser(self.extractor)
        # Modern path — DocumentParser (PyMuPDF + GROBID + SectionSegmenter)
        self.document_parser = document_parser or DocumentParser()
        # Auto-detect: dùng DocumentParser nếu enabled trong config
        # Default False để backward compat với legacy pipeline tests;
        # User phải explicit opt-in qua constructor hoặc CLI flag.
        self._use_document_parser: bool = (
            use_document_parser
            if use_document_parser is not None
            else False
        )
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.checker = checker or NeuroSymbolicChecker()
        self.cis_calc = cis_calc or CISCalculator()
        # NEW v1.2 §3.2.2 — CitationLinker cho in-text ↔ reference integrity
        self.linker = linker or CitationLinker()

    def _build_default_parser(self) -> BasePDFParser:
        """Theo config: mupdf | pdfplumber | hybrid (mupdf → pdfplumber fallback)."""
        mode = get_settings().extraction.parser
        if mode == "mupdf":
            return MuPdfParser()
        if mode == "pdfplumber":
            return PdfPlumberParser()
        return chain_parsers([MuPdfParser(), PdfPlumberParser()])

    # -- sync entry (CLI / tests) --

    def run(self, pdf_path: str, essay_id: int = 0) -> AnalysisReport:
        """Sync wrapper quanh async run_async."""
        return asyncio.run(self.run_async(pdf_path, essay_id=essay_id))

    # -- async entry (FastAPI) --

    async def run_async(self, pdf_path: str, essay_id: int = 0) -> AnalysisReport:
        """Full pipeline async.

        Flow v1.2:
            1. DocumentParser.parse(pdf_path) → ParsedDocument
               (PyMuPDF + GROBID + SectionSegmenter fused)
            2. body_citations + references + appendix_citations
            3. _merge_citations(...) — ưu tiên references (có title + DOI)
            4. Per-citation: RetrievalOrchestrator.retrieve() → SourceResult
            5. NeuroSymbolicChecker.check() → CitationVerdict
            6. CISCalculator.compute(verdicts) → CitationIntegrityScore
            7. AnalysisReport
        """
        logger.info(f"Pipeline start: {pdf_path}")

        # 1. Parse PDF
        num_pages = 0
        in_text_citations: list[Citation] = []
        ref_citations: list[Citation] = []
        appendix_citations: list[Citation] = []
        parser_warnings: list[str] = []
        style_profile_dict: dict[str, Any] | None = None
        if self._use_document_parser:
            # Modern path: DocumentParser (PyMuPDF + GROBID + SectionSegmenter)
            parsed = self.document_parser.parse(pdf_path)
            num_pages = len(parsed.sections)
            in_text_citations = parsed.body_citations
            ref_citations = parsed.references
            appendix_citations = parsed.appendix_citations
            parser_warnings = parsed.parser_warnings
            logger.info(
                f"DocumentParser: {len(parsed.body_citations)} body + "
                f"{len(parsed.references)} ref + "
                f"{len(parsed.appendix_citations)} appendix citations"
                + (f" (warnings: {parser_warnings})" if parser_warnings else "")
            )
        else:
            # Legacy fallback path
            doc = self.parser.parse(pdf_path)
            num_pages = doc.num_pages
            in_text_citations = self.extractor.extract_from_document(doc)
            ref_citations = self.ref_parser.parse_reference_section(doc)
            logger.info(
                f"Legacy parse: {doc.num_pages} pages via {doc.parser_used}, "
                f"{len(in_text_citations)} in-text + {len(ref_citations)} ref-list"
            )

        # 1b. Style profile detection (v1.2 — dùng cho linker + CIS format_consistency)
        style_profile = self._detect_style(in_text_citations, ref_citations)
        style_profile_dict = self._serialize_style_profile(style_profile)

        # 1c. Citation linking (in-text ↔ reference) — v1.2 §3.5
        linking_result = self._run_linking(in_text_citations, ref_citations, style_profile)
        link_by_raw_text = self._build_link_lookup(linking_result.links)

        # 1d. Merge citations theo priority (cho retrieval/checker).
        # Appendix chỉ dùng cho linking thống kê, không retrieval.
        all_citations = self._merge_citations(
            in_text_citations, ref_citations, []
        )

        # 2. Retrieve + check từng citation
        verdicts: list[CitationVerdict] = []
        for citation in all_citations:
            source = await self.orchestrator.retrieve(citation)
            # NEW v1.2 §3.2.2 (task #33) — compute mapping_status TRƯỚC rules
            # để SymbolicRules có input cho AMBIGUOUS_MAPPING rule.
            link = link_by_raw_text.get(citation.raw_text.lower().strip())
            if link is not None:
                mapping_status = link.status
                mapping_confidence = link.confidence
                citation_link = link
            else:
                # Không tìm thấy link — mặc định MISSING_REFERENCE nếu ref_list rỗng,
                # nếu không thì AMBIGUOUS_MAPPING.
                if not ref_citations:
                    mapping_status = CitationMappingStatus.MISSING_REFERENCE
                    mapping_confidence = 0.0
                    citation_link = None
                else:
                    mapping_status = CitationMappingStatus.AMBIGUOUS_MAPPING
                    mapping_confidence = 0.0
                    citation_link = None
            # Pass mapping_status + style_profile vào checker
            verdict = self.checker.check(
                citation,
                source,
                mapping_status=mapping_status,
                style_profile=style_profile,
            )
            verdict.mapping_status = mapping_status
            verdict.mapping_confidence = mapping_confidence
            verdict.citation_link = citation_link
            verdicts.append(verdict)
            logger.debug(
                f"  [{verdict.label.value}] conf={verdict.confidence:.2f} "
                f"mapping={verdict.mapping_status.value if verdict.mapping_status else 'NONE'} "
                f"raw={citation.raw_text[:60]}"
            )

        # 3. Linking summary (counts per CitationMappingStatus) — cho Web UI dashboard
        linking_summary = self._build_linking_summary(verdicts)

        # 4. CIS
        cis = self.cis_calc.compute(
            verdicts,
            linking_result=linking_result,
            style_profile=style_profile,
        )

        # 5. Build report
        report = AnalysisReport(
            essay_id=essay_id,
            filename=Path(pdf_path).name,
            num_pages=num_pages,
            num_citations=len(all_citations),
            verdicts=verdicts,
            cis=cis,
            linking_summary=linking_summary,
            style_profile=style_profile_dict,
            disclaimer=get_settings().disclaimer.long,
            generated_at=datetime.now().isoformat() + "Z",  # fixed: utcnow deprecated
        )
        logger.info(
            f"Pipeline done: {report.num_citations} citations, CIS={cis.score:.1f}/100"
        )
        return report

    @staticmethod
    def _merge_citations(
        body: list[Citation],
        references: list[Citation],
        appendix: list[Citation],
    ) -> list[Citation]:
        """Gộp + dedupe theo (style, normalized raw). Reference list ưu tiên (có title).

        Flow v1.2:
            1. References trước (chứa title + DOI — đầy đủ nhất)
            2. body_citations (in-text — thiếu title)
            3. appendix_citations last (out-of-scope nhưng vẫn kiểm tra)
        """
        seen: set[tuple[str, str]] = set()
        merged: list[Citation] = []
        for source_list in (references, body, appendix):
            for c in source_list:
                key = (c.style.value, c.raw_text.lower().strip())
                if key not in seen:
                    seen.add(key)
                    merged.append(c)
        return merged

    @staticmethod
    def _merge_citations_legacy(
        in_text: list[Citation], ref_list: list[Citation]
    ) -> list[Citation]:
        """Legacy merge (backward compat cho fallback path)."""
        seen: set[tuple[str, str]] = set()
        merged: list[Citation] = []
        for c in ref_list:
            key = (c.style.value, c.raw_text.lower().strip())
            if key not in seen:
                seen.add(key)
                merged.append(c)
        for c in in_text:
            key = (c.style.value, c.raw_text.lower().strip())
            if key not in seen:
                seen.add(key)
                merged.append(c)
        return merged

    # --- v1.2 §3.5 helpers (linking + style) ---

    def _detect_style(
        self,
        in_text: list[Citation],
        references: list[Citation],
    ) -> StyleProfile:
        """Detect document-level style từ in-text + reference citations.

        Convert từ extraction.StyleProfile → linking.StyleProfile.
        extraction schema: ``label`` ('APA-like' / 'IEEE-like' / 'MIXED' / 'UNKNOWN')
        + ``ratios`` dict + ``features`` StyleFeatures.
        linking schema: ``style`` + ``apa_count`` + ``numeric_count`` + ``evidence``.

        Nếu StyleDetector raise → fallback APA-LIKE.
        """
        try:
            from integrity_checker.extraction.style_detector import StyleDetector

            detector = StyleDetector()
            ext_profile = detector.detect(in_text, references)
            # Map label (e.g. 'APA-like') → linking style 'APA-LIKE'
            style_value = (ext_profile.label or "UNKNOWN").upper()
            ratios = ext_profile.ratios or {}
            return StyleProfile(
                style=style_value,
                confidence=ext_profile.confidence,
                apa_count=ratios.get("apa_count", 0) + ratios.get("APA_count", 0),
                numeric_count=ratios.get("ieee_count", 0) + ratios.get("IEEE_count", 0),
                evidence={"ratios": dict(ratios), "explanation": ext_profile.explanation},
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Style detection failed: {e}; fallback APA-LIKE")
            return StyleProfile(
                style="APA-LIKE",
                confidence=0.0,
                apa_count=0,
                numeric_count=0,
                evidence={"error": str(e)},
            )

    @staticmethod
    def _serialize_style_profile(profile: StyleProfile) -> dict[str, Any]:
        """linking.StyleProfile → JSON-friendly dict."""
        return {
            "style": profile.style,
            "confidence": profile.confidence,
            "apa_count": profile.apa_count,
            "numeric_count": profile.numeric_count,
            "evidence": dict(profile.evidence) if profile.evidence else {},
        }

    def _run_linking(
        self,
        in_text: list[Citation],
        references: list[Citation],
        style_profile: StyleProfile,
    ) -> LinkingResult:
        """Chạy CitationLinker.link() với Citation[].

        Wraps in-text citations và references để populate occurrence_id/reference_id,
        sau đó gọi CitationLinker.link(body_citations, bib_citations).

        Returns:
            LinkingResult với links, unmatched_reference_ids, status_counts.
        """
        # Populate occurrence_id/reference_id trên citations
        body_with_ids: list[Citation] = []
        for idx, c in enumerate(in_text):
            c.reference_id = f"occ-{idx + 1:04d}"
            body_with_ids.append(c)

        bib_with_ids: list[Citation] = []
        for idx, c in enumerate(references):
            c.reference_id = f"ref-{idx + 1:04d}"
            bib_with_ids.append(c)

        return self.linker.link(body_with_ids, bib_with_ids)

    @staticmethod
    def _build_link_lookup(
        links: list[CitationLink],
    ) -> dict[str, CitationLink]:
        """Map raw_text → CitationLink cho O(1) lookup từ verdict.

        CitationLinker sets evidence['raw'] (not 'raw_text') to the original
        raw_text. Match by lowercased + stripped form.
        """
        lookup: dict[str, CitationLink] = {}
        for link in links:
            evidence = link.evidence or {}
            raw = evidence.get("raw", "") or evidence.get("raw_text", "")
            if raw:
                lookup[raw.lower().strip()] = link
            else:
                # Fallback: use occurrence_id as key
                lookup[link.occurrence_id] = link
        return lookup

    @staticmethod
    def _build_linking_summary(verdicts: list[CitationVerdict]) -> dict[str, int]:
        """Đếm số verdict theo CitationMappingStatus.

        Trả về dict[str, int] cho Web UI dashboard. Bao gồm tất cả 7 status
        (giá trị 0 nếu không có).
        """
        counts: dict[str, int] = {s.value: 0 for s in CitationMappingStatus}
        for v in verdicts:
            if v.mapping_status is not None:
                status_value = (
                    v.mapping_status.value
                    if hasattr(v.mapping_status, "value")
                    else str(v.mapping_status)
                )
                counts[status_value] = counts.get(status_value, 0) + 1
        return counts


# ============================================================
# CLI entry-point
# ============================================================


def _serialize_verdict_for_json(v: CitationVerdict) -> dict[str, Any]:
    """CitationVerdict không JSON-serializable do Citation dataclass nested."""
    return {
        "citation_raw": v.citation.raw_text,
        "label": v.label.value,
        "confidence": v.confidence,
        "reasoning": v.reasoning,
        "triggered_rules": v.triggered_rules,
        "mismatched_fields": v.mismatched_fields,
        "features": {
            "title_sim_fuzzy": v.features.title_sim_fuzzy,
            "title_sim_semantic": v.features.title_sim_semantic,
            "author_jaccard": v.features.author_jaccard,
            "year_distance": v.features.year_distance,
            "doi_exact_match": v.features.doi_exact_match,
            "source_consensus": v.features.source_consensus,
        },
    }


def _serialize_citation_link(link: Any) -> dict[str, Any]:
    """CitationLink → JSON-friendly dict.

    Handles enum values, dict evidence, optional fields.
    """
    if link is None:
        return {}
    status = link.status
    method = link.method
    return {
        "occurrence_id": link.occurrence_id,
        "reference_id": link.reference_id,
        "status": status.value if hasattr(status, "value") else str(status),
        "confidence": link.confidence,
        "method": method.value if hasattr(method, "value") else str(method),
        "evidence": dict(link.evidence) if link.evidence else {},
        "page": link.page,
        "section": link.section,
    }


def main() -> None:
    """CLI: python -m integrity_checker.pipeline.integrity_pipeline FILE [--output FILE]"""
    configure_logging()

    parser = argparse.ArgumentParser(
        description="Essay Integrity Checker — run pipeline trên 1 PDF tiểu luận"
    )
    parser.add_argument("pdf", help="Đường dẫn tới PDF essay")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Ghi report JSON ra file (mặc định: in ra stdout)",
    )
    parser.add_argument("--essay-id", type=int, default=0)
    parser.add_argument(
        "--no-document-parser",
        action="store_true",
        help="Dùng legacy flow (PyMuPDF + regex) thay vì DocumentParser",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error(f"File không tồn tại: {pdf_path}")
        raise SystemExit(1)

    pipeline = IntegrityPipeline(
        use_document_parser=not args.no_document_parser
    )
    report = pipeline.run(str(pdf_path), essay_id=args.essay_id)

    # In summary
    print("\n" + "=" * 70)
    print(f" ESSAY: {report.filename}")
    print(f" Pages: {report.num_pages}  |  Citations: {report.num_citations}")
    if report.cis:
        print(
            f" CIS (Citation Integrity Score): {report.cis.score:.1f}/100  "
            f"(unresolved: {report.cis.num_unresolved})"
        )
    print("=" * 70)
    print("\n Verdicts:")
    for i, v in enumerate(report.verdicts, 1):
        marker = {
            "verified": "✓",
            "metadata_error": "△",
            "suspected_hallucination": "✗",
            "unresolved": "?",
        }[v.label.value]
        print(
            f"  {marker} [{v.label.value:25s}] conf={v.confidence:.0%}  "
            f"raw={v.citation.raw_text[:80]}"
        )
    print("\n ⚠ " + report.disclaimer)
    print()

    # Ghi file JSON nếu có --output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Wrote report → {out_path}")


if __name__ == "__main__":
    main()