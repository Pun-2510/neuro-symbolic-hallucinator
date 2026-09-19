"""NeuroSymbolicChecker — orchestrate neural features + symbolic rules."""

from __future__ import annotations

from typing import TYPE_CHECKING

from integrity_checker.config import get_settings
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import CitationVerdict, MatchFeatures, ValidationLabel
from integrity_checker.matching.features import FeatureCalculator
from integrity_checker.logic.rules import SymbolicRules
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator

if TYPE_CHECKING:
    from integrity_checker.linking.statuses import CitationMappingStatus, StyleProfile


class NeuroSymbolicChecker:
    """Kết hợp:
        - Neural: feature vector từ FeatureCalculator
        - Symbolic: SymbolicRules decision table

    v1.2 §3.2.2 (task #33): check() giờ nhận thêm ``mapping_status`` +
    ``style_profile`` để SymbolicRules có đủ input cho rules mở rộng.

    2026-09-15: Uses SemanticMatcher singleton for ~5s performance improvement
    by avoiding model reload on each instantiation.

    FIX Bug 5: Now checks for known seminal papers and returns VERIFIED
    with high confidence even when APIs fail.

    # TODO(user): tuần 12–13 — bổ sung:
        - Thêm classifier ML (LogisticRegression / XGBoost) như baseline B4
        - Calibration layer (Platt scaling) cho confidence
    """

    _feature_calculator: FeatureCalculator | None = None

    def __init__(
        self,
        feature_calculator: FeatureCalculator | None = None,
        rules: SymbolicRules | None = None,
    ) -> None:
        # Reuse shared FeatureCalculator instance to benefit from SemanticMatcher singleton
        if feature_calculator is not None:
            self.feature_calculator = feature_calculator
        elif NeuroSymbolicChecker._feature_calculator is None:
            NeuroSymbolicChecker._feature_calculator = FeatureCalculator()
        self.feature_calculator = NeuroSymbolicChecker._feature_calculator
        self.rules = rules or SymbolicRules()

    def check(
        self,
        citation: Citation,
        source: SourceResult,
        mapping_status: "CitationMappingStatus | None" = None,
        style_profile: "StyleProfile | None" = None,
    ) -> CitationVerdict:
        """Trả CitationVerdict đầy đủ (label + confidence + reasoning + features).

        FIX Bug 5: If citation matches a known seminal paper, return VERIFIED
        with high confidence even when all APIs fail.
        """
        # FIX Bug 5: Check for known seminal papers first
        is_known, paper_info = RetrievalOrchestrator.is_known_paper(citation)
        if is_known and paper_info:
            # Known paper - return VERIFIED with high confidence
            # Create a synthetic SourceCandidate from known paper info
            known_candidate = SourceCandidate(
                source_name="known_papers",
                found=True,
                title=paper_info.get("title"),
                doi=paper_info.get("doi"),
                authors=paper_info.get("authors", []),
                year=paper_info.get("year"),
                confidence=0.95,
                score=1.0,
            )
            # Inject into source result for feature calculation
            enhanced_source = SourceResult(
                citation_raw=source.citation_raw,
                candidates=[known_candidate] + source.candidates,
                sources_queried=["known_papers"] + source.sources_queried,
                sources_succeeded=["known_papers"] + source.sources_succeeded,
                sources_failed=source.sources_failed,
            )
            # Recalculate features with known paper
            features = self.feature_calculator.compute(citation, enhanced_source)

            return CitationVerdict(
                citation=citation,
                label=ValidationLabel.VERIFIED,  # Known papers are VERIFIED
                confidence=0.90,
                matched_source=enhanced_source,
                features=features,
                reasoning=f"Known seminal paper verified via known papers database: '{paper_info.get('title')}'. APIs failed but paper is well-documented.",
                triggered_rules=["R-KNOWN-PAPER"],
                mismatched_fields=[],
            )

        features = self.feature_calculator.compute(citation, source)
        outcome = self.rules.apply(
            features,
            source,
            mapping_status=mapping_status,
            style_profile=style_profile,
            citation_doi=citation.doi,
            citation_url=citation.url,
        )
        return CitationVerdict(
            citation=citation,
            label=outcome.label,
            confidence=outcome.confidence,
            matched_source=source,
            features=features,
            reasoning=outcome.reasoning,
            triggered_rules=outcome.triggered_rules,
            mismatched_fields=outcome.mismatched_fields,
        )