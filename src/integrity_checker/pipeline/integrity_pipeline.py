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
import hashlib
import inspect
import json
import re
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
from integrity_checker.extraction.base import BasePDFParser, Document, Page, chain_parsers
from integrity_checker.extraction.document_parser import ParsedDocument
from integrity_checker.linking.citation_linker import CitationLinker
from integrity_checker.linking.duplicate_detector import DuplicateDetector
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
from integrity_checker.models.citation import Citation, CitationStyle, CitationType
from integrity_checker.models.validation import (
    CISComponents,
    CitationIntegrityScore,
    CitationVerdict,
    MatchFeatures,
    ValidationLabel,
)
from integrity_checker.retrieval import RetrievalOrchestrator
from integrity_checker.retrieval.normalization import citation_key

logger = get_logger(__name__)

# Regex for normalizing "et al." citation formats for link lookup
# Matches: "(Vaswani et al., 2017)", "(Vaswani et al. (2017))", "Vaswani et al. (2017)"
_ET_AL_NORM_RE = re.compile(
    r"\(?([A-Za-zÀ-ÿ'.\s-]+?)(?:\s+et\s+al\.?)?[,\s]+\(?\s*((?:19|20)\d{2})",
    re.IGNORECASE,
)


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
    cache_hit: bool = False

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
                    "citation": _serialize_citation(v.citation),
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
                        "title_sim_fuzzy": v.features.title_sim_fuzzy if v.features else None,
                        "title_sim_semantic": v.features.title_sim_semantic if v.features else None,
                        "author_jaccard": v.features.author_jaccard if v.features else None,
                        "year_distance": v.features.year_distance if v.features else None,
                        "doi_exact_match": v.features.doi_exact_match if v.features else None,
                        "source_consensus": v.features.source_consensus if v.features else None,
                    },
                    # NEW v1.3: Provenance tracking
                    "provenance": {
                        "sources_succeeded": v.sources_succeeded,
                        "sources_failed": dict(v.sources_failed),
                        "api_exhausted": v.api_exhausted,
                        "used_local_db": v.used_local_db,
                    },
                    "warnings": _get_verdict_warnings_from_verdict(v),
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
            "cache_hit": self.cache_hit,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnalysisReport":
        """Rehydrate a report from the persistent JSON report cache."""
        verdicts: list[CitationVerdict] = []
        for raw_verdict in payload.get("verdicts", []):
            citation_data = raw_verdict.get("citation") or {
                "raw_text": raw_verdict.get("citation_raw", ""),
            }
            citation = _deserialize_citation(citation_data)
            feature_data = raw_verdict.get("features") or {}
            features = _match_features_from_dict(feature_data)

            mapping_status = raw_verdict.get("mapping_status")
            if mapping_status:
                mapping_status = CitationMappingStatus(mapping_status)
            citation_link = _deserialize_citation_link(raw_verdict.get("citation_link"))

            verdict = CitationVerdict(
                citation=citation,
                label=ValidationLabel(raw_verdict.get("label", "unresolved")),
                confidence=float(raw_verdict.get("confidence", 0.0)),
                mapping_status=mapping_status,
                mapping_confidence=float(raw_verdict.get("mapping_confidence", 0.0)),
                citation_link=citation_link,
                features=features,
                reasoning=raw_verdict.get("reasoning", ""),
                triggered_rules=list(raw_verdict.get("triggered_rules", [])),
                mismatched_fields=list(raw_verdict.get("mismatched_fields", [])),
                is_overridden=bool(raw_verdict.get("is_overridden", False)),
                sources_succeeded=list(
                    (raw_verdict.get("provenance") or {}).get("sources_succeeded", [])
                ),
                sources_failed=dict(
                    (raw_verdict.get("provenance") or {}).get("sources_failed", {})
                ),
                api_exhausted=bool(
                    (raw_verdict.get("provenance") or {}).get("api_exhausted", False)
                ),
                used_local_db=bool(
                    (raw_verdict.get("provenance") or {}).get("used_local_db", False)
                ),
            )
            verdicts.append(verdict)

        cis_payload = payload.get("cis")
        cis = None
        if cis_payload:
            components = cis_payload.get("components") or {}
            cis = CitationIntegrityScore(
                score=float(cis_payload.get("score", 0.0)),
                components=CISComponents(
                    verified_ratio=float(components.get("verified_ratio", 0.0)),
                    metadata_accuracy=float(components.get("metadata_accuracy", 0.0)),
                    in_text_bib_consistency=float(
                        components.get("in_text_bib_consistency", 0.0)
                    ),
                    format_consistency=float(components.get("format_consistency", 0.0)),
                    identifier_validity=float(components.get("identifier_validity", 0.0)),
                ),
                weights_used=dict(cis_payload.get("weights_used") or {}),
                num_citations=int(cis_payload.get("num_citations", 0)),
                num_unresolved=int(cis_payload.get("num_unresolved", 0)),
            )

        return cls(
            essay_id=int(payload.get("essay_id", 0)),
            filename=payload.get("filename", ""),
            num_pages=int(payload.get("num_pages", 0)),
            num_citations=int(payload.get("num_citations", len(verdicts))),
            verdicts=verdicts,
            cis=cis,
            linking_summary=dict(payload.get("linking_summary") or {}),
            style_profile=payload.get("style_profile"),
            disclaimer=payload.get("disclaimer", ""),
            generated_at=payload.get("generated_at", ""),
            cache_hit=True,
        )


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
        use_report_cache: bool | None = None,
    ) -> None:
        # Legacy components (fallback path)
        self.parser = parser or self._build_default_parser()
        self.extractor = extractor or CitationExtractor()
        self.ref_parser = ref_parser or ReferenceListParser(self.extractor)
        # Modern path — DocumentParser (PyMuPDF + GROBID + SectionSegmenter)
        self.document_parser = document_parser or DocumentParser()
        # Use DocumentParser by default in v1.2+ (fix 2026-09-20)
        self._use_document_parser: bool = (
            use_document_parser
            if use_document_parser is not None
            else True
        )
        self._document_parser_explicit = use_document_parser is not None
        self.orchestrator = orchestrator or RetrievalOrchestrator()
        self.checker = checker or NeuroSymbolicChecker()
        self.cis_calc = cis_calc or CISCalculator()
        # NEW v1.2 §3.2.2 — CitationLinker cho in-text ↔ reference integrity
        self.linker = linker or CitationLinker()
        settings = get_settings()
        self._use_report_cache = (
            use_report_cache
            if use_report_cache is not None
            else (
                settings.app.env.casefold() not in {"test", "testing"}
                and orchestrator is None
                and checker is None
            )
        )
        self._report_cache_dir = settings.paths.cache_dir / "reports"

    def _build_default_parser(self) -> BasePDFParser:
        """Theo config: mupdf | pdfplumber | hybrid (mupdf → pdfplumber fallback)."""
        mode = get_settings().extraction.parser
        if mode == "mupdf":
            return MuPdfParser()
        if mode == "pdfplumber":
            return PdfPlumberParser()
        return chain_parsers([MuPdfParser(), PdfPlumberParser()])

    @staticmethod
    def _pdf_sha256(pdf_path: str) -> str | None:
        """Compute a stable content hash without loading the whole PDF."""
        path = Path(pdf_path)
        if not path.is_file():
            return None
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError:
            return None
        return digest.hexdigest()

    def _report_cache_key(self, pdf_path: str) -> str | None:
        digest = self._pdf_sha256(pdf_path)
        return f"report-v3-{digest}" if digest else None

    def _report_cache_path(self, cache_key: str) -> Path:
        return self._report_cache_dir / f"{cache_key}.json"

    def _load_report_cache(self, cache_key: str) -> AnalysisReport | None:
        path = self._report_cache_path(cache_key)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return AnalysisReport.from_dict(payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            logger.warning(f"Invalid report cache {path}: {exc}; recomputing")
            return None

    def _save_report_cache(self, cache_key: str, report: AnalysisReport) -> None:
        path = self._report_cache_path(cache_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(".tmp")
            temp_path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(path)
        except OSError as exc:
            logger.warning(f"Could not write report cache {path}: {exc}")

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

        if (
            not Path(pdf_path).is_file()
            and self._use_document_parser
            and not self._document_parser_explicit
        ):
            # Preserve the legacy sync API contract for callers that did not
            # explicitly opt into DocumentParser's graceful empty-report mode.
            raise FileNotFoundError(pdf_path)

        cache_key = self._report_cache_key(pdf_path)
        if cache_key and self._use_report_cache:
            cached_report = self._load_report_cache(cache_key)
            if cached_report is not None:
                cached_report.essay_id = essay_id
                cached_report.filename = Path(pdf_path).name
                logger.info(
                    f"Report cache HIT: {Path(pdf_path).name} "
                    f"(sha256={cache_key.removeprefix('report-v3-')[:12]}...)"
                )
                return cached_report

        # 1. Parse PDF
        num_pages = 0
        in_text_citations: list[Citation] = []
        ref_citations: list[Citation] = []
        appendix_citations: list[Citation] = []
        parser_warnings: list[str] = []
        style_profile_dict: dict[str, Any] | None = None
        document_pages: list[Page] = []  # Store pages for context extraction

        if self._use_document_parser:
            # Modern path: DocumentParser (PyMuPDF + GROBID + SectionSegmenter)
            parsed = self.document_parser.parse(pdf_path)
            num_pages = parsed.document.num_pages  # FIX: lấy num_pages từ document gốc
            in_text_citations = parsed.body_citations
            ref_citations = parsed.references
            appendix_citations = parsed.appendix_citations
            parser_warnings = parsed.parser_warnings
            document_pages = parsed.document.pages  # Store for context extraction
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
            document_pages = doc.pages  # Store for context extraction
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

        # 1d. Populate metadata for in-text citations from matched references
        # FIX: For numeric citations like "[1]" that have no title/author/year,
        # copy metadata from the matched reference entry
        self._populate_citation_metadata(in_text_citations, ref_citations, link_by_raw_text)

        # 1e. Merge citations theo priority (cho retrieval/checker).
        # Appendix chỉ dùng cho linking thống kê, không retrieval.
        all_citations = self._merge_citations(
            in_text_citations, ref_citations, []
        )

        # 2. Retrieve + check từng citation (PARALLEL cho tốc độ).  Keep one
        # verdict per extracted citation, but retrieve one canonical paper
        # only once when a bibliography entry and in-text occurrence refer to
        # the same paper.
        unique_citations: dict[str, Citation] = {}
        citation_keys: list[str] = []
        for citation in all_citations:
            key = citation_key(citation)
            citation_keys.append(key)
            unique_citations.setdefault(key, citation)

        unique_sources = await asyncio.gather(
            *(self.orchestrator.retrieve(c) for c in unique_citations.values()),
            return_exceptions=False,
        )
        source_by_key = dict(zip(unique_citations, unique_sources))
        sources = [source_by_key[key] for key in citation_keys]
        if len(unique_citations) != len(all_citations):
            logger.info(
                f"Retrieval dedupe: {len(all_citations)} citations -> "
                f"{len(unique_citations)} unique paper keys"
            )

        verdicts: list[CitationVerdict] = []
        for citation, source in zip(all_citations, sources):
            # NEW v1.2 §3.2.2 (task #33) — compute mapping_status TRƯỚC rules
            # để SymbolicRules có input cho AMBIGUOUS_MAPPING rule.
            # Reference list entries are the reference entries themselves — they're "matched" by definition
            if citation.citation_type.value == "reference_list":
                mapping_status = CitationMappingStatus.MATCHED
                mapping_confidence = 0.95
                citation_link = None
            else:
                # Normalize the raw_text to handle newlines/whitespace variations
                normalized_text = citation.raw_text.replace("\n", " ").replace("  ", " ")
                # Try lookup with normalized text
                normalized_key = IntegrityPipeline._normalize_identifier(normalized_text)
                link = link_by_raw_text.get(normalized_key)
                if link is None:
                    link = link_by_raw_text.get(normalized_text.lower().strip())
                # Special case: author-year style without parens vs with parens
                # e.g., "Vaswani et al. (2017)" vs "(Vaswani et al., 2017)"
                if link is None and "et al." in normalized_text:
                    # Try adding parens if missing
                    if not normalized_text.strip().startswith("("):
                        with_parens = f"({normalized_text.strip().rstrip('.')})"
                        link = link_by_raw_text.get(with_parens.lower())
                        if link is None:
                            link = link_by_raw_text.get(
                                IntegrityPipeline._normalize_identifier(with_parens)
                            )
                # Final fallback: try extracting (author, year) from any APA-like format
                if link is None:
                    # Normalize both sides: extract first author name and year
                    # Patterns: "(Vaswani et al., 2017)", "(Vaswani et al. (2017))", "Vaswani et al. (2017)"
                    def normalize_et_al(text):
                        # Extract first author and year
                        m = _ET_AL_NORM_RE.search(text)
                        if m:
                            first = m.group(1).strip().split()[0].lower()
                            year = m.group(2)
                            return f"({first} et al., {year})"
                        return None

                    norm = normalize_et_al(normalized_text)
                    if norm:
                        link = link_by_raw_text.get(norm)
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
            # Extract citation context from page text (v1.3 - Neural content alignment)
            citation_context = None
            # Search all pages for the citation (page_num may be incorrect from extraction)
            for page in document_pages:
                if citation.raw_text.lower() in page.text.lower():
                    citation_context = IntegrityPipeline._extract_citation_context(
                        citation.raw_text,
                        page.text,
                        window_chars=200,
                    )
                    break

            # NEW v1.3: Provenance tracking - compute before calling checker
            api_exhausted = len(source.sources_succeeded) == 0 and len(source.sources_failed) > 0
            used_local_db = source.sources_succeeded == ["local_db"] if source.sources_succeeded else False

            # Pass mapping_status + style_profile + citation_context + provenance vào checker
            check_kwargs = {
                "mapping_status": mapping_status,
                "style_profile": style_profile,
                "citation_context": citation_context,
                "api_exhausted": api_exhausted,
                "used_local_db": used_local_db,
            }
            # Older injected checkers (used by downstream integrations and
            # legacy tests) do not accept the v1.3 provenance parameters.
            accepted = inspect.signature(self.checker.check).parameters
            check_kwargs = {
                key: value
                for key, value in check_kwargs.items()
                if key in accepted
            }
            verdict = self.checker.check(citation, source, **check_kwargs)
            verdict.mapping_status = mapping_status
            verdict.mapping_confidence = mapping_confidence
            verdict.citation_link = citation_link

            # NEW v1.3: Provenance tracking on verdict
            verdict.sources_succeeded = source.sources_succeeded
            verdict.sources_failed = source.sources_failed
            verdict.api_exhausted = api_exhausted
            verdict.used_local_db = used_local_db

            verdicts.append(verdict)
            logger.debug(
                f"  [{verdict.label.value}] conf={verdict.confidence:.2f} "
                f"mapping={verdict.mapping_status.value if verdict.mapping_status else 'NONE'} "
                f"raw={citation.raw_text[:60]}"
            )        # 3. Linking summary (counts per CitationMappingStatus) — cho Web UI dashboard
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
        if cache_key and self._use_report_cache:
            self._save_report_cache(cache_key, report)
        return report

    @staticmethod
    def _normalize_identifier(raw_text: str) -> str:
        """Normalize citation raw_text để so sánh dedup: bỏ doi.org prefix, lowercase.

        "https://doi.org/10.48550/arXiv.1706.03762" → "doi:10.48550/arXiv.1706.03762"
        "10.48550/arXiv.1706.03762" → "doi:10.48550/arXiv.1706.03762"
        "10.18653/v1/N19-1423" → "doi:10.18653/v1/N19-1423"
        "https://doi.org/10.18653/v1/N19-1423" → "doi:10.18653/v1/N19-1423"
        """
        text = raw_text.strip()
        # Bỏ trailing punctuation
        text = text.rstrip(".,;:")
        # Bỏ https://doi.org/ prefix
        doi_prefixes = [
            "https://doi.org/",
            "http://doi.org/",
            "https://doi.org",
            "http://doi.org",
            "doi.org/",
            "doi.org",
        ]
        for prefix in doi_prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):]
                break
        # Chuẩn hóa: lowercase + strip
        return text.strip().lower()

    @staticmethod
    def _extract_citation_context(
        citation_raw: str,
        page_text: str,
        window_chars: int = 150,
    ) -> str | None:
        """Extract context around a citation from page text.

        Args:
            citation_raw: The citation text (e.g., "(Vaswani et al., 2017)")
            page_text: Full text of the page containing the citation
            window_chars: Number of characters before/after to include

        Returns:
            String containing citation with surrounding context, or None if not found
        """
        if not citation_raw or not page_text:
            return None

        # Find citation in page text
        citation_lower = citation_raw.lower()
        page_lower = page_text.lower()

        pos = page_lower.find(citation_lower)
        if pos == -1:
            return None

        # Extract context window
        start = max(0, pos - window_chars)
        end = min(len(page_text), pos + len(citation_raw) + window_chars)

        context = page_text[start:end].strip()

        # Clean up: remove newlines in the middle and limit length
        context = " ".join(context.split())  # Normalize whitespace

        return context if len(context) > 20 else None

    @staticmethod
    def _merge_citations(
        body: list[Citation],
        references: list[Citation],
        appendix: list[Citation],
    ) -> list[Citation]:
        """Gộp + dedupe theo (style, normalized identifier). Reference list ưu tiên (có title).

        Flow v1.2:
            1. References trước (chứa title + DOI — đầy đủ nhất)
            2. body_citations (in-text — thiếu title)
            3. appendix_citations last (out-of-scope nhưng vẫn kiểm tra)

        Deduplication: normalize DOI/URL để "10.48550/arXiv.1706.03762" và
        "https://doi.org/10.48550/arXiv.1706.03762" được nhận diện là cùng 1 ref.
        """
        seen: set[tuple[str, str]] = set()
        merged: list[Citation] = []
        for source_list in (references, body, appendix):
            for c in source_list:
                # Dùng normalized identifier thay vì raw_text để dedupe
                normalized = IntegrityPipeline._normalize_identifier(c.raw_text)
                key = (c.style.value, normalized)
                if key not in seen:
                    seen.add(key)
                    merged.append(c)
        return merged

    @staticmethod
    def _merge_citations_legacy(
        in_text: list[Citation], ref_list: list[Citation]
    ) -> list[Citation]:
        """Legacy merge (backward compat cho fallback path) with DOI/URL normalization."""
        seen: set[tuple[str, str]] = set()
        merged: list[Citation] = []
        for c in ref_list:
            normalized = IntegrityPipeline._normalize_identifier(c.raw_text)
            key = (c.style.value, normalized)
            if key not in seen:
                seen.add(key)
                merged.append(c)
        for c in in_text:
            normalized = IntegrityPipeline._normalize_identifier(c.raw_text)
            key = (c.style.value, normalized)
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

    @staticmethod
    def _populate_citation_metadata(
        in_text: list[Citation],
        references: list[Citation],
        link_lookup: dict[str, CitationLink],
    ) -> None:
        """Populate citation metadata from matched reference entries.

        For numeric citations like "[1]" that have no title/author/year,
        copy metadata from the matched reference entry.

        This ensures that verification can use the full reference metadata
        even when the in-text citation is just a number.
        """
        # Build reference lookup by reference_id
        ref_by_id: dict[str, Citation] = {}
        for ref in references:
            if ref.reference_id:
                ref_by_id[ref.reference_id] = ref

        for citation in in_text:
            # Only populate if citation lacks essential metadata
            if citation.title and citation.authors and citation.year:
                continue

            # Find matching reference via link lookup by occurrence_id
            # (in-text citations have occurrence_id as their reference_id)
            link = link_lookup.get(citation.reference_id)

            if link and link.reference_id:
                ref = ref_by_id.get(link.reference_id)
                if ref:
                    # Copy metadata from reference if citation lacks it
                    if not citation.title and ref.title:
                        citation.title = ref.title
                    if not citation.authors and ref.authors:
                        citation.authors = ref.authors
                    if not citation.year and ref.year:
                        citation.year = ref.year
                    if not citation.doi and ref.doi:
                        citation.doi = ref.doi

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
        """Map normalized identifier → CitationLink cho O(1) lookup từ verdict.

        Indexes by (in priority order):
          1. occurrence_id (in-text citation's stable ID)
          2. normalized identifier (DOI/URL forms)
          3. raw text lowercased (for non-DOI citations)
        """
        lookup: dict[str, CitationLink] = {}
        for link in links:
            # Index by occurrence_id FIRST (most reliable for numeric citations)
            if link.occurrence_id:
                lookup[link.occurrence_id] = link

            evidence = link.evidence or {}
            raw = evidence.get("raw", "") or evidence.get("raw_text", "")
            if raw:
                # Normalize newlines and extra spaces first (for consistent matching)
                raw_normalized = raw.replace("\n", " ").replace("  ", " ").strip()
                # Normalize: both DOI and URL form map to same key
                normalized = IntegrityPipeline._normalize_identifier(raw_normalized)
                lookup[normalized] = link
                # Also index by raw as fallback (for non-DOI citations)
                lookup[raw_normalized.lower()] = link
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


