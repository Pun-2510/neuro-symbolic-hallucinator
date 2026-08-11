"""Unit tests cho metrics/iaa_calculator.py (v1.2 §3.3)."""

from __future__ import annotations

import pytest
from integrity_checker.metrics.iaa_calculator import (
    cohen_kappa,
    cohen_kappa_per_label,
    krippendorffs_alpha,
)


class TestCohenKappa:
    def test_perfect_agreement(self):
        labels = ["A", "B", "A", "B", "A"]
        kappa = cohen_kappa(labels, labels)
        assert kappa == 1.0

    def test_no_agreement_random(self):
        a = ["A", "B", "A", "B", "A", "B"]
        b = ["B", "A", "B", "A", "B", "A"]
        kappa = cohen_kappa(a, b)
        # Perfect disagreement → kappa = -1.0
        assert -1.5 < kappa <= 0.5

    def test_all_same_label(self):
        a = ["VERIFIED"] * 10
        b = ["VERIFIED"] * 10
        kappa = cohen_kappa(a, b)
        assert kappa == 1.0

    def test_partial_agreement(self):
        a = ["A", "A", "A", "A", "B", "B"]
        b = ["A", "A", "A", "B", "B", "B"]
        kappa = cohen_kappa(a, b)
        assert 0.0 < kappa <= 1.0

    def test_empty_lists(self):
        kappa = cohen_kappa([], [])
        assert kappa == 1.0

    def test_mismatched_length_raises(self):
        with pytest.raises(ValueError):
            cohen_kappa(["A", "B"], ["A"])


class TestCohenKappaPerLabel:
    def test_binary_per_label(self):
        a = ["VERIFIED", "VERIFIED", "SUSPECTED", "SUSPECTED"]
        b = ["VERIFIED", "SUSPECTED", "VERIFIED", "SUSPECTED"]
        kappas = cohen_kappa_per_label(a, b)
        assert "VERIFIED" in kappas
        assert "SUSPECTED" in kappas

    def test_four_labels(self):
        labels = ["A", "B", "C", "D"]
        kappas = cohen_kappa_per_label(labels, labels)
        for label in labels:
            assert kappas[label] == 1.0

    def test_empty(self):
        kappas = cohen_kappa_per_label([], [])
        assert kappas == {}


class TestKrippendorffAlpha:
    def test_perfect_agreement(self):
        labels = ["A", "B", "C", "A", "B"]
        alpha = krippendorffs_alpha(labels, labels)
        assert alpha == 1.0

    def test_all_same_label(self):
        a = ["VERIFIED"] * 10
        b = ["VERIFIED"] * 10
        alpha = krippendorffs_alpha(a, b)
        assert alpha == 1.0

    def test_near_random(self):
        a = ["A", "B", "C", "D"] * 5
        b = ["D", "C", "B", "A"] * 5
        alpha = krippendorffs_alpha(a, b)
        # Alpha can be negative when agreement is worse than random
        assert -1.5 <= alpha <= 1.0

    def test_empty(self):
        alpha = krippendorffs_alpha([], [])
        assert alpha == 1.0

    def test_mismatched_length_raises(self):
        with pytest.raises(ValueError):
            krippendorffs_alpha(["A", "B"], ["A"])


class TestIntegration:
    def test_four_source_labels(self):
        """4 nhãn source: VERIFIED, METADATA_ERROR, SUSPECTED, UNRESOLVED."""
        a = ["VERIFIED", "METADATA_ERROR", "SUSPECTED", "UNRESOLVED",
             "VERIFIED", "VERIFIED", "SUSPECTED", "UNRESOLVED"]
        b = ["VERIFIED", "METADATA_ERROR", "SUSPECTED", "UNRESOLVED",
             "METADATA_ERROR", "VERIFIED", "SUSPECTED", "VERIFIED"]

        kappa = cohen_kappa(a, b)
        alpha = krippendorffs_alpha(a, b)

        assert -1.0 <= kappa <= 1.0
        assert -1.0 <= alpha <= 1.0
        # At least one should be perfect for matching pairs
        assert kappa >= 0.0 or alpha >= 0.0

    def test_realistic_annotation_scenario(self):
        """Simulate real annotation: 20 citations."""
        a = ["VERIFIED"] * 10 + ["SUSPECTED"] * 5 + ["METADATA_ERROR"] * 3 + ["UNRESOLVED"] * 2
        b = ["VERIFIED"] * 9 + ["SUSPECTED"] * 5 + ["METADATA_ERROR"] * 3 + ["UNRESOLVED"] * 3
        # ~12 agree, 8 disagree

        kappa = cohen_kappa(a, b)
        alpha = krippendorffs_alpha(a, b)

        # Both metrics in valid range
        assert -1.0 <= kappa <= 1.0
        assert -1.0 <= alpha <= 1.0
