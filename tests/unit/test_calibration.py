"""Tests cho calibration metrics (task #34 — Sprint 2)."""

from __future__ import annotations

import math

import pytest

from integrity_checker.logic.calibration import (
    CalibrationCalculator,
    CalibrationMetrics,
    compute_brier,
    compute_calibration_metrics,
    compute_coverage_accuracy,
    compute_ece,
    find_optimal_abstention_threshold,
)


class TestComputeBrier:
    """Brier score: MSE giữa predicted prob và ground truth."""

    def test_perfect_predictions(self) -> None:
        # conf 1.0 + correct → 0 error
        brier = compute_brier([1.0, 1.0], [1, 1])
        assert brier == 0.0

    def test_worst_predictions(self) -> None:
        # conf 1.0 + incorrect (label 0) → (1.0 - 0)^2 = 1.0
        brier = compute_brier([1.0, 1.0], [0, 0])
        assert brier == 1.0

    def test_mixed(self) -> None:
        # conf 0.5 + label 1 → (0.5 - 1)^2 = 0.25
        # conf 0.5 + label 0 → (0.5 - 0)^2 = 0.25
        # mean = 0.25
        brier = compute_brier([0.5, 0.5], [1, 0])
        assert brier == pytest.approx(0.25, abs=0.001)

    def test_empty(self) -> None:
        assert compute_brier([], []) == 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_brier([0.5], [0, 1])

    def test_clip_predictions(self) -> None:
        # conf > 1.0 clipped to 1.0
        brier = compute_brier([1.5], [0])
        assert brier == 1.0  # (1.0 - 0)^2 = 1.0


class TestComputeECE:
    """Expected Calibration Error."""

    def test_perfect_calibration(self) -> None:
        # All predictions in bin [0.9, 1.0] with all correct → ECE ≈ 0
        preds = [0.95, 0.96, 0.97, 0.98]
        labels = [1, 1, 1, 1]
        ece = compute_ece(preds, labels, n_bins=10)
        assert ece == pytest.approx(0.04, abs=0.01)  # |1.0 - 0.965|

    def test_bad_calibration_high_ece(self) -> None:
        # All predictions high (conf 0.9) but all wrong (label 0)
        preds = [0.9, 0.9, 0.9, 0.9]
        labels = [0, 0, 0, 0]
        ece = compute_ece(preds, labels, n_bins=10)
        assert ece == pytest.approx(0.9, abs=0.01)  # |0.0 - 0.9|

    def test_empty(self) -> None:
        assert compute_ece([], []) == 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_ece([0.5], [0, 1])

    def test_n_bins_zero_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_ece([0.5], [0], n_bins=0)


class TestComputeCoverageAccuracy:
    """Coverage-accuracy curve."""

    def test_full_coverage(self) -> None:
        # Coverage 1.0 → use all predictions
        preds = [0.9, 0.8, 0.5]
        labels = [1, 0, 1]
        result = compute_coverage_accuracy(preds, labels, coverages=[1.0])
        assert result[1.0] == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_partial_coverage_picks_top_k(self) -> None:
        # Coverage 0.5 → top 50% by confidence
        preds = [0.9, 0.8, 0.7, 0.6]  # sorted: 0.9, 0.8, 0.7, 0.6
        labels = [1, 1, 0, 0]          # top 2: 1, 1 → accuracy 1.0
        result = compute_coverage_accuracy(preds, labels, coverages=[0.5])
        assert result[0.5] == 1.0

    def test_default_coverages(self) -> None:
        preds = [0.9, 0.8, 0.7, 0.6, 0.5]
        labels = [1, 1, 1, 0, 0]
        result = compute_coverage_accuracy(preds, labels)
        # All 5 default coverages returned
        assert set(result.keys()) == {0.5, 0.7, 0.9, 0.95, 1.0}

    def test_empty(self) -> None:
        result = compute_coverage_accuracy([], [])
        # coverages default to {0.5, 0.7, ...} all 0.0
        assert result[0.5] == 0.0

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_coverage_accuracy([0.5], [0, 1])


class TestCalibrationCalculator:
    """Main CalibrationCalculator class."""

    def test_empty_predictions(self) -> None:
        result = CalibrationCalculator.compute([])
        assert result.ece == 0.0
        assert result.brier == 0.0
        assert result.coverage == 0.0
        assert result.n_samples == 0

    def test_full_run(self) -> None:
        preds = [
            (0.95, 1), (0.85, 1), (0.75, 0), (0.65, 1),
            (0.55, 0), (0.45, 0), (0.35, 0),
        ]
        result = CalibrationCalculator.compute(preds)
        assert isinstance(result, CalibrationMetrics)
        assert result.n_samples == 7
        assert 0.0 <= result.ece <= 1.0
        assert 0.0 <= result.brier <= 1.0
        assert 0.0 <= result.coverage <= 1.0

    def test_to_dict(self) -> None:
        preds = [(0.9, 1), (0.8, 0)]
        result = CalibrationCalculator.compute(preds)
        d = result.to_dict()
        assert "ece" in d
        assert "brier" in d
        assert "coverage" in d
        assert "n_samples" in d
        assert "coverage_accuracy" in d
        assert "abstention_band" in d
        assert d["n_samples"] == 2

    def test_summary(self) -> None:
        preds = [(0.9, 1)]
        result = CalibrationCalculator.compute(preds)
        s = result.summary()
        assert "ece" in s
        assert "brier" in s
        assert "coverage" in s


class TestComputeCalibrationMetrics:
    """List-based wrapper."""

    def test_basic(self) -> None:
        preds = [0.9, 0.8, 0.5, 0.3]
        labels = [1, 1, 0, 0]
        result = compute_calibration_metrics(preds, labels)
        assert result.n_samples == 4

    def test_empty(self) -> None:
        result = compute_calibration_metrics([], [])
        assert result.n_samples == 0


class TestFindOptimalAbstentionThreshold:
    """Threshold tuner cho coverage target."""

    def test_target_80_percent(self) -> None:
        preds = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
        threshold, cov = find_optimal_abstention_threshold(preds, [0] * 10, target_coverage=0.8)
        # k = round(10 * 0.8) = 8 → threshold = sorted_preds[7] = 0.2
        assert threshold == 0.2
        # 8/10 = 0.8 have conf >= 0.2
        assert cov == 0.8

    def test_empty(self) -> None:
        threshold, cov = find_optimal_abstention_threshold([], [], target_coverage=0.8)
        assert threshold == 0.0
        assert cov == 0.0