def _serialize_author(author: Any) -> str:
    """Serialize parser Author objects and plain strings uniformly."""
    if isinstance(author, str):
        return author
    if hasattr(author, "last_name"):
        parts = [getattr(author, "last_name", "")]
        for attr in ("first_name", "middle_name"):
            value = getattr(author, attr, None)
            if value:
                parts.append(value)
        return " ".join(part for part in parts if part)
    return str(author)


def _serialize_citation(citation: Citation) -> dict[str, Any]:
    """Serialize all citation metadata needed by report-cache rehydration."""
    return {
        "raw_text": citation.raw_text,
        "citation_type": citation.citation_type.value,
        "style": citation.style.value,
        "authors": [_serialize_author(author) for author in (citation.authors or [])],
        "year": citation.year,
        "title": citation.title,
        "venue": citation.venue,
        "doi": citation.doi,
        "url": citation.url,
        "volume": citation.volume,
        "issue": citation.issue,
        "pages": citation.pages,
        "title_normalized": citation.title_normalized,
        "year_suffix": citation.year_suffix,
        "order_index": citation.order_index,
        "numeric_index": citation.numeric_index,
        "page_num": citation.page_num,
        "paragraph_num": citation.paragraph_num,
        "matched_pattern": citation.matched_pattern,
        "raw_in_text_citation": citation.raw_in_text_citation,
        "confidence": citation.confidence,
        "reference_id": citation.reference_id,
        "context": citation.context,
    }


