"""SymbolicRules — decision table cho 4 nhãn (đề cương §5.6).

Mỗi rule là 1 hàm check điều kiện → trả ValidationLabel + reasoning + triggered_rules.

# TODO(user): tuần 12 — tinh chỉnh thresholds từ validation set.
"""

from __future__ import annotations

from dataclasses import dataclass

from integrity_checker.config import get_settings
from integrity_checker.models.source import SourceResult
from integrity_checker.models.validation import MatchFeatures, ValidationLabel


@dataclass
class RuleOutcome:
    label: ValidationLabel
    confidence: float            # 0.0–1.0
    reasoning: str
    triggered_rules: list[str]
    mismatched_fields: list[str]  # chỉ dùng cho METADATA_ERROR


class SymbolicRules:
    """Apply symbolic rules trên (MatchFeatures, SourceResult) → RuleOutcome."""

    def __init__(self) -> None:
        s = get_settings()
        self.title_sim_verified = s.matching.title_sim_verified
        self.title_sim_metadata_error = s.matching.title_sim_metadata_error
        self.author_jaccard_verified = s.matching.author_jaccard_verified
        self.year_tolerance = s.matching.year_tolerance
        self.abstention_low = s.logic.abstention_low
        self.abstention_high = s.logic.abstention_high
        self.consensus_verified = s.logic.require_consensus_for_verified
        self.consensus_metadata_error = s.logic.require_consensus_for_metadata_error

    def apply(self, features: MatchFeatures, source: SourceResult) -> RuleOutcome:
        """Apply rules theo thứ tự ưu tiên:
            1. DOI resolve + title tốt → VERIFIED
            2. DOI resolve + title trung bình → METADATA_ERROR
            3. ≥2 nguồn đồng thuận (title + author + year) → VERIFIED
            4. Không có candidate, API 200 OK → SUSPECTED_HALLUCINATION
            5. Vùng biên / API lỗi → UNRESOLVED
        """
        # --- Rule 5 (default): không có gì để quyết định ---
        if not source.candidates or not source.best_candidate():
            # Nếu API fail → UNRESOLVED; nếu API OK mà không có gì → SUSPECTED
            if source.sources_failed and not source.sources_succeeded:
                return RuleOutcome(
                    label=ValidationLabel.UNRESOLVED,
                    confidence=0.3,
                    reasoning="Tất cả API đều fail — không đủ bằng chứng để kết luận.",
                    triggered_rules=["R-FAIL-ALL"],
                    mismatched_fields=[],
                )
            return RuleOutcome(
                label=ValidationLabel.SUSPECTED_HALLUCINATION,
                confidence=0.85,
                reasoning=(
                    "Không tìm thấy candidate nào trong 4 nguồn (Crossref/OpenAlex/"
                    "Semantic Scholar/arXiv). Có thể là nguồn bịa."
                ),
                triggered_rules=["R-NO-CANDIDATE"],
                mismatched_fields=[],
            )

        title_sim = features.title_sim_max
        consensus = features.source_consensus
        doi_match = features.doi_exact_match
        author_sim = features.author_jaccard
        year_dist = features.year_distance

        mismatched: list[str] = []

        # --- Rule 1: DOI + title + author khớp mạnh → VERIFIED ---
        if (
            doi_match
            and title_sim >= self.title_sim_verified
            and author_sim >= self.author_jaccard_verified
        ):
            return RuleOutcome(
                label=ValidationLabel.VERIFIED,
                confidence=min(0.95, 0.7 + title_sim * 0.2 + author_sim * 0.1),
                reasoning=(
                    f"DOI khớp chính xác, title similarity={title_sim:.2f}, "
                    f"author overlap={author_sim:.2f}."
                ),
                triggered_rules=["R-DOI-TITLE-AUTHOR"],
                mismatched_fields=[],
            )

        # --- Rule 2: DOI + title similarity trung bình → METADATA_ERROR ---
        if (
            doi_match
            and self.title_sim_metadata_error <= title_sim < self.title_sim_verified
        ):
            mismatched.append("title")
            if year_dist > self.year_tolerance:
                mismatched.append("year")
            if author_sim < self.author_jaccard_verified:
                mismatched.append("author")
            return RuleOutcome(
                label=ValidationLabel.METADATA_ERROR,
                confidence=0.7,
                reasoning=(
                    f"DOI resolve được nhưng title similarity chỉ {title_sim:.2f}. "
                    f"Các trường lệch: {', '.join(mismatched)}."
                ),
                triggered_rules=["R-DOI-TITLE-MISMATCH"],
                mismatched_fields=mismatched,
            )

        # --- Rule 3: ≥2 nguồn đồng thuận ---
        if consensus >= self.consensus_verified and title_sim >= self.title_sim_verified:
            if author_sim >= self.author_jaccard_verified and year_dist <= self.year_tolerance:
                return RuleOutcome(
                    label=ValidationLabel.VERIFIED,
                    confidence=0.8,
                    reasoning=f"{consensus} nguồn đồng thuận về title + author + year.",
                    triggered_rules=["R-CONSENSUS-FULL"],
                    mismatched_fields=[],
                )
            if year_dist > self.year_tolerance:
                mismatched.append("year")
            if author_sim < self.author_jaccard_verified:
                mismatched.append("author")
            return RuleOutcome(
                label=ValidationLabel.METADATA_ERROR,
                confidence=0.65,
                reasoning=(
                    f"{consensus} nguồn đồng thuận nhưng có trường lệch: "
                    f"{', '.join(mismatched)}."
                ),
                triggered_rules=["R-CONSENSUS-PARTIAL"],
                mismatched_fields=mismatched,
            )

        # --- Rule 4: Vùng biên → UNRESOLVED (abstention) ---
        if self.abstention_low <= title_sim <= self.abstention_high:
            return RuleOutcome(
                label=ValidationLabel.UNRESOLVED,
                confidence=title_sim,
                reasoning=(
                    f"Title similarity nằm vùng biên [{self.abstention_low}, "
                    f"{self.abstention_high}] — hệ thống từ chối kết luận."
                ),
                triggered_rules=["R-ABSTENTION-BORDER"],
                mismatched_fields=[],
            )

        # --- Rule fallback ---
        return RuleOutcome(
            label=ValidationLabel.SUSPECTED_HALLUCINATION,
            confidence=0.6,
            reasoning=(
                f"Có candidate nhưng title sim={title_sim:.2f}, author={author_sim:.2f}, "
                f"DOI match={doi_match}, consensus={consensus} — không đủ để xác minh."
            ),
            triggered_rules=["R-WEAK-EVIDENCE"],
            mismatched_fields=[],
        )