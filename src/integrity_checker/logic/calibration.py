"""Calibration — đo ECE, Brier, coverage-accuracy cho confidence.

# TODO(user): tuần 16 — implement:
    - ECE: Expected Calibration Error
    - Brier score: trung bình bình phương sai số giữa confidence và outcome
    - Reliability diagram (matplotlib) — optional
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class CalibrationMetrics:
    ece: float                  # Expected Calibration Error
    brier: float                # Brier score
    coverage: float             # tỉ lệ verdict ≠ UNRESOLVED
    num_buckets: int = 10

    def summary(self) -> dict[str, float]:
        return {
            "ece": self.ece,
            "brier": self.brier,
            "coverage": self.coverage,
        }


class CalibrationCalculator:
    """Tính calibration metrics từ danh sách verdict + ground-truth labels."""

    @staticmethod
    def compute(
        predictions: list[tuple[float, int]],  # (confidence, is_correct)
        num_buckets: int = 10,
    ) -> CalibrationMetrics:
        """`is_correct` ∈ {0, 1}."""
        if not predictions:
            return CalibrationMetrics(ece=0.0, brier=0.0, coverage=0.0, num_buckets=num_buckets)

        # ECE
        buckets: dict[int, list[tuple[float, int]]] = defaultdict(list)
        for conf, correct in predictions:
            idx = min(int(conf * num_buckets), num_buckets - 1)
            buckets[idx].append((conf, correct))

        n = len(predictions)
        ece = sum(len(b) / n * abs(sum(c for _, c in b) / len(b) - sum(c for _, c in b) / len(b) / max(1, len(b)))
                   for b in buckets.values()) if False else 0.0
        # Recompute correctly:
        ece = 0.0
        for b in buckets.values():
            avg_conf = sum(c for c, _ in b) / len(b)
            avg_acc = sum(c for _, c in b) / len(b)
            ece += (len(b) / n) * abs(avg_acc - avg_conf)

        # Brier
        brier = sum((conf - correct) ** 2 for conf, correct in predictions) / n

        # Coverage (đếm non-UNRESOLVED = confidence > abstention_low)
        coverage = sum(1 for c, _ in predictions if c >= 0.5) / n

        return CalibrationMetrics(ece=ece, brier=brier, coverage=coverage, num_buckets=num_buckets)