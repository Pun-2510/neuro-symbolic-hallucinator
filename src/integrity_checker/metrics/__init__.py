"""metrics/ — Evaluation metrics (v1.2 §3.3, §4.4).

Modules:
    iaa_calculator.py — Cohen's kappa + Krippendorff's alpha for IAA measurement.
    calibration.py — ECE, Brier score, coverage-accuracy curve.
"""

from integrity_checker.metrics.iaa_calculator import (
    compute_iaa,
    cohen_kappa,
    cohen_kappa_per_label,
    krippendorffs_alpha,
)

__all__ = [
    "compute_iaa",
    "cohen_kappa",
    "cohen_kappa_per_label",
    "krippendorffs_alpha",
]