def _deserialize_citation(data: dict[str, Any]) -> Citation:
    """Deserialize a cached citation without rerunning PDF extraction."""
    try:
        citation_type = CitationType(data.get("citation_type", CitationType.UNKNOWN.value))
    except ValueError:
        citation_type = CitationType.UNKNOWN
    try:
        style = CitationStyle(data.get("style", CitationStyle.UNKNOWN.value))
    except ValueError:
        style = CitationStyle.UNKNOWN
    return Citation(
        raw_text=data.get("raw_text", ""),
        citation_type=citation_type,
        style=style,
        authors=list(data.get("authors") or []),
        year=data.get("year"),
        title=data.get("title"),
        venue=data.get("venue"),
        doi=data.get("doi"),
        url=data.get("url"),
        volume=data.get("volume"),
        issue=data.get("issue"),
        pages=data.get("pages"),
        title_normalized=data.get("title_normalized"),
        year_suffix=data.get("year_suffix"),
        order_index=int(data.get("order_index", 0)),
        numeric_index=data.get("numeric_index"),
        page_num=int(data.get("page_num", 0)),
        paragraph_num=int(data.get("paragraph_num", 0)),
        matched_pattern=data.get("matched_pattern"),
        raw_in_text_citation=data.get("raw_in_text_citation"),
        confidence=float(data.get("confidence", 0.0)),
        reference_id=data.get("reference_id"),
        context=data.get("context"),
    )


