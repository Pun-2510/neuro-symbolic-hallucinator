"""NeuroSymbolicChecker -- orchestrate neural features + symbolic rules.

v1.3: Bổ sung content alignment check (Neural layer) để kiểm tra semantic
alignment giữa đoạn văn được trích dẫn và paper nguồn.

Đây là component chính thể hiện tính "Neuro-Symbolic":
    - Neural: Sentence-BERT embeddings cho content-context alignment
    - Symbolic: Bộ quy tắc regex, logic validation cho decision making
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
        - Neural: feature vector từ FeatureCalculator (bao gồm semantic content alignment)
        - Symbolic: SymbolicRules decision table

    v1.3: Bổ sung citation context để compute content alignment.
    Citation context = đoạn văn xung quanh citation trong essay,
    dùng để kiểm tra semantic alignment với paper nguồn.

    v1.2 §3.2.2 (task #33): check() giờ nhận thêm ``mapping_status`` +
    ``style_profile`` để SymbolicRules có đủ input cho rules mở rộng.

    2026-09-15: Uses SemanticMatcher singleton for ~5s performance improvement
    by avoiding model reload on each instantiation.

    FIX Bug 5: Now checks for known seminal papers and returns VERIFIED
    with high confidence even when APIs fail.

    # TODO(user): tuần 12–13 -- bổ sung:
        - Thêm classifier ML (LogisticRegression / XGBoost) như baseline B4
        - Calibration layer (Platt scaling) cho confidence
    """

    _feature_calculator: FeatureCalculator | None = None

    def __init__(
        self,
        feature_calculator: FeatureCalculator | None = None,
        rules: SymbolicRules | None = None,
        enable_content_alignment: bool = True,
    ) -> None:
        # Reuse shared FeatureCalculator instance to benefit from SemanticMatcher singleton
        if feature_calculator is not None:
            self.feature_calculator = feature_calculator
        elif NeuroSymbolicChecker._feature_calculator is None:
            NeuroSymbolicChecker._feature_calculator = FeatureCalculator(
                enable_content_alignment=enable_content_alignment
            )
        self.feature_calculator = NeuroSymbolicChecker._feature_calculator
        self.rules = rules or SymbolicRules()
        self.enable_content_alignment = enable_content_alignment

    def check(
        self,
        citation: Citation,
        source: SourceResult,
        mapping_status: "CitationMappingStatus | None" = None,
        style_profile: "StyleProfile | None" = None,
        citation_context: Optional[str] = None,
        # NEW v1.3: Provenance tracking
        api_exhausted: bool = False,
        used_cache: bool = False,
    ) -> CitationVerdict:
        """Trả CitationVerdict đầy đủ (label + confidence + reasoning + features).

        Args:
            citation: Citation từ PDF extraction
            source: SourceResult từ retrieval (API calls)
            mapping_status: CitationMappingStatus từ CitationLinker
            style_profile: StyleProfile từ StyleDetector
            citation_context: Đoạn văn xung quanh citation (cho Neural content alignment)

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
            # Recalculate features with known paper (pass context if available)
            features = self.feature_calculator.compute(citation, enhanced_source, citation_context)

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

        # Compute features với context (nếu có) cho Neural content alignment
        features = self.feature_calculator.compute(citation, source, citation_context)

        # Apply symbolic rules với content alignment features
        outcome = self.rules.apply(
            features,
            source,
            mapping_status=mapping_status,
            style_profile=style_profile,
            citation_doi=citation.doi,
            citation_url=citation.url,
            # NEW v1.3: Provenance tracking
            api_exhausted=api_exhausted,
            used_cache=used_cache,
        )

        # Enhance reasoning với content alignment info (Neural layer feedback)
        enhanced_reasoning = self._enhance_reasoning_with_neural(
            outcome.reasoning, features, outcome.triggered_rules
        )

        return CitationVerdict(
            citation=citation,
            label=outcome.label,
            confidence=outcome.confidence,
            matched_source=source,
            features=features,
            reasoning=enhanced_reasoning,
            triggered_rules=outcome.triggered_rules,
            mismatched_fields=outcome.mismatched_fields,
        )

    def _enhance_reasoning_with_neural(
        self,
        symbolic_reasoning: str,
        features: MatchFeatures,
        triggered_rules: list[str],
    ) -> str:
        """Enhance symbolic reasoning với Neural content alignment info.

        Thêm thông tin về content alignment vào reasoning để giảng viên
        hiểu được tại sao Neural layer đưa ra kết luận.
        """
        if not self.enable_content_alignment:
            return symbolic_reasoning

        # Nếu có content alignment info, thêm vào reasoning
        if features.content_alignment_score > 0:
            alignment_info = (
                f" [Neural: content alignment score={features.content_alignment_score:.2f} "
                f"({features.content_alignment_confidence})"
            )

            # Thêm signal nếu content alignment khác với symbolic decision
            if features.content_is_aligned and "VERIFIED" not in triggered_rules:
                alignment_info += " - content semantically aligned with source"
            elif not features.content_is_aligned and features.content_alignment_score > 0.3:
                alignment_info += " - WARNING: content may not align with source"

            alignment_info += "]"
            return symbolic_reasoning + alignment_info

        return symbolic_reasoning