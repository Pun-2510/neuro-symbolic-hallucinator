"""Unit tests cho CISCalculator."""

from __future__ import annotations

from integrity_checker.logic.cis import CISCalculator
from integrity_checker.models.citation import Citation, CitationStyle, CitationType
from integrity_checker.models.validation import CitationVerdict, ValidationLabel


def _make_verdict(raw: str, label: ValidationLabel, doi: str | None = None) -> CitationVerdict:
    c = Citation(
        raw_text=raw,
        citation_type=CitationType.REFERENCE_LIST,
        style=CitationStyle.APA,
        doi=doi,
    )
    return CitationVerdict(citation=c, label=label, confidence=0.9)


def test_cis_empty() -> None:
    cis = CISCalculator().compute([])
    assert cis.score == 0.0
    assert cis.num_citations == 0


def test_cis_all_verified() -> None:
    verdicts = [
        _make_verdict("a", ValidationLabel.VERIFIED, doi="10.1/a"),
        _make_verdict("b", ValidationLabel.VERIFIED, doi="10.1/b"),
        _make_verdict("c", ValidationLabel.VERIFIED, doi="10.1/c"),
    ]
    cis = CISCalculator().compute(verdicts)
    assert cis.score > 90.0  # do verified_ratio + identifier_validity full
    assert cis.num_unresolved == 0


def test_cis_all_hallucinated_low_score() -> None:
    verdicts = [
        _make_verdict("a", ValidationLabel.SUSPECTED_HALLUCINATION),
        _make_verdict("b", ValidationLabel.SUSPECTED_HALLUCINATION),
    ]
    cis = CISCalculator().compute(verdicts)
    assert cis.score < 50.0


def test_cis_mixed() -> None:
    verdicts = [
        _make_verdict("a", ValidationLabel.VERIFIED, doi="10.1/a"),
        _make_verdict("b", ValidationLabel.METADATA_ERROR, doi="10.1/b"),
        _make_verdict("c", ValidationLabel.SUSPECTED_HALLUCINATION),
        _make_verdict("d", ValidationLabel.UNRESOLVED),
    ]
    cis = CISCalculator().compute(verdicts)
    assert 0 <= cis.score <= 100
    assert cis.num_unresolved == 1
    assert cis.num_citations == 4
    assert abs(
        sum(cis.weights_used.values()) - 1.0
    ) < 0.01  # weights phải sum = 1


def test_cis_excludes_url_resources_from_score() -> None:
    academic = _make_verdict("paper", ValidationLabel.VERIFIED, doi="10.1/paper")
    resource = _make_verdict("https://github.com/example/repo", ValidationLabel.RESOURCE)

    cis = CISCalculator().compute([academic, resource])

    assert cis.score > 90.0
    assert cis.num_citations == 1
    assert cis.num_unresolved == 0


def test_cis_strategy_a_penalizes_uncited_and_duplicate_references() -> None:
    """Strategy A (with LinkingResult) must penalize UNCITED_REFERENCE and DUPLICATE_REFERENCE."""
    from integrity_checker.linking.citation_linker import LinkingResult
    from integrity_checker.linking.statuses import CitationMappingStatus
    from integrity_checker.models.validation import CitationLink, MappingMethod

    v_matched = _make_verdict("Vaswani (2017)", ValidationLabel.VERIFIED, doi="10.1/a")
    v_matched.mapping_status = CitationMappingStatus.MATCHED

    v_uncited = _make_verdict("Devlin (2019)", ValidationLabel.VERIFIED, doi="10.1/b")
    v_uncited.mapping_status = CitationMappingStatus.UNCITED_REFERENCE

    v_dup = _make_verdict("Vaswani (2017) duplicate", ValidationLabel.VERIFIED, doi="10.1/a")
    v_dup.mapping_status = CitationMappingStatus.DUPLICATE_REFERENCE

    linking_result = LinkingResult(
        links=[
            CitationLink(
                occurrence_id="occ-0000",
                reference_id="ref-0000",
                status=CitationMappingStatus.MATCHED,
                confidence=1.0,
                method=MappingMethod.AUTHOR_YEAR,
            )
        ],
        unmatched_reference_ids=["ref-0001"],
    )

    cis = CISCalculator().compute([v_matched, v_uncited, v_dup], linking_result=linking_result)
    assert cis.components.in_text_bib_consistency < 1.0


