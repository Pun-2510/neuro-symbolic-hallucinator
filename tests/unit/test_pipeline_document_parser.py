"""Unit test cho IntegrityPipeline với DocumentParser integration (task #25).

Test cả 2 path:
- Modern: DocumentParser (PyMuPDF + GROBID) — khi use_document_parser=True
- Legacy: BasePDFParser + CitationExtractor + ReferenceListParser — fallback

Verify:
- _merge_citations dedupe đúng (priority ref > body > appendix)
- use_document_parser=False → fallback legacy flow
- use_document_parser=True → gọi DocumentParser.parse()
- num_pages, num_citations populated
- verdicts generated per citation
- CIS computed
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from integrity_checker.extraction.document_parser import ParsedDocument
from integrity_checker.extraction.base import Document
from integrity_checker.models.citation import (
    Citation,
    CitationStyle,
    CitationType,
)
from integrity_checker.pipeline.integrity_pipeline import (
    AnalysisReport,
    IntegrityPipeline,
)


def _make_citation(
    raw_text: str, title: str | None = None, year: str | None = None
) -> Citation:
    """Build minimal Citation cho test."""
    return Citation(
        raw_text=raw_text,
        citation_type=CitationType.IN_TEXT,
        style=CitationStyle.APA,
        title=title,
        year=year,
    )


class TestPipelineMergeCitations:
    """Test _merge_citations cho modern flow."""

    def test_merge_priority_ref_over_body_over_appendix(self):
        """References ưu tiên (có title), sau đó body, cuối cùng appendix."""
        ref = _make_citation("Smith, J. (2020). A study. Journal A.", title="A study", year="2020")
        body = _make_citation("(Smith, 2020)")
        appendix = _make_citation("(Smith, 2020)")  # duplicate of body

        merged = IntegrityPipeline._merge_citations(
            body=[body], references=[ref], appendix=[appendix]
        )
        assert len(merged) == 2
        # Reference đầu tiên (priority)
        assert merged[0].title == "A study"
        # Body ở vị trí 2 (dedupe vs appendix giống raw_text)
        assert merged[1].raw_text == "(Smith, 2020)"

    def test_merge_dedupe_by_raw_text(self):
        """Citation trùng raw_text → chỉ giữ 1."""
        a = _make_citation("Smith, J. (2020).")
        b = _make_citation("Smith, J. (2020).")
        merged = IntegrityPipeline._merge_citations(
            body=[a], references=[b], appendix=[]
        )
        assert len(merged) == 1

    def test_merge_empty_inputs(self):
        """Empty lists → empty output."""
        merged = IntegrityPipeline._merge_citations(body=[], references=[], appendix=[])
        assert merged == []


class TestPipelineLegacyMerge:
    """Test _merge_citations_legacy cho fallback flow."""

    def test_legacy_merge_priority_ref(self):
        ref = _make_citation("Smith, J. (2020).", title="A study")
        body = _make_citation("(Smith, 2020)")
        merged = IntegrityPipeline._merge_citations_legacy(in_text=[body], ref_list=[ref])
        assert len(merged) == 2
        # Reference đầu tiên
        assert merged[0].title == "A study"


class TestPipelineWithDocumentParser:
    """Test pipeline.run_async() với DocumentParser mocked."""

    @pytest.mark.asyncio
    async def test_pipeline_uses_document_parser_when_enabled(self):
        """use_document_parser=True → gọi DocumentParser.parse()."""
        # Mock DocumentParser
        body_cit = _make_citation("(Smith, 2020)")
        ref_cit = _make_citation("Smith, J. (2020). A study.", title="A study", year="2020")
        parsed = ParsedDocument(
            document=Document(file_path="/fake/path.pdf", num_pages=5, pages=[]),
            body_citations=[body_cit],
            references=[ref_cit],
            appendix_citations=[],
            sections=[],
            parser_warnings=[],
        )

        mock_doc_parser = MagicMock()
        mock_doc_parser.parse.return_value = parsed

        # Mock orchestrator + checker để tránh network calls
        mock_orchestrator = MagicMock()

        async def mock_retrieve(citation):
            from integrity_checker.models.source import SourceCandidate, SourceResult
            return SourceResult(
                citation_raw=citation.raw_text,
                candidates=[SourceCandidate(source_name="test", found=False)],
                sources_queried=["test"],
                sources_succeeded=[],
                sources_failed={"test": "mock"},
            )

        mock_orchestrator.retrieve = mock_retrieve

        mock_checker = MagicMock()
        mock_verdict = MagicMock()
        mock_verdict.label.value = "unresolved"
        mock_verdict.confidence = 0.0
        mock_verdict.citation = body_cit
        mock_verdict.features.title_sim_fuzzy = 0.0
        mock_verdict.features.title_sim_semantic = 0.0
        mock_verdict.features.author_jaccard = 0.0
        mock_verdict.features.year_distance = 0
        mock_verdict.features.doi_exact_match = False
        mock_verdict.features.source_consensus = 0
        mock_verdict.reasoning = "mock"
        mock_verdict.triggered_rules = []
        mock_verdict.mismatched_fields = []
        mock_checker.check.return_value = mock_verdict

        from integrity_checker.logic.cis import CISCalculator
        pipeline = IntegrityPipeline(
            document_parser=mock_doc_parser,
            use_document_parser=True,
            orchestrator=mock_orchestrator,
            checker=mock_checker,
            cis_calc=CISCalculator(),
        )

        report = await pipeline.run_async("/fake/path.pdf", essay_id=42)

        # Verify DocumentParser was called
        mock_doc_parser.parse.assert_called_once_with("/fake/path.pdf")

        # Verify report populated
        assert isinstance(report, AnalysisReport)
        assert report.essay_id == 42
        assert report.filename == "path.pdf"
        assert report.num_citations == 2  # body + ref
        assert len(report.verdicts) == 2

    @pytest.mark.asyncio
    async def test_pipeline_uses_legacy_path_when_disabled(self):
        """use_document_parser=False → fallback legacy flow."""
        # Mock DocumentParser không được gọi
        mock_doc_parser = MagicMock()
        mock_doc_parser.parse.return_value = ParsedDocument(
            document=Document(file_path="/fake/path.pdf", num_pages=0, pages=[])
        )

        # Mock parser (legacy BasePDFParser)
        body_cit = _make_citation("(Smith, 2020)")
        ref_cit = _make_citation("Smith, J. (2020). A study.", title="A study")
        mock_parser = MagicMock()
        mock_doc = MagicMock(spec=Document)
        mock_doc.num_pages = 5
        mock_doc.pages = []
        mock_parser.parse.return_value = mock_doc

        # Mock extractor + ref_parser
        mock_extractor = MagicMock()
        mock_extractor.extract_from_document.return_value = [body_cit]
        mock_extractor.preprocessor = MagicMock()
        mock_extractor.find_reference_section.return_value = None

        mock_ref_parser = MagicMock()
        mock_ref_parser.parse_reference_section.return_value = [ref_cit]

        # Mock orchestrator + checker
        mock_orchestrator = MagicMock()

        async def mock_retrieve(citation):
            from integrity_checker.models.source import SourceCandidate, SourceResult
            return SourceResult(
                citation_raw=citation.raw_text,
                candidates=[SourceCandidate(source_name="test", found=False)],
                sources_queried=["test"],
                sources_succeeded=[],
                sources_failed={"test": "mock"},
            )

        mock_orchestrator.retrieve = mock_retrieve

        mock_checker = MagicMock()
        mock_verdict = MagicMock()
        mock_verdict.label.value = "unresolved"
        mock_verdict.confidence = 0.0
        mock_verdict.citation = body_cit
        mock_verdict.features.title_sim_fuzzy = 0.0
        mock_verdict.features.title_sim_semantic = 0.0
        mock_verdict.features.author_jaccard = 0.0
        mock_verdict.features.year_distance = 0
        mock_verdict.features.doi_exact_match = False
        mock_verdict.features.source_consensus = 0
        mock_verdict.reasoning = "mock"
        mock_verdict.triggered_rules = []
        mock_verdict.mismatched_fields = []
        mock_checker.check.return_value = mock_verdict

        from integrity_checker.logic.cis import CISCalculator
        pipeline = IntegrityPipeline(
            parser=mock_parser,
            extractor=mock_extractor,
            ref_parser=mock_ref_parser,
            orchestrator=mock_orchestrator,
            checker=mock_checker,
            cis_calc=CISCalculator(),
            document_parser=mock_doc_parser,
            use_document_parser=False,
        )

        report = await pipeline.run_async("/fake/path.pdf")

        # Verify legacy path: DocumentParser NOT called, parser.parse called
        mock_doc_parser.parse.assert_not_called()
        mock_parser.parse.assert_called_once()
        mock_extractor.extract_from_document.assert_called_once()
        mock_ref_parser.parse_reference_section.assert_called_once()

        # num_pages từ legacy parser
        assert report.num_pages == 5
        assert report.num_citations == 2

    @pytest.mark.asyncio
    async def test_pipeline_default_uses_legacy_path(self):
        """Default (use_document_parser=None) → False (backward compat)."""
        pipeline = IntegrityPipeline()
        assert pipeline._use_document_parser is False

        pipeline = IntegrityPipeline(use_document_parser=True)
        assert pipeline._use_document_parser is True

        pipeline = IntegrityPipeline(use_document_parser=False)
        assert pipeline._use_document_parser is False