def _match_features_from_dict(data: dict[str, Any]) -> MatchFeatures:
    """Build ``MatchFeatures`` while tolerating older cache schemas."""
    return MatchFeatures(
        title_sim_fuzzy=float(data.get("title_sim_fuzzy", 0.0)),
        title_sim_semantic=float(data.get("title_sim_semantic", 0.0)),
        author_jaccard=float(data.get("author_jaccard", 0.0)),
        year_distance=int(data.get("year_distance", 999)),
        doi_exact_match=bool(data.get("doi_exact_match", False)),
        source_consensus=int(data.get("source_consensus", 0)),
        content_alignment_score=float(data.get("content_alignment_score", 0.0)),
        content_alignment_confidence=data.get("content_alignment_confidence", ""),
        content_is_aligned=bool(data.get("content_is_aligned", False)),
    )


def _deserialize_citation_link(data: Any) -> CitationLink | None:
    """Deserialize an optional linker edge from a cached report."""
    if not data:
        return None
    try:
        status = CitationMappingStatus(data.get("status", CitationMappingStatus.UNRESOLVED.value))
    except ValueError:
        status = CitationMappingStatus.UNRESOLVED
    try:
        from integrity_checker.models.validation import MappingMethod

        method = MappingMethod(data.get("method", MappingMethod.NO_KEYS.value))
    except ValueError:
        method = "no_keys"
    return CitationLink(
        occurrence_id=data.get("occurrence_id", ""),
        reference_id=data.get("reference_id"),
        status=status,
        confidence=float(data.get("confidence", 0.0)),
        method=method,
        evidence=dict(data.get("evidence") or {}),
        page=int(data.get("page", 0)),
        section=data.get("section", ""),
    )


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
        # NEW v1.3: Provenance tracking
        "provenance": {
            "sources_succeeded": v.sources_succeeded,
            "sources_failed": v.sources_failed,
            "api_exhausted": v.api_exhausted,
            "used_local_db": v.used_local_db,
        },
        "warnings": _get_verdict_warnings(v),
    }


