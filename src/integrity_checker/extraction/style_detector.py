"""StyleDetector — phân lớp document-level citation style (v1.2 §3.5).

Mục tiêu:
    Phân loại 1 document thuộc APA-like, IEEE-like, MIXED, hoặc UNKNOWN
    dựa trên tín hiệu kết hợp từ:
        - Body in-text citations (CitationType.IN_TEXT / NUMERIC)
        - Bibliography entries (CitationType.REFERENCE_LIST) + style của entry

Features:
    - Body APA ratio: tỉ lệ in-text "(Author, Year)" trên tổng.
    - Body IEEE ratio: tỉ lệ in-text "[N]" trên tổng.
    - Bib APA ratio: tỉ lệ ReferenceListParser detect APA entries.
    - Bib IEEE ratio: tương tự IEEE.
    - Bib Vancouver, Chicago, MLA ratios.

Decision:
    - Cần >= min_occurrences_to_classify citations để classify.
    - Nếu APA ratio > 0.5 và IEEE ratio < 0.2 → APA-like.
    - Nếu IEEE ratio > 0.5 và APA ratio < 0.2 → IEEE-like.
    - Nếu cả 2 ratio đều trong [0.2, 0.5] → MIXED.
    - Nếu max ratio < unknown_threshold → UNKNOWN.

References:
    v1.2 §3.5 (style signals — body vs bibliography split)
    v1.2 §3.7 (linking styles — cần style consistency check)
    config.style_detection.* (thresholds + features)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from integrity_checker.config import Settings, StyleDetectionConfig
from integrity_checker.models.citation import Citation, CitationStyle, CitationType

logger = logging.getLogger(__name__)


@dataclass
class StyleFeatures:
    """Features trích từ body + bibliography."""

    body_total_citations: int = 0
    body_apa_like: int = 0     # count (Author, Year) hoặc Author (Year)
    body_ieee_like: int = 0    # count [N]
    body_vancouver_like: int = 0  # count (N. Author) — ít gặp
    body_other: int = 0

    bib_total_entries: int = 0
    bib_apa_style: int = 0
    bib_ieee_style: int = 0
    bib_vancouver_style: int = 0
    bib_chicago_style: int = 0
    bib_other_style: int = 0


@dataclass
class StyleProfile:
    """Output từ StyleDetector."""

    label: str                     # 'APA-like' / 'IEEE-like' / 'MIXED' / 'UNKNOWN'
    confidence: float              # 0–1
    features: StyleFeatures = field(default_factory=StyleFeatures)
    ratios: dict = field(default_factory=dict)
    explanation: str = ""


class StyleDetector:
    """Phân lớp document-level citation style."""

    def __init__(self, config: Optional[StyleDetectionConfig] = None) -> None:
        self.config = config or StyleDetectionConfig()

    def detect(
        self,
        body_citations: list[Citation],
        bib_citations: list[Citation],
    ) -> StyleProfile:
        """Classify style dựa trên body citations + bibliography entries.

        Args:
            body_citations: Citation[] trích từ body (IN_TEXT / NUMERIC).
            bib_citations: Citation[] trích từ bibliography (REFERENCE_LIST).
        """
        features = self._extract_features(body_citations, bib_citations)
        ratios = self._compute_ratios(features)

        label, confidence, explanation = self._classify(ratios, features)

        return StyleProfile(
            label=label,
            confidence=confidence,
            features=features,
            ratios=ratios,
            explanation=explanation,
        )

    # -- internals --

    def _extract_features(
        self,
        body_citations: list[Citation],
        bib_citations: list[Citation],
    ) -> StyleFeatures:
        f = StyleFeatures()

        apa_re = re.compile(self.config.features.apa_author_year_pattern)
        ieee_re = re.compile(self.config.features.ieee_numeric_pattern)

        # Body signals
        for c in body_citations:
            f.body_total_citations += 1
            if ieee_re.search(c.raw_text):
                f.body_ieee_like += 1
            elif apa_re.search(c.raw_text):
                f.body_apa_like += 1
            elif re.search(r"^\s*\d+\.\s+[A-Z]", c.raw_text):
                f.body_vancouver_like += 1
            else:
                f.body_other += 1

        # Bib signals (dùng Citation.style đã được ReferenceListParser set)
        for c in bib_citations:
            f.bib_total_entries += 1
            if c.style == CitationStyle.APA:
                f.bib_apa_style += 1
            elif c.style == CitationStyle.IEEE:
                f.bib_ieee_style += 1
            elif c.style == CitationStyle.VANCOUVER:
                f.bib_vancouver_style += 1
            elif c.style == CitationStyle.CHICAGO:
                f.bib_chicago_style += 1
            else:
                f.bib_other_style += 1

        return f

    def _compute_ratios(self, f: StyleFeatures) -> dict[str, float]:
        """Tính tỉ lệ % APA-like / IEEE-like / khác từ body + bib.

        Nếu 1 trong 2 (body hoặc bib) rỗng → dùng cái còn lại thay vì chia cho 0.
        """
        ratios: dict[str, float] = {}

        # Body ratios
        body_total = f.body_total_citations
        if body_total > 0:
            ratios["body_apa"] = f.body_apa_like / body_total
            ratios["body_ieee"] = f.body_ieee_like / body_total
            ratios["body_other"] = f.body_other / body_total
        else:
            ratios["body_apa"] = 0.0
            ratios["body_ieee"] = 0.0
            ratios["body_other"] = 0.0

        # Bib ratios
        bib_total = f.bib_total_entries
        if bib_total > 0:
            ratios["bib_apa"] = f.bib_apa_style / bib_total
            ratios["bib_ieee"] = f.bib_ieee_style / bib_total
            ratios["bib_vancouver"] = f.bib_vancouver_style / bib_total
            ratios["bib_chicago"] = f.bib_chicago_style / bib_total
            ratios["bib_other"] = f.bib_other_style / bib_total
        else:
            ratios["bib_apa"] = 0.0
            ratios["bib_ieee"] = 0.0
            ratios["bib_vancouver"] = 0.0
            ratios["bib_chicago"] = 0.0
            ratios["bib_other"] = 0.0

        # Combined score (weight body + bib equally).
        # Nếu bib rỗng → dùng body only (không nhân 0.5).
        if bib_total == 0:
            ratios["apa_combined"] = ratios["body_apa"]
            ratios["ieee_combined"] = ratios["body_ieee"]
        elif body_total == 0:
            ratios["apa_combined"] = ratios["bib_apa"]
            ratios["ieee_combined"] = ratios["bib_ieee"]
        else:
            ratios["apa_combined"] = (ratios["body_apa"] + ratios["bib_apa"]) / 2
            ratios["ieee_combined"] = (ratios["body_ieee"] + ratios["bib_ieee"]) / 2
        return ratios

    def _classify(
        self, ratios: dict[str, float], f: StyleFeatures
    ) -> tuple[str, float, str]:
        apa = ratios.get("apa_combined", 0)
        ieee = ratios.get("ieee_combined", 0)
        max_score = max(apa, ieee)
        min_total = self.config.min_occurrences_to_classify

        # Quá ít tín hiệu → UNKNOWN
        total_signals = f.body_total_citations + f.bib_total_entries
        if total_signals < min_total or max_score < self.config.unknown_threshold:
            return (
                "UNKNOWN",
                float(max_score),
                f"Only {total_signals} signals (< {min_total}); "
                f"max score={max_score:.2f} < unknown threshold",
            )

        # MIXED: cả 2 đều đáng kể
        if (
            apa > self.config.mixed_threshold
            and ieee > self.config.mixed_threshold
        ):
            return (
                "MIXED",
                float(max_score),
                f"Both APA={apa:.2f} and IEEE={ieee:.2f} > "
                f"{self.config.mixed_threshold}",
            )

        # APA-like
        if apa > ieee and apa > 0.5:
            confidence = min(1.0, apa + 0.1 * f.bib_total_entries / max(f.bib_total_entries, 1))
            return (
                "APA-like",
                float(confidence),
                f"APA score={apa:.2f} dominates IEEE={ieee:.2f}",
            )

        # IEEE-like
        if ieee > apa and ieee > 0.5:
            confidence = min(1.0, ieee + 0.1 * f.bib_total_entries / max(f.bib_total_entries, 1))
            return (
                "IEEE-like",
                float(confidence),
                f"IEEE score={ieee:.2f} dominates APA={apa:.2f}",
            )

        return (
            "UNKNOWN",
            float(max_score),
            f"APA={apa:.2f}, IEEE={ieee:.2f}; no clear winner",
        )