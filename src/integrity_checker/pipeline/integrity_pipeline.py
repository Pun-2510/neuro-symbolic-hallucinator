"""IntegrityPipeline — end-to-end PDF → AnalysisReport.

Flow:
    PDF → BasePDFParser → CitationExtractor + ReferenceListParser
        → RetrievalOrchestrator (per citation)
        → NeuroSymbolicChecker
        → CISCalculator
        → AnalysisReport

CLI entry-point: `python -m integrity_checker.pipeline.integrity_pipeline`
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
    MuPdfParser,
    PdfPlumberParser,
    ReferenceListParser,
)
from integrity_checker.extraction.base import BasePDFParser, Document, chain_parsers
from integrity_checker.logging import configure_logging, get_logger
from integrity_checker.logic.cis import CISCalculator
from integrity_checker.logic.explanation import ExplanationGenerator
from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
from integrity_checker.models.citation import Citation
from integrity_checker.models.validation import (
    CitationIntegrityScore,
    CitationVerdict,
)
from integrity_checker.retrieval import RetrievalOrchestrator

logger = get_logger(__name__)


@dataclass
class AnalysisReport:
    """Đầu ra cuối cùng của pipeline."""

    essay_id: int = 0
    filename: str = ""
    num_pages: int = 0
    num_citations: int = 0
    verdicts: list[CitationVerdict] = field(default_factory=list)
    cis: CitationIntegrityScore | None = None
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
                    "suggestions": ExplanationGenerator.suggestions(v),
                }
                for v in self.verdicts
            ],
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

    # TODO(user): tuần 7–8 — thêm:
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
    ) -> None:
        self.parser = parser or self._build_default_parser()
        self.extractor = extractor or CitationExtractor()
        self.ref_parser = ref_parser or ReferenceListParser(self.extractor)
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.checker = checker or NeuroSymbolicChecker()
        self.cis_calc = cis_calc or CISCalculator()

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
        """Full pipeline async."""
        logger.info(f"Pipeline start: {pdf_path}")
        # 1. Parse PDF
        doc = self.parser.parse(pdf_path)
        logger.info(f"Parsed: {doc.num_pages} pages via {doc.parser_used}")

        # 2. Extract citations
        in_text = self.extractor.extract_from_document(doc)
        ref_list = self.ref_parser.parse_reference_section(doc)
        all_citations = self._merge_citations(in_text, ref_list)
        logger.info(f"Extracted: {len(in_text)} in-text + {len(ref_list)} ref-list = {len(all_citations)}")

        # 3. Retrieve + check từng citation
        verdicts: list[CitationVerdict] = []
        for citation in all_citations:
            source = await self.orchestrator.retrieve(citation)
            verdict = self.checker.check(citation, source)
            verdicts.append(verdict)
            logger.debug(
                f"  [{verdict.label.value}] conf={verdict.confidence:.2f} "
                f"raw={citation.raw_text[:60]}"
            )

        # 4. CIS
        cis = self.cis_calc.compute(verdicts)

        # 5. Build report
        report = AnalysisReport(
            essay_id=essay_id,
            filename=Path(pdf_path).name,
            num_pages=doc.num_pages,
            num_citations=len(all_citations),
            verdicts=verdicts,
            cis=cis,
            disclaimer=get_settings().disclaimer.long,
            generated_at=datetime.utcnow().isoformat() + "Z",
        )
        logger.info(
            f"Pipeline done: {report.num_citations} citations, CIS={cis.score:.1f}/100"
        )
        return report

    @staticmethod
    def _merge_citations(
        in_text: list[Citation], ref_list: list[Citation]
    ) -> list[Citation]:
        """Gộp + dedupe theo (style, normalized raw). Reference list ưu tiên (có title)."""
        seen: set[tuple[str, str]] = set()
        merged: list[Citation] = []
        # Ưu tiên reference list trước
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
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        logger.error(f"File không tồn tại: {pdf_path}")
        raise SystemExit(1)

    pipeline = IntegrityPipeline()
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