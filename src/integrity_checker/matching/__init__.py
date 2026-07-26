"""Matching module — feature engineering cho so khớp citation vs candidate.

Bao gồm:
- Fuzzy (RapidFuzz)
- Semantic (sentence-transformers wrapper)
- Features (gộp thành MatchFeatures)
- Consensus (cross-source agreement)
"""

from integrity_checker.matching.consensus import ConsensusCalculator
from integrity_checker.matching.features import FeatureCalculator
from integrity_checker.matching.fuzzy import FuzzyMatcher
from integrity_checker.matching.semantic import SemanticMatcher

__all__ = [
    "FuzzyMatcher",
    "SemanticMatcher",
    "FeatureCalculator",
    "ConsensusCalculator",
]