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