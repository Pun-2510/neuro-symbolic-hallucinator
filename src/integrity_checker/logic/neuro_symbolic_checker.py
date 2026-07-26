"""NeuroSymbolicChecker — orchestrate neural features + symbolic rules."""

from __future__ import annotations

from integrity_checker.config import get_settings
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceResult
from integrity_checker.models.validation import CitationVerdict
from integrity_checker.matching.features import FeatureCalculator
from integrity_checker.logic.rules import SymbolicRules


class NeuroSymbolicChecker:
    """Kết hợp:
        - Neural: feature vector từ FeatureCalculator
        - Symbolic: SymbolicRules decision table

    # TODO(user): tuần 12–13 — bổ sung:
        - Thêm classifier ML (LogisticRegression / XGBoost) như baseline B4
        - Calibration layer (Platt scaling) cho confidence
    """

    def __init__(
        self,
        feature_calculator: FeatureCalculator | None = None,
        rules: SymbolicRules | None = None,
    ) -> None:
        self.feature_calculator = feature_calculator or FeatureCalculator()
        self.rules = rules or SymbolicRules()

    def check(self, citation: Citation, source: SourceResult) -> CitationVerdict:
        """Trả CitationVerdict đầy đủ (label + confidence + reasoning + features)."""
        features = self.feature_calculator.compute(citation, source)
        outcome = self.rules.apply(features, source)
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