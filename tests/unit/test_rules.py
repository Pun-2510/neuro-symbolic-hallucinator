"""Unit tests cho SymbolicRules."""

from __future__ import annotations

from integrity_checker.logic.rules import SymbolicRules
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import MatchFeatures, ValidationLabel


def test_no_candidate_no_api_success_returns_suspected() -> None:
    """Không có candidate, API OK → SUSPECTED_HALLUCINATION."""
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="test",
        candidates=[],
        sources_queried=["crossref"],
        sources_succeeded=[],
        sources_failed={},
    )
    outcome = rules.apply(MatchFeatures(), source)
    assert outcome.label == ValidationLabel.SUSPECTED_HALLUCINATION
    assert "R-NO-CANDIDATE" in outcome.triggered_rules


def test_no_candidate_all_api_failed_returns_unresolved() -> None:
    """Không có candidate, tất cả API fail → UNRESOLVED."""
    rules = SymbolicRules()
    source = SourceResult(
        citation_raw="test",
        candidates=[],
        sources_queried=["crossref", "openalex"],
        sources_succeeded=[],
        sources_failed={"crossref": "timeout", "openalex": "timeout"},
    )
    outcome = rules.apply(MatchFeatures(), source)
    assert outcome.label == ValidationLabel.UNRESOLVED
    assert "R-FAIL-ALL" in outcome.triggered_rules


def test_candidate_with_doi_and_high_title_sim_returns_verified() -> None:
    """DOI match + title sim cao → VERIFIED."""
    rules = SymbolicRules()
    cand = SourceCandidate(
        source_name="crossref",
        found=True,
        doi="10.1038/nature14539",
        title="Deep learning",
        authors=["LeCun, Y."],
        year="2015",
        confidence=0.9,
    )
    source = SourceResult(
        citation_raw="LeCun, 2015",
        candidates=[cand],
        sources_queried=["crossref"],
        sources_succeeded=["crossref"],
    )
    features = MatchFeatures(
        title_sim_fuzzy=0.95,
        title_sim_semantic=0.95,
        author_jaccard=0.8,
        year_distance=0,
        doi_exact_match=True,
        source_consensus=1,
    )
    outcome = rules.apply(features, source)
    assert outcome.label == ValidationLabel.VERIFIED
    assert "R-DOI-TITLE-AUTHOR" in outcome.triggered_rules


def test_doi_match_low_title_sim_returns_metadata_error() -> None:
    """DOI match nhưng title sim thấp → METADATA_ERROR."""
    rules = SymbolicRules()
    cand = SourceCandidate(
        source_name="crossref",
        found=True,
        doi="10.1038/nature14539",
        title="Deep learning revisited",
        authors=["LeCun, Y."],
        year="2015",
    )
    source = SourceResult(
        citation_raw="test",
        candidates=[cand],
        sources_queried=["crossref"],
        sources_succeeded=["crossref"],
    )
    features = MatchFeatures(
        title_sim_fuzzy=0.7,
        author_jaccard=0.8,
        year_distance=0,
        doi_exact_match=True,
        source_consensus=1,
    )
    outcome = rules.apply(features, source)
    assert outcome.label == ValidationLabel.METADATA_ERROR


def test_abstention_border_zone_returns_unresolved() -> None:
    """Title sim trong vùng biên [0.4, 0.6] → UNRESOLVED."""
    rules = SymbolicRules()
    cand = SourceCandidate(
        source_name="openalex",
        found=True,
        title="Some related paper",
        confidence=0.5,
    )
    source = SourceResult(
        citation_raw="test",
        candidates=[cand],
        sources_queried=["openalex"],
        sources_succeeded=["openalex"],
    )
    features = MatchFeatures(
        title_sim_fuzzy=0.5,  # đúng biên trên
        source_consensus=1,
    )
    outcome = rules.apply(features, source)
    assert outcome.label == ValidationLabel.UNRESOLVED
    assert "R-ABSTENTION-BORDER" in outcome.triggered_rules