def _get_verdict_warnings(v: CitationVerdict) -> list[str]:
    """Generate warning flags based on provenance (for CLI)."""
    return _get_verdict_warnings_from_verdict(v)


def _get_verdict_warnings_from_verdict(v: CitationVerdict) -> list[str]:
    """Generate warning flags based on provenance (for JSON serialization)."""
    warnings = []

    if v.api_exhausted:
        warnings.append("API_EXHAUSTED: All external APIs failed - verification based on limited data")

    if v.used_local_db and not v.api_exhausted:
        warnings.append("LOCAL_DB: Result from local database")

    if v.api_exhausted and v.label.value == "verified":
        warnings.append("CAUTION: Verified despite API failures - confidence reduced")

    if len(v.sources_succeeded) == 1 and v.sources_succeeded[0] == "local_db":
        warnings.append("LOCAL_DB_ONLY: Verification from local database only")

    return warnings


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
        help="Đường dẫn output JSON (mặc định: reports/<pdf-stem>.json)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Chỉ in summary ra stdout, không ghi file JSON",
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
            "resource": "🔗",
        }[v.label.value]

        # Build provenance string
        prov_parts = []
        if v.sources_succeeded:
            prov_parts.append(f"sources={','.join(v.sources_succeeded)}")
        if v.api_exhausted:
            prov_parts.append("API_EXHAUSTED")

        prov_str = f" ({', '.join(prov_parts)})" if prov_parts else ""

        # Add warnings indicator
        warn_indicator = " ⚠" if v.api_exhausted or v.used_local_db else ""

        print(
            f"  {marker} [{v.label.value:25s}] conf={v.confidence:.0%}{prov_str}{warn_indicator}  "
            f"raw={v.citation.raw_text[:80]}"
        )
    print("\n ⚠ " + report.disclaimer)
    print()

    # Ghi file JSON: --stdout bỏ qua, mặc định ghi vào reports/, --output ghi đúng path chỉ định
    if args.stdout:
        return

    if args.output:
        out_path = Path(args.output)
    else:
        # Default: reports/<pdf-stem>.json (relative to CWD)
        out_path = Path("reports") / f"{pdf_path.stem}.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
    print(f" 📄 Report saved → {out_path}")
    logger.info(f"Wrote report → {out_path}")


if __name__ == "__main__":
    main()
