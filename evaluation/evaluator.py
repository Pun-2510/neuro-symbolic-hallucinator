"""Evaluation Metrics for Citation Integrity Checker.

Provides comprehensive evaluation metrics for hallucination detection:
- Precision, Recall, F1 (binary and multi-class)
- ROC-AUC, PR-AUC
- Confusion Matrix
- Specificity, Sensitivity
- Calibration metrics (ECE, Brier Score)
- 95% Confidence Intervals

Usage:
    from evaluation.evaluator import FakeDetectionEvaluator

    evaluator = FakeDetectionEvaluator()
    results = evaluator.evaluate(predictions, ground_truth)
    evaluator.print_report(results)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import numpy as np

# For type hints only - these are optional dependencies
try:
    from sklearn.metrics import (
        confusion_matrix as sklearn_cm,
        classification_report,
        roc_auc_score,
        precision_recall_curve,
        average_precision_score,
        cohen_kappa_score,
    )
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# For statistical tests
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BinaryMetrics:
    """Binary classification metrics."""
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def specificity(self) -> float:
        return self.tn / (self.tn + self.fp) if (self.tn + self.fp) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        total = self.tp + self.tn + self.fp + self.fn
        return (self.tp + self.tn) / total if total > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) > 0 else 0.0

    @property
    def false_negative_rate(self) -> float:
        return self.fn / (self.fn + self.tp) if (self.fn + self.tp) > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "specificity": round(self.specificity, 4),
            "f1": round(self.f1, 4),
            "accuracy": round(self.accuracy, 4),
            "fpr": round(self.false_positive_rate, 4),
            "fnr": round(self.false_negative_rate, 4),
        }


@dataclass
class ConfidenceInterval:
    """95% Confidence Interval."""
    value: float
    lower: float
    upper: float
    confidence: float = 0.95

    def __str__(self) -> str:
        return f"{self.value:.4f} [{self.lower:.4f}, {self.upper:.4f}]"


@dataclass
class CalibrationMetrics:
    """Calibration metrics for probability outputs."""
    ece: float = 0.0  # Expected Calibration Error
    mce: float = 0.0  # Maximum Calibration Error
    brier_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
            "brier_score": round(self.brier_score, 4),
        }


@dataclass
class EvaluationResult:
    """Complete evaluation results."""
    # Binary metrics (Hallucination detection: HALLUCINATED vs REAL/METAERR)
    binary: BinaryMetrics = field(default_factory=BinaryMetrics)

    # Multi-class confusion matrix
    confusion_matrix: list[list[int]] = field(default_factory=list)

    # AUC scores
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None

    # Per-class metrics
    per_class: dict = field(default_factory=dict)

    # Calibration
    calibration: CalibrationMetrics = field(default_factory=CalibrationMetrics)

    # Confidence intervals
    ci_precision: Optional[ConfidenceInterval] = None
    ci_recall: Optional[ConfidenceInterval] = None
    ci_f1: Optional[ConfidenceInterval] = None

    # Cohen's Kappa (inter-annotator agreement style)
    cohen_kappa: Optional[float] = None

    # Dataset info
    total_samples: int = 0
    samples_by_label: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = {
            "binary_metrics": self.binary.to_dict(),
            "confusion_matrix": self.confusion_matrix,
            "roc_auc": round(self.roc_auc, 4) if self.roc_auc else None,
            "pr_auc": round(self.pr_auc, 4) if self.pr_auc else None,
            "per_class": self.per_class,
            "calibration": self.calibration.to_dict(),
            "total_samples": self.total_samples,
            "samples_by_label": self.samples_by_label,
        }

        if self.ci_precision:
            result["ci_precision"] = str(self.ci_precision)
        if self.ci_recall:
            result["ci_recall"] = str(self.ci_recall)
        if self.ci_f1:
            result["ci_f1"] = str(self.ci_f1)
        if self.cohen_kappa is not None:
            result["cohen_kappa"] = round(self.cohen_kappa, 4)

        return result


# =============================================================================
# MAIN EVALUATOR CLASS
# =============================================================================

class FakeDetectionEvaluator:
    """Evaluator for Citation Integrity Checker - Fake Detection.

    Supports:
    - Binary classification: REAL vs HALLUCINATED
    - Multi-class: REAL, HALLUCINATED, METADATA_ERROR, UNRESOLVED
    - Probability calibration metrics
    - Statistical significance with confidence intervals
    """

    # Label mappings
    LABELS = ["REAL", "HALLUCINATED", "METADATA_ERROR", "UNRESOLVED"]

    # For binary classification: what counts as "positive" (fake)
    FAKE_LABELS = {"HALLUCINATED", "FABRICATED"}

    def __init__(self, confidence_level: float = 0.95):
        """
        Args:
            confidence_level: Confidence level for CI (default 0.95 for 95% CI)
        """
        self.confidence_level = confidence_level

    def load_ground_truth(self, path: str) -> dict[str, str]:
        """Load ground truth labels from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle both list and dict formats
        if isinstance(data, list):
            return {item["citation_id"]: item["ground_truth"] for item in data}
        return data

    def load_predictions(self, path: str) -> dict[str, str]:
        """Load system predictions from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return {item["citation_id"]: item["predicted_verdict"] for item in data}
        return data

    def _compute_binary_metrics(
        self,
        y_true: list[str],
        y_pred: list[str],
        y_proba: Optional[list[float]] = None,
    ) -> tuple[BinaryMetrics, list[int], list[int], list[float]]:
        """Compute binary classification metrics."""
        tp = fp = fn = tn = 0

        for true, pred in zip(y_true, y_pred):
            is_true_fake = true in self.FAKE_LABELS
            is_pred_fake = pred in self.FAKE_LABELS

            if is_true_fake and is_pred_fake:
                tp += 1
            elif not is_true_fake and is_pred_fake:
                fp += 1
            elif is_true_fake and not is_pred_fake:
                fn += 1
            else:
                tn += 1

        return BinaryMetrics(tp=tp, fp=fp, fn=fn, tn=tn), [], [], []

    def compute_confusion_matrix(
        self,
        y_true: list[str],
        y_pred: list[str],
        labels: Optional[list[str]] = None,
    ) -> tuple[list[list[int]], list[str]]:
        """Compute confusion matrix."""
        if labels is None:
            labels = self.LABELS

        n = len(labels)
        cm = [[0] * n for _ in range(n)]

        label_to_idx = {label: i for i, label in enumerate(labels)}

        for true, pred in zip(y_true, y_pred):
            if true in label_to_idx and pred in label_to_idx:
                cm[label_to_idx[true]][label_to_idx[pred]] += 1

        return cm, labels

    def compute_binomial_ci(
        self,
        n_success: int,
        n_total: int,
        confidence: float = 0.95,
    ) -> ConfidenceInterval:
        """Compute confidence interval using Wilson score interval."""
        if n_total == 0:
            return ConfidenceInterval(0.0, 0.0, 0.0, confidence)

        z = 1.96 if confidence == 0.95 else scipy_stats.ppf((1 + confidence) / 2) if HAS_SCIPY else 1.96
        p = n_success / n_total

        denominator = 1 + z**2 / n_total
        center = (p + z**2 / (2 * n_total)) / denominator
        spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n_total)) / n_total) / denominator

        lower = max(0.0, center - spread)
        upper = min(1.0, center + spread)

        return ConfidenceInterval(
            value=round(p, 4),
            lower=round(lower, 4),
            upper=round(upper, 4),
            confidence=confidence,
        )

    def compute_calibration(
        self,
        y_true: list[str],
        y_proba: list[float],
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Compute calibration metrics (ECE, MCE, Brier Score)."""
        if len(y_true) == 0 or len(y_proba) == 0:
            return CalibrationMetrics()

        # Convert to binary
        y_binary = [1 if y in self.FAKE_LABELS else 0 for y in y_true]

        # Bin predictions
        bin_edges = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        mce = 0.0

        for i in range(n_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]

            # Get samples in this bin
            mask = (np.array(y_proba) >= lower) & (np.array(y_proba) < upper)
            if upper == 1.0:
                mask = (np.array(y_proba) >= lower) & (np.array(y_proba) <= upper)

            if mask.sum() == 0:
                continue

            bin_acc = np.mean([y_binary[j] for j in range(len(y_binary)) if mask[j]])
            bin_conf = (lower + upper) / 2
            bin_size = mask.sum()

            ece += abs(bin_acc - bin_conf) * (bin_size / len(y_true))
            mce = max(mce, abs(bin_acc - bin_conf))

        # Brier Score
        brier = np.mean([(y_proba[i] - y_binary[i]) ** 2 for i in range(len(y_true))])

        return CalibrationMetrics(
            ece=round(ece, 4),
            mce=round(mce, 4),
            brier_score=round(brier, 4),
        )

    def evaluate(
        self,
        predictions: dict[str, str],
        ground_truth: dict[str, str],
        probabilities: Optional[dict[str, float]] = None,
    ) -> EvaluationResult:
        """Run full evaluation.

        Args:
            predictions: Dict of citation_id -> predicted verdict
            ground_truth: Dict of citation_id -> ground truth label
            probabilities: Optional dict of citation_id -> P(hallucinated)

        Returns:
            EvaluationResult with all metrics
        """
        # Align data
        common_ids = sorted(set(predictions.keys()) & set(ground_truth.keys()))

        if not common_ids:
            raise ValueError("No common citation IDs between predictions and ground truth")

        y_true = [ground_truth[cid] for cid in common_ids]
        y_pred = [predictions[cid] for cid in common_ids]
        y_proba = (
            [probabilities.get(cid, 0.5) for cid in common_ids]
            if probabilities
            else [0.5] * len(common_ids)
        )

        # Compute metrics
        result = EvaluationResult()
        result.total_samples = len(common_ids)

        # Count by label
        for label in self.LABELS:
            count = sum(1 for y in y_true if y == label)
            if count > 0:
                result.samples_by_label[label] = count

        # Binary metrics
        result.binary, _, _, _ = self._compute_binary_metrics(y_true, y_pred, y_proba)

        # Confusion matrix
        result.confusion_matrix, labels_used = self.compute_confusion_matrix(y_true, y_pred)

        # AUC scores (if probabilities provided)
        if probabilities and HAS_SKLEARN:
            y_true_binary = [1 if y in self.FAKE_LABELS else 0 for y in y_true]

            try:
                result.roc_auc = roc_auc_score(y_true_binary, y_proba)
            except ValueError:
                pass

            try:
                result.pr_auc = average_precision_score(y_true_binary, y_proba)
            except ValueError:
                pass

        # Calibration
        if probabilities:
            result.calibration = self.compute_calibration(y_true, y_proba)

        # Per-class metrics
        result.per_class = self._compute_per_class_metrics(y_true, y_pred, labels_used)

        # Confidence intervals
        if HAS_SCIPY:
            result.ci_precision = self.compute_binomial_ci(
                result.binary.tp + result.binary.fp,  # All predicted as fake
                result.binary.tp + result.binary.fp,
                self.confidence_level,
            )

            # For recall CI: need bootstrap or Wilson for proportion
            # Using simplified approach
            n_fake = result.binary.tp + result.binary.fn
            result.ci_recall = self.compute_binomial_ci(
                result.binary.tp, n_fake, self.confidence_level
            )

        # Cohen's Kappa (treat as multi-class agreement)
        if HAS_SKLEARN:
            try:
                result.cohen_kappa = cohen_kappa_score(y_true, y_pred)
            except ValueError:
                pass

        return result

    def _compute_per_class_metrics(
        self,
        y_true: list[str],
        y_pred: list[str],
        labels: list[str],
    ) -> dict:
        """Compute per-class precision, recall, F1."""
        per_class = {}

        for label in labels:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            per_class[label] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "support": tp + fn,
            }

        return per_class

    def print_report(self, result: EvaluationResult) -> str:
        """Generate printable evaluation report."""
        lines = []

        lines.append("=" * 70)
        lines.append("CITATION INTEGRITY CHECKER - EVALUATION REPORT")
        lines.append("=" * 70)

        # Dataset info
        lines.append(f"\n📊 DATASET INFO")
        lines.append(f"   Total samples: {result.total_samples}")
        for label, count in result.samples_by_label.items():
            lines.append(f"   - {label}: {count}")

        # Binary metrics
        lines.append(f"\n🎯 BINARY CLASSIFICATION (Hallucination Detection)")
        lines.append(f"   ┌─────────────────────────────────────────────────────────┐")
        lines.append(f"   │ Metric                    │ Value    │ 95% CI            │")
        lines.append(f"   ├─────────────────────────────────────────────────────────┤")

        # Recall (most important for hallucination detection)
        recall_str = f"{result.binary.recall:.4f}"
        recall_ci = f"[{result.ci_recall.lower:.4f}, {result.ci_recall.upper:.4f}]" if result.ci_recall else "N/A"
        lines.append(f"   │ Recall (Sensitivity)     │ {recall_str}   │ {recall_ci} │")

        # Precision
        prec_str = f"{result.binary.precision:.4f}"
        lines.append(f"   │ Precision                  │ {prec_str}   │                  │")

        # Specificity
        spec_str = f"{result.binary.specificity:.4f}"
        lines.append(f"   │ Specificity                │ {spec_str}   │                  │")

        # F1
        f1_str = f"{result.binary.f1:.4f}"
        lines.append(f"   │ F1-Score                   │ {f1_str}   │                  │")

        # Accuracy
        acc_str = f"{result.binary.accuracy:.4f}"
        lines.append(f"   │ Accuracy                   │ {acc_str}   │                  │")

        lines.append(f"   └─────────────────────────────────────────────────────────┘")

        # Confusion Matrix
        lines.append(f"\n📋 CONFUSION MATRIX")
        labels = ["REAL", "HALLU", "METAERR", "UNRES"]
        header = "            " + "  ".join(f"{l:>8}" for l in labels)
        lines.append(f"            " + "-" * len(header))
        lines.append(header)

        for i, row in enumerate(result.confusion_matrix):
            row_str = "  ".join(f"{v:>8}" for v in row)
            lines.append(f"   {labels[i]:>8} │ {row_str}")

        # Per-class metrics
        lines.append(f"\n📈 PER-CLASS METRICS")
        lines.append(f"   ┌────────────────────────────────────────────────────────┐")
        lines.append(f"   │ Class           │ Precision │ Recall │ F1    │ Support │")
        lines.append(f"   ├────────────────────────────────────────────────────────┤")

        for label, metrics in result.per_class.items():
            label_display = label[:13].ljust(13)
            lines.append(
                f"   │ {label_display} │ "
                f"{metrics['precision']:.4f}   │ "
                f"{metrics['recall']:.4f}   │ "
                f"{metrics['f1']:.4f} │ "
                f"{metrics['support']:>6} │"
            )

        lines.append(f"   └────────────────────────────────────────────────────────┘")

        # AUC scores
        if result.roc_auc is not None or result.pr_auc is not None:
            lines.append(f"\n📉 AUC SCORES")
            if result.roc_auc is not None:
                lines.append(f"   ROC-AUC: {result.roc_auc:.4f}")
            if result.pr_auc is not None:
                lines.append(f"   PR-AUC:  {result.pr_auc:.4f}")

        # Calibration
        if result.calibration:
            lines.append(f"\n🎚️ CALIBRATION (ECE)")
            lines.append(f"   ECE: {result.calibration.ece:.4f}")
            lines.append(f"   (Lower is better, < 0.05 is good)")

        # Cohen's Kappa
        if result.cohen_kappa is not None:
            lines.append(f"\n🔄 INTER-RATER AGREEMENT")
            lines.append(f"   Cohen's Kappa: {result.cohen_kappa:.4f}")
            if result.cohen_kappa >= 0.8:
                lines.append(f"   Interpretation: Almost Perfect")
            elif result.cohen_kappa >= 0.6:
                lines.append(f"   Interpretation: Substantial")
            elif result.cohen_kappa >= 0.4:
                lines.append(f"   Interpretation: Moderate")
            else:
                lines.append(f"   Interpretation: Poor")

        # Error analysis
        lines.append(f"\n⚠️ ERROR BREAKDOWN")
        lines.append(f"   False Positives (wrongly flagged as fake): {result.binary.fp}")
        lines.append(f"   False Negatives (missed hallucinations):   {result.binary.fn}")

        if result.binary.fp + result.binary.tn > 0:
            fpr = result.binary.fp / (result.binary.fp + result.binary.tn)
            lines.append(f"   False Positive Rate: {fpr:.4f}")

        if result.binary.fn + result.binary.tp > 0:
            fnr = result.binary.fn / (result.binary.fn + result.binary.tp)
            lines.append(f"   False Negative Rate: {fnr:.4f}")

        lines.append("\n" + "=" * 70)

        report = "\n".join(lines)
        print(report)
        return report

    def save_report(self, result: EvaluationResult, output_path: str):
        """Save evaluation result to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_path}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def compute_mcnemar_test(
    predictions_a: list[str],
    predictions_b: list[str],
    ground_truth: list[str],
) -> dict:
    """McNemar's test to compare two systems.

    Returns p-value for whether two systems are significantly different.
    """
    if not HAS_SCIPY:
        return {"error": "scipy not installed"}

    if len(predictions_a) != len(predictions_b) or len(predictions_a) != len(ground_truth):
        raise ValueError("All lists must have same length")

    # Convert to binary: correct vs incorrect
    correct_a = [1 if p == t else 0 for p, t in zip(predictions_a, ground_truth)]
    correct_b = [1 if p == t else 0 for p, t in zip(predictions_b, ground_truth)]

    # Count discordant pairs
    b01 = sum(1 for a, b in zip(correct_a, correct_b) if a == 1 and b == 0)  # A correct, B wrong
    b10 = sum(1 for a, b in zip(correct_a, correct_b) if a == 0 and b == 1)  # A wrong, B correct

    if b01 + b10 == 0:
        return {"p_value": 1.0, "b01": b01, "b10": b10, "significant": False}

    # McNemar's chi-squared
    chi2 = (abs(b01 - b10) - 1) ** 2 / (b01 + b10) if (b01 + b10) > 0 else 0
    p_value = 1 - scipy_stats.chi2.cdf(chi2, df=1)

    return {
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 6),
        "b01": b01,
        "b10": b10,
        "significant": p_value < 0.05,
    }


def main():
    """Demo evaluation."""
    import random

    print("=" * 60)
    print("FAKE DETECTION EVALUATOR - DEMO")
    print("=" * 60)

    evaluator = FakeDetectionEvaluator()

    # Load ground truth
    gt_path = Path(__file__).parent / "ground_truth.json"
    if gt_path.exists():
        ground_truth = evaluator.load_ground_truth(str(gt_path))

        # Simulate predictions (for demo - in real use, load from system output)
        predictions = {}
        for cid, gt in ground_truth.items():
            # Simulate ~85% accuracy
            if random.random() < 0.85:
                predictions[cid] = gt
            else:
                # Random wrong prediction
                possible = [l for l in evaluator.LABELS if l != gt]
                predictions[cid] = random.choice(possible)

        # Run evaluation
        result = evaluator.evaluate(predictions, ground_truth)

        # Print report
        evaluator.print_report(result)

        # Save report
        evaluator.save_report(result, str(Path(__file__).parent / "evaluation_results.json"))
    else:
        print(f"Ground truth file not found: {gt_path}")
        print("Run synthetic_dataset.py first to generate the dataset.")


if __name__ == "__main__":
    main()
