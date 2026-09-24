"""CIS — Citation Integrity Score aggregator (đề cương §5.7).

Trọng số mặc định (tổng = 1.0):
    - verified_ratio: 35%
    - metadata_accuracy: 25%
    - in_text_bib_consistency: 25%
    - format_consistency: 10%
    - identifier_validity: 5%

CIS chỉ đo trích dẫn, KHÔNG phải điểm tiểu luận.

v1.2 §3.2.2 — Tách output 2 lớp:
    - Source verification (ValidationLabel) → verified_ratio, metadata_accuracy,
      identifier_validity.
    - Integrity mapping (CitationMappingStatus) → in_text_bib_consistency
      (tính từ CitationLinker.link()).

v1.2 §3.7 — format_consistency tính từ StyleDetector (không phải constant).

FIX Bug 6: Added debug logging to trace in_text_bib_consistency calculation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from integrity_checker.config import get_settings
from integrity_checker.models.validation import (
    CISComponents,
    CitationIntegrityScore,
    CitationVerdict,
    ValidationLabel,
)

if TYPE_CHECKING:
    from integrity_checker.linking.statuses import LinkingResult, StyleProfile

logger = logging.getLogger(__name__)


# Penalty per mapping status — cộng dồn vào "negative" bucket.
# in_text_bib_consistency = 1 - (sum_penalties / total_citations)
# FIX Bug 6: Updated penalties to match CISConfig rubric_penalty weights
MAPPING_PENALTIES: dict[str, float] = {
    "matched": 0.0,
    "missing_reference": 0.20,    # FIX: Match CISConfig rubric_penalty
    "uncited_reference": 0.10,   # FIX: Match CISConfig rubric_penalty
    "in_text_mismatch": 0.15,   # FIX: Match CISConfig rubric_penalty
    "duplicate_reference": 0.10, # FIX: Match CISConfig rubric_penalty
    "ambiguous_mapping": 0.05,   # FIX: Match CISConfig rubric_penalty
    "style_inconsistent": 0.02, # FIX: Match CISConfig rubric_penalty
}


class CISCalculator:
    """Tính Citation Integrity Score (0–100).

    v1.2 tuần 9 (task #28): CIS components KHÔNG còn là constants. Real inputs:
        - ``verdicts``: từ NeuroSymbolicChecker.check() + CitationLinker.link().
        - ``linking_result``: từ CitationLinker.link() (optional, for
          in_text_bib_consistency calculation).
        - ``style_profile``: từ StyleDetector.detect() (optional, for
          format_consistency calculation).
    """

    def __init__(self) -> None:
        s = get_settings()
        self.w = s.cis.weights

    def compute(
        self,
        verdicts: list[CitationVerdict],
        linking_result: "LinkingResult | None" = None,
        style_profile: "StyleProfile | None" = None,
    ) -> CitationIntegrityScore:
        if not verdicts:
            return CitationIntegrityScore(
                score=0.0,
                components=CISComponents(),
                weights_used=self.w.model_dump(),
                num_citations=0,
                num_unresolved=0,
            )

        components = self._compute_components(
            verdicts,
            linking_result=linking_result,
            style_profile=style_profile,
        )
        score = (
            components.verified_ratio * self.w.verified_ratio
            + components.metadata_accuracy * self.w.metadata_accuracy
            + components.in_text_bib_consistency * self.w.in_text_bib_consistency
            + components.format_consistency * self.w.format_consistency
            + components.identifier_validity * self.w.identifier_validity
        ) * 100.0

        num_unresolved = sum(1 for v in verdicts if v.label in (ValidationLabel.UNRESOLVED, ValidationLabel.RESOURCE))
        num_citations = len(verdicts)
        num_academic = sum(1 for v in verdicts if v.label != ValidationLabel.RESOURCE)
        return CitationIntegrityScore(
            score=round(score, 2),
            components=components,
            weights_used=self.w.model_dump(),
            num_citations=num_citations,
            num_unresolved=num_unresolved,
        )

    # --- internals ---

    def _compute_components(
        self,
        verdicts: list[CitationVerdict],
        linking_result: "LinkingResult | None" = None,
        style_profile: "StyleProfile | None" = None,
    ) -> CISComponents:
        n = len(verdicts)

        verified = sum(1 for v in verdicts if v.label == ValidationLabel.VERIFIED)
        meta_err = sum(1 for v in verdicts if v.label == ValidationLabel.METADATA_ERROR)
        halluc = sum(1 for v in verdicts if v.label == ValidationLabel.SUSPECTED_HALLUCINATION)

        # Filter out RESOURCE (URLs/References) from academic citation stats
        academic_verdicts = [v for v in verdicts if v.label != ValidationLabel.RESOURCE]
        n_academic = len(academic_verdicts)

        # 1. Verified ratio — tỉ lệ academic citations được verify
        verified_ratio = verified / n_academic if n_academic > 0 else 0.0

        # 2. Metadata accuracy = 1 - (METADATA_ERROR + SUSPECTED) / academic citations
        metadata_accuracy = max(0.0, 1.0 - (meta_err + halluc) / n_academic) if n_academic > 0 else 0.0

        # 3. In-text ↔ bib consistency — TÍNH TỪ CitationLinker (không còn stub)
        # 2 strategies (ưu tiên linking_result nếu có):
        #   a. Từ LinkingResult.links (nếu pipeline có chạy CitationLinker)
        #   b. Từ verdict.mapping_status (fallback nếu linker không chạy)
        in_text_bib_consistency = self._compute_link_consistency(
            verdicts, linking_result
        )

        # 4. Format consistency — TÍNH TỪ StyleDetector
        # Style profile có style (APA-LIKE / IEEE-LIKE / MIXED / UNKNOWN)
        # MIXED = penalty; UNKNOWN = neutral; rõ ràng = high score.
        format_consistency = self._compute_format_consistency(
            style_profile, verdicts
        )

        # 5. Identifier validity: tỉ lệ DOI/URL có resolve được
        with_doi = sum(1 for v in verdicts if v.citation.doi)
        with_doi_valid = sum(
            1
            for v in verdicts
            if v.citation.doi and v.label in (ValidationLabel.VERIFIED, ValidationLabel.METADATA_ERROR)
        )
        identifier_validity = (with_doi_valid / with_doi) if with_doi > 0 else 1.0

        return CISComponents(
            verified_ratio=verified_ratio,
            metadata_accuracy=metadata_accuracy,
            in_text_bib_consistency=in_text_bib_consistency,
            format_consistency=format_consistency,
            identifier_validity=identifier_validity,
        )

    @staticmethod
    def _compute_link_consistency(
        verdicts: list[CitationVerdict],
        linking_result: "LinkingResult | None" = None,
    ) -> float:
        """Tính in_text_bib_consistency từ CitationLinker output.

        FIX Bug 6: Added debug logging to trace calculation.
        """
        # DEBUG: Log input state
        logger.debug(
            f"CIS link consistency: verdicts={len(verdicts)}, "
            f"linking_result={'present' if linking_result else 'None'}"
        )

        # Strategy A: LinkingResult có sẵn
        if linking_result is not None and linking_result.links:
            total = len(linking_result.links)
            penalty = 0.0
            status_counts: dict[str, int] = {}
            for link in linking_result.links:
                status = (
                    link.status.value
                    if hasattr(link.status, "value")
                    else str(link.status)
                )
                status_counts[status] = status_counts.get(status, 0) + 1
                penalty += MAPPING_PENALTIES.get(status, 0.0)

            logger.debug(f"CIS from links: status_counts={status_counts}, penalty={penalty:.2f}, total={total}")
            result = max(0.0, 1.0 - penalty / total) if total > 0 else 1.0
            logger.debug(f"CIS link consistency result: {result:.4f}")
            return result

        # Strategy B: verdict-level (fallback khi không có linking_result)
        n = len(verdicts)
        if n == 0:
            logger.debug("CIS: no verdicts, returning 1.0")
            return 1.0

        status_counts: dict[str, int] = {}
        for v in verdicts:
            if v.mapping_status is None:
                continue
            status = (
                v.mapping_status.value
                if hasattr(v.mapping_status, "value")
                else str(v.mapping_status)
            )
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.debug(f"CIS from verdicts: status_counts={status_counts}")

        penalty = 0.0
        for status, count in status_counts.items():
            p = MAPPING_PENALTIES.get(status, 0.0)
            logger.debug(f"  {status}: count={count}, penalty={p:.2f}, total_contrib={p * count:.2f}")
            penalty += p * count

        result = max(0.0, 1.0 - penalty / n) if n > 0 else 1.0
        logger.debug(f"CIS link consistency result: {result:.4f} (penalty={penalty:.2f}, n={n})")
        return result

    @staticmethod
    def _compute_format_consistency(
        style_profile: "StyleProfile | None" = None,
        verdicts: list[CitationVerdict] | None = None,
    ) -> float:
        """Tính format_consistency từ StyleDetector output.

        Logic:
            - StyleProfile.style rõ ràng (APA-LIKE / IEEE-LIKE) + confidence cao → score cao.
            - MIXED → penalty (essay dùng nhiều style).
            - UNKNOWN / None → neutral (0.5 — conservative default).
            - StyleDetector chưa chạy → dùng STYLE_INCONSISTENT mapping penalty trên verdict.
        """
        if style_profile is not None:
            style_value = (style_profile.style or "").upper()
            confidence = style_profile.confidence

            if "MIXED" in style_value:
                # MIXED = essay dùng nhiều style → penalty
                base = 0.4
            elif "UNKNOWN" in style_value:
                base = 0.5
            elif "APA" in style_value or "IEEE" in style_value:
                # Rõ ràng → score cao scaled by confidence
                base = 0.8 + 0.2 * confidence  # 0.8-1.0
            else:
                base = 0.5

            # Penalty nếu style_profile có STYLE_INCONSISTENT signals
            evidence = getattr(style_profile, "evidence", {}) or {}
            if evidence.get("style_inconsistent"):
                base = max(0.2, base - 0.2)

            return min(1.0, max(0.0, base))

        # Fallback: từ verdict mapping STYLE_INCONSISTENT count
        if verdicts:
            n = len(verdicts)
            inconsistent = sum(
                1
                for v in verdicts
                if v.mapping_status is not None
                and hasattr(v.mapping_status, "value")
                and v.mapping_status.value == "style_inconsistent"
            )
            if inconsistent > 0:
                return max(0.3, 1.0 - inconsistent / n)
            return 0.8  # Default — không penalty

        return 0.5  # Conservative default