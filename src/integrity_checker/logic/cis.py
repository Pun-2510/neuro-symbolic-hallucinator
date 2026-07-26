"""CIS — Citation Integrity Score aggregator (đề cương §5.7).

Trọng số mặc định (tổng = 1.0):
    - verified_ratio: 45%
    - metadata_accuracy: 25%
    - in_text_bib_consistency: 15%
    - format_consistency: 10%
    - identifier_validity: 5%

CIS chỉ đo trích dẫn, KHÔNG phải điểm tiểu luận.

# TODO(user): tuần 13 — tối ưu trọng số trên validation set hoặc theo rubric GVHD.
"""

from __future__ import annotations

from integrity_checker.config import get_settings
from integrity_checker.models.validation import (
    CISComponents,
    CitationIntegrityScore,
    CitationVerdict,
    ValidationLabel,
)


class CISCalculator:
    """Tính Citation Integrity Score (0–100)."""

    def __init__(self) -> None:
        s = get_settings()
        self.w = s.cis.weights

    def compute(self, verdicts: list[CitationVerdict]) -> CitationIntegrityScore:
        if not verdicts:
            return CitationIntegrityScore(
                score=0.0,
                components=CISComponents(),
                weights_used=self.w.model_dump(),
                num_citations=0,
                num_unresolved=0,
            )

        components = self._compute_components(verdicts)
        score = (
            components.verified_ratio * self.w.verified_ratio
            + components.metadata_accuracy * self.w.metadata_accuracy
            + components.in_text_bib_consistency * self.w.in_text_bib_consistency
            + components.format_consistency * self.w.format_consistency
            + components.identifier_validity * self.w.identifier_validity
        ) * 100.0

        num_unresolved = sum(1 for v in verdicts if v.label == ValidationLabel.UNRESOLVED)
        return CitationIntegrityScore(
            score=round(score, 2),
            components=components,
            weights_used=self.w.model_dump(),
            num_citations=len(verdicts),
            num_unresolved=num_unresolved,
        )

    # --- internals ---

    def _compute_components(self, verdicts: list[CitationVerdict]) -> CISComponents:
        n = len(verdicts)

        verified = sum(1 for v in verdicts if v.label == ValidationLabel.VERIFIED)
        meta_err = sum(1 for v in verdicts if v.label == ValidationLabel.METADATA_ERROR)
        halluc = sum(1 for v in verdicts if v.label == ValidationLabel.SUSPECTED_HALLUCINATION)

        # 1. Verified ratio
        verified_ratio = verified / n

        # 2. Metadata accuracy = 1 - (METADATA_ERROR + SUSPECTED) / n
        metadata_accuracy = max(0.0, 1.0 - (meta_err + halluc) / n)

        # 3. In-text ↔ bib consistency (stub): tỉ lệ in-text có match trong bib
        # TODO(user): thật sự thì cần map citation in-text ↔ reference list entry
        in_text_bib_consistency = 0.8 if n > 0 else 0.0  # placeholder

        # 4. Format consistency (stub): hiện tại coi như OK
        format_consistency = 0.85 if n > 0 else 0.0  # placeholder

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