def test_analysis_report_round_trips_neural_and_venue_features() -> None:
    """AnalysisReport.to_dict() and from_dict() preserve venue_sim and content alignment features."""
    from integrity_checker.models.validation import MatchFeatures
    from integrity_checker.pipeline.integrity_pipeline import AnalysisReport

    v = _make_verdict("Vaswani (2017)", ValidationLabel.VERIFIED, doi="10.1/a")
    v.features = MatchFeatures(
        title_sim_fuzzy=0.95,
        title_sim_semantic=0.92,
        author_jaccard=1.0,
        year_distance=0,
        doi_exact_match=True,
        source_consensus=2,
        venue_sim=0.88,
        content_alignment_score=0.76,
        content_alignment_confidence="high",
        content_is_aligned=True,
    )
    report = AnalysisReport(
        essay_id=1,
        filename="test.pdf",
        num_pages=5,
        num_citations=1,
        extracted_citations=[v.citation],
        verdicts=[v],
        cis=CISCalculator().compute([v]),
    )
    payload = report.to_dict()
    feat_dict = payload["verdicts"][0]["features"]
    assert feat_dict["venue_sim"] == 0.88
    assert feat_dict["content_alignment_score"] == 0.76
    assert feat_dict["content_alignment_confidence"] == "high"
    assert feat_dict["content_is_aligned"] is True

    rehydrated = AnalysisReport.from_dict(payload)
    assert rehydrated.verdicts[0].features.venue_sim == 0.88
    assert rehydrated.verdicts[0].features.content_alignment_score == 0.76
    assert rehydrated.verdicts[0].features.content_alignment_confidence == "high"
    assert rehydrated.verdicts[0].features.content_is_aligned is True


def test_cis_linking_consistency_falls_back_when_no_in_text_links() -> None:
    """When linking_result has 0 active links, CIS falls back to Strategy B (verdict-level mapping_status)."""
    from integrity_checker.linking.citation_linker import LinkingResult
    from integrity_checker.linking.statuses import CitationMappingStatus

    v1 = _make_verdict("Welling (2008)", ValidationLabel.VERIFIED)
    v1.mapping_status = CitationMappingStatus.IN_TEXT_MISMATCH
    v2 = _make_verdict("Resig (2006)", ValidationLabel.VERIFIED)
    v2.mapping_status = CitationMappingStatus.IN_TEXT_MISMATCH

    linking_result = LinkingResult(
        links=[],
        unmatched_reference_ids=["ref-0000", "ref-0001"],
    )

    cis = CISCalculator().compute([v1, v2], linking_result=linking_result)
    assert abs(cis.components.in_text_bib_consistency - 0.85) < 1e-6


def test_cis_identifier_validity_evaluates_urls_and_penalizes_dead_links() -> None:
    """identifier_validity evaluates both DOI and URL identifiers and penalizes dead links."""
    from integrity_checker.models.source import SourceResult

    c_alive = Citation(
        raw_text="Paper A (2022). https://arxiv.org/abs/2201.00001",
        citation_type=CitationType.REFERENCE_LIST,
        style=CitationStyle.APA,
        url="https://arxiv.org/abs/2201.00001",
    )
    v_alive = CitationVerdict(
        citation=c_alive,
        label=ValidationLabel.VERIFIED,
        confidence=0.95,
        matched_source=SourceResult(citation_raw="Paper A", url_status="alive", url_status_code=200),
    )

    c_dead = Citation(
        raw_text="Paper B (2022). https://example-university.edu/dead-paper.pdf",
        citation_type=CitationType.REFERENCE_LIST,
        style=CitationStyle.APA,
        url="https://example-university.edu/dead-paper.pdf",
    )
    v_dead = CitationVerdict(
        citation=c_dead,
        label=ValidationLabel.VERIFIED,
        confidence=0.90,
        domain_exception=True,
        triggered_rules=["R-HIGH-CONF", "R-DOMAIN-EXCEPTION", "R-BROKEN-LINK"],
        matched_source=SourceResult(citation_raw="Paper B", url_status="dead_link", url_status_code=404),
    )

    cis = CISCalculator().compute([v_alive, v_dead])
    assert abs(cis.components.identifier_validity - 0.5) < 1e-6



