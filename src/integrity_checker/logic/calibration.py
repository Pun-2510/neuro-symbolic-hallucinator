"""Calibration metrics — v1.2 §2.6 (task #34).

Đo 3 metrics theo đề cương §3.10.2:
    1. **Brier score** — mean squared error giữa predicted probability +
       ground truth (0.0 = perfect, 1.0 = worst).
    2. **ECE (Expected Calibration Error)** — weighted mean of |accuracy -
       confidence| per bin. 0.0 = perfect calibration.
    3. **Coverage-accuracy curve** — accuracy tại các coverage thresholds
       (top-K% highest confidence → accuracy trên subset đó).

Use cases:
    - Đánh giá SymbolicRules sau khi deploy.
    - Tune abstention band (lower bound = "too uncertain to decide").
    - So sánh với baselines B0-B5.

API:
    - ``compute_brier(predictions, ground_truth) -> float``
    - ``compute_ece(predictions, ground_truth, *, n_bins=10) -> float``
    - ``compute_coverage_accuracy(predictions, ground_truth, *,
        coverages=[0.5, 0.7, 0.9, 0.95, 1.0]) -> dict[float, float]``
    - ``CalibrationReport.to_dict()`` — serialize cho JSON output.

v1.2 §2.6 — Sprint 2.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Sequence


def compute_brier(
    predictions: Sequence[float],
    ground_truth: Sequence[int],
) -> float:
    """Brier score: mean squared error giữa predicted prob + ground truth.

    Args:
        predictions: list of predicted probabilities (0.0–1.0).
        ground_truth: list of 0/1 labels.

    Returns:
        Brier score (0.0 = perfect, 1.0 = worst possible).

    Raises:
        ValueError: nếu 2 lists khác length.
    """
    if len(predictions) != len(ground_truth):
        raise ValueError(
            f"predictions ({len(predictions)}) and ground_truth "
            f"({len(ground_truth)}) must have same length"
        )
    if not predictions:
        return 0.0
    n = len(predictions)
    s = 0.0
    for p, y in zip(predictions, ground_truth):
        p_clamped = max(0.0, min(1.0, p))
        s += (p_clamped - y) ** 2
    return s / n


def compute_ece(
    predictions: Sequence[float],
    ground_truth: Sequence[int],
    *,
    n_bins: int = 10,
) -> float:
    """Expected Calibration Error.

    Chia predictions thành ``n_bins`` equal-width bins [0, 1/n_bins), [1/n_bins, 2/n_bins), ...
    Tính accuracy và mean confidence trong mỗi bin, weighted theo số samples.

    Args:
        predictions: list of predicted probabilities.
        ground_truth: list of 0/1 labels.
        n_bins: số bins (default 10).

    Returns:
        ECE (0.0 = perfect calibration).
    """
    if len(predictions) != len(ground_truth):
        raise ValueError(
            f"predictions ({len(predictions)}) and ground_truth "
            f"({len(ground_truth)}) must have same length"
        )
    if not predictions:
        return 0.0
    if n_bins <= 0:
        raise ValueError(f"n_bins must be > 0, got {n_bins}")

    n = len(predictions)
    bin_sums_pred: list[float] = [0.0] * n_bins
    bin_correct: list[int] = [0] * n_bins
    bin_counts: list[int] = [0] * n_bins

    for p, y in zip(predictions, ground_truth):
        p_clamped = max(0.0, min(1.0, p))
        # Find bin (last bin includes 1.0)
        bin_idx = min(int(p_clamped * n_bins), n_bins - 1)
        bin_sums_pred[bin_idx] += p_clamped
        bin_correct[bin_idx] += int(y)
        bin_counts[bin_idx] += 1

    ece = 0.0
    for i in range(n_bins):
        if bin_counts[i] == 0:
            continue
        bin_acc = bin_correct[i] / bin_counts[i]
        bin_conf = bin_sums_pred[i] / bin_counts[i]
        ece += (bin_counts[i] / n) * abs(bin_acc - bin_conf)

    return ece


def compute_coverage_accuracy(
    predictions: Sequence[float],
    ground_truth: Sequence[int],
    *,
    coverages: Sequence[float] = (0.5, 0.7, 0.9, 0.95, 1.0),
    descending: bool = True,
) -> dict[float, float]:
    """Coverage-accuracy curve.

    Tại mỗi coverage threshold (0–1), giữ lại top-K% predictions có confidence
    cao nhất và tính accuracy trên subset đó.

    Args:
        predictions: list of predicted probabilities.
        ground_truth: list of 0/1 labels.
        coverages: list of coverage thresholds (default 50%, 70%, 90%, 95%, 100%).
        descending: True nếu sort theo confidence descending (default True).

    Returns:
        Dict mapping coverage → accuracy. Coverage = 1.0 → accuracy trên toàn bộ.
    """
    if len(predictions) != len(ground_truth):
        raise ValueError("predictions and ground_truth must have same length")
    if not predictions:
        return {c: 0.0 for c in coverages}

    paired = sorted(
        zip(predictions, ground_truth),
        key=lambda x: x[0],
        reverse=descending,
    )
    n = len(paired)
    results: dict[float, float] = {}
    for cov in coverages:
        if not 0.0 <= cov <= 1.0:
            continue
        k = max(1, int(round(n * cov)))
        subset = paired[:k]
        if not subset:
            results[cov] = 0.0
            continue
        correct = sum(int(y) for _, y in subset)
        results[cov] = correct / len(subset)
    return results


@dataclass
class CalibrationMetrics:
    """Output gộp của compute_calibration_metrics() — backward-compatible.

    v1.2 §2.6 (task #34) — extends prior stub với:
        - coverage_accuracy (dict mapping coverage thresholds → accuracy).
        - abstention_band (lowest coverage + accuracy).
    """

    ece: float = 0.0
    brier: float = 0.0
    coverage: float = 0.0           # tỉ lệ verdict ≠ UNRESOLVED
    num_buckets: int = 10
    coverage_accuracy: dict[float, float] = field(default_factory=dict)
    abstention_band: tuple[float, float] = (0.0, 0.0)
    n_samples: int = 0

    def summary(self) -> dict[str, float]:
        return {
            "ece": self.ece,
            "brier": self.brier,
            "coverage": self.coverage,
            "n_samples": self.n_samples,
        }

    def to_dict(self) -> dict:
        return {
            "ece": round(self.ece, 4),
            "brier": round(self.brier, 4),
            "coverage": round(self.coverage, 4),
            "n_samples": self.n_samples,
            "coverage_accuracy": {
                str(k): round(v, 4) for k, v in self.coverage_accuracy.items()
            },
            "abstention_band": [self.abstention_band[0], round(self.abstention_band[1], 4)],
        }


class CalibrationCalculator:
    """Tính calibration metrics từ predictions + ground-truth labels.

    v1.2 §2.6 (task #34) — full implementation, replaces prior placeholder stub.
    """

    @staticmethod
    def compute(
        predictions: list[tuple[float, int]],  # (confidence, is_correct)
        num_buckets: int = 10,
        coverages: Sequence[float] = (0.5, 0.7, 0.9, 0.95, 1.0),
        abstention_threshold: float = 0.5,
    ) -> CalibrationMetrics:
        """Compute ECE + Brier + coverage-accuracy.

        Args:
            predictions: list of (confidence, is_correct) pairs.
                is_correct ∈ {0, 1}.
            num_buckets: số bins cho ECE (default 10).
            coverages: coverage thresholds cho accuracy curve.
            abstention_threshold: threshold để tính coverage
                (default 0.5 — confidence ≥ 0.5 = non-abstained).

        Returns:
            CalibrationMetrics với ece, brier, coverage, coverage_accuracy.
        """
        if not predictions:
            return CalibrationMetrics(
                ece=0.0,
                brier=0.0,
                coverage=0.0,
                num_buckets=num_buckets,
                coverage_accuracy={c: 0.0 for c in coverages},
                n_samples=0,
            )

        # Unpack
        confs = [p[0] for p in predictions]
        labels = [p[1] for p in predictions]
        n = len(predictions)

        # ECE
        ece = compute_ece(confs, labels, n_bins=num_buckets)

        # Brier
        brier = compute_brier(confs, labels)

        # Coverage (default: confidence ≥ abstention_threshold = non-abstained)
        coverage = sum(1 for c in confs if c >= abstention_threshold) / n

        # Coverage-accuracy curve
        coverage_acc = compute_coverage_accuracy(
            confs, labels, coverages=coverages
        )

        # Abstention band (lowest coverage + accuracy)
        if coverage_acc:
            min_cov = min(coverage_acc.keys())
            abstention_acc = coverage_acc[min_cov]
        else:
            min_cov = 0.0
            abstention_acc = 0.0

        return CalibrationMetrics(
            ece=ece,
            brier=brier,
            coverage=coverage,
            num_buckets=num_buckets,
            coverage_accuracy=coverage_acc,
            abstention_band=(min_cov, abstention_acc),
            n_samples=n,
        )


# ----- Convenience: list-based API -----


def compute_calibration_metrics(
    predictions: Sequence[float],
    ground_truth: Sequence[int],
    *,
    n_bins: int = 10,
    coverages: Sequence[float] = (0.5, 0.7, 0.9, 0.95, 1.0),
) -> CalibrationMetrics:
    """List-based wrapper cho CalibrationCalculator.compute().

    Args:
        predictions: list of predicted probabilities.
        ground_truth: list of 0/1 labels.

    Returns:
        CalibrationMetrics.
    """
    pairs = list(zip(predictions, ground_truth))
    return CalibrationCalculator.compute(
        pairs,  # type: ignore[arg-type]
        num_buckets=n_bins,
        coverages=coverages,
    )


def find_optimal_abstention_threshold(
    predictions: Sequence[float],
    ground_truth: Sequence[int],
    *,
    target_coverage: float = 0.8,
) -> tuple[float, float]:
    """Find abstention threshold để đạt target_coverage.

    Tìm threshold T sao cho ≥target_coverage % predictions có confidence ≥ T.

    Args:
        predictions: list of predicted probabilities.
        ground_truth: list of 0/1 labels.
        target_coverage: target coverage (default 0.8 = 80%).

    Returns:
        Tuple (threshold, actual_coverage).
    """
    if not predictions:
        return 0.0, 0.0
    n = len(predictions)
    sorted_preds = sorted(predictions, reverse=True)
    k = max(1, int(round(n * target_coverage)))
    threshold = sorted_preds[k - 1]
    actual_cov = sum(1 for p in predictions if p >= threshold) / n
    return threshold, actual_cov