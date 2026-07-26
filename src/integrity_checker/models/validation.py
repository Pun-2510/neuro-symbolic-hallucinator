"""Validation models — output của logic module (Neuro-Symbolic checker)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceResult


class ValidationLabel(str, Enum):
    """Taxonomy 4 nhãn — đề cương §5.2.

    BẮT BUỘC dùng đúng các giá trị này (lowercase) để serialize/UI.
    """

    VERIFIED = "verified"
    METADATA_ERROR = "metadata_error"
    SUSPECTED_HALLUCINATION = "suspected_hallucination"
    UNRESOLVED = "unresolved"

    @property
    def color(self) -> str:
        """Màu badge trên UI (hex)."""
        return {
            ValidationLabel.VERIFIED: "#16a34a",               # xanh
            ValidationLabel.METADATA_ERROR: "#ca8a04",         # vàng
            ValidationLabel.SUSPECTED_HALLUCINATION: "#dc2626",  # đỏ
            ValidationLabel.UNRESOLVED: "#6b7280",             # xám
        }[self]


@dataclass
class MatchFeatures:
    """Vector features so khớp giữa citation và candidate tốt nhất.

    Mọi score đều 0.0–1.0 (trừ `year_distance` là int).
    """

    title_sim_fuzzy: float = 0.0       # RapidFuzz token_set_ratio / 100
    title_sim_semantic: float = 0.0    # cosine similarity sentence-transformers
    author_jaccard: float = 0.0        # |A ∩ B| / |A ∪ B| trên last-name
    year_distance: int = 999           # |cited.year - candidate.year|
    doi_exact_match: bool = False      # True nếu DOI khớp 100%
    source_consensus: int = 0          # số nguồn đồng thuận (≥1)

    @property
    def title_sim_max(self) -> float:
        """Lấy max(fuzzy, semantic) — dùng cho rules."""
        return max(self.title_sim_fuzzy, self.title_sim_semantic)


@dataclass
class CitationVerdict:
    """Quyết định cuối cùng cho 1 citation — output chính của pipeline."""

    citation: Citation
    label: ValidationLabel
    confidence: float                  # 0.0–1.0, dùng cho calibration + CIS

    # Bằng chứng
    matched_source: Optional[SourceResult] = None
    features: MatchFeatures = field(default_factory=MatchFeatures)

    # Giải thích cho giảng viên
    reasoning: str = ""
    triggered_rules: list[str] = field(default_factory=list)
    mismatched_fields: list[str] = field(default_factory=list)  # nếu METADATA_ERROR

    # Audit (override của giảng viên)
    is_overridden: bool = False
    overridden_label: Optional[ValidationLabel] = None
    overridden_by: Optional[str] = None  # user id / lecturer email
    override_note: Optional[str] = None


@dataclass
class CISComponents:
    """5 thành phần của Citation Integrity Score (đề cương §5.7)."""

    verified_ratio: float = 0.0          # 0–1
    metadata_accuracy: float = 0.0       # 0–1
    in_text_bib_consistency: float = 0.0  # 0–1
    format_consistency: float = 0.0       # 0–1
    identifier_validity: float = 0.0      # 0–1

    def to_dict(self) -> dict[str, float]:
        return {
            "verified_ratio": self.verified_ratio,
            "metadata_accuracy": self.metadata_accuracy,
            "in_text_bib_consistency": self.in_text_bib_consistency,
            "format_consistency": self.format_consistency,
            "identifier_validity": self.identifier_validity,
        }


@dataclass
class CitationIntegrityScore:
    """CIS = trọng số-weighted tổng của 5 components, scale 0–100.

    Lưu ý: CIS chỉ đo trích dẫn, KHÔNG phải điểm tiểu luận.
    """

    score: float  # 0–100
    components: CISComponents
    weights_used: dict[str, float]
    num_citations: int
    num_unresolved: int  # số verdict = UNRESOLVED (để minh bạch)