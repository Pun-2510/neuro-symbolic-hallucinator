"""IAA Calculator — Cohen's kappa + Krippendorff's alpha (v1.2 §3.3).

Usage:
    python -m integrity_checker.metrics.iaa_calculator \\
        data/ground_truth/iaa_results_2026-08-11.csv \\
        --output data/ground_truth/iaa_results_2026-08-11.json

Workflow:
    1. Hai SV cùng annotate 100 citations (tuần 3-5).
    2. Điền kết quả vào 2 file: iaa_annotator_A.csv, iaa_annotator_B.csv.
       Format: essay_file, citation_raw, label
    3. Script này tính Cohen's kappa (per-label) + Krippendorff's alpha (overall).
    4. Target: Cohen's kappa ≥ 0.7 AND Krippendorff's alpha ≥ 0.7.

Labels (v1.2 §3.2.1):
    VERIFIED           — nguồn tồn tại, metadata đúng
    METADATA_ERROR     — nguồn tồn tại, metadata sai
    SUSPECTED          — có vẻ fabricated/hallucinated
    UNRESOLVED         — không xác định được
    FABRICATED         — rõ ràng fabricated (bonus)
    [BLANK/EMPTY]      — không annotate được

References:
    v1.2 §3.3 (Inter-annotator agreement — Cohen's kappa + Krippendorff's alpha)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = __import__("logging").getLogger(__name__)

# Optional: krippendorff library
try:
    import krippendorff  # type: ignore

    HAS_KRIPPENDORFF = True
except ImportError:
    HAS_KRIPPENDORFF = False


def load_annotations(csv_path: str) -> dict[str, dict[str, str]]:
    """Load annotations từ CSV file.

    Returns:
        dict[citation_id, {"label": str, "essay": str, "raw": str}]
    """
    annotations: dict[str, dict[str, str]] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Build citation_id from essay + raw citation
            essay = row.get("essay_file", "").strip()
            raw = row.get("citation_raw", "").strip()
            citation_id = f"{essay}::{raw}"
            label = row.get("label", row.get("final", "")).strip().upper()
            if not label:
                label = "UNRESOLVED"
            annotations[citation_id] = {
                "essay": essay,
                "raw": raw,
                "label": label,
            }
    return annotations


def cohen_kappa(annotator_a: list[str], annotator_b: list[str]) -> float:
    """Tính Cohen's kappa cho 2 annotators.

    Args:
        annotator_a: labels từ annotator A (theo thứ tự citation)
        annotator_b: labels từ annotator B (theo thứ tự citation)

    Returns:
        kappa score (-1 to 1). Returns 1.0 nếu perfect agreement.
    """
    if len(annotator_a) != len(annotator_b):
        raise ValueError("Lists must have same length")

    n = len(annotator_a)
    if n == 0:
        return 1.0

    # Count categories
    categories: set[str] = set(annotator_a) | set(annotator_b)
    k = len(categories)

    # Agreement matrix
    agreement: dict[str, dict[str, int]] = {
        cat: {cat2: 0 for cat2 in categories} for cat in categories
    }
    for a, b in zip(annotator_a, annotator_b):
        agreement[a][b] += 1

    # Observed agreement
    observed = sum(agreement[cat][cat] for cat in categories) / n

    # Expected agreement
    col_totals: dict[str, float] = defaultdict(float)
    row_totals: dict[str, float] = defaultdict(float)
    for cat_r in categories:
        for cat_c in categories:
            col_totals[cat_c] += agreement[cat_r][cat_c]
            row_totals[cat_r] += agreement[cat_r][cat_c]
    expected = sum(
        row_totals[cat] * col_totals[cat] / n for cat in categories
    ) / n

    if expected == 1.0:
        return 1.0

    kappa = (observed - expected) / (1.0 - expected)
    return kappa


def cohen_kappa_per_label(
    annotator_a: list[str], annotator_b: list[str]
) -> dict[str, float]:
    """Tính Cohen's kappa cho từng label (binary: this label vs rest).

    Args:
        annotator_a: labels từ annotator A
        annotator_b: labels từ annotator B

    Returns:
        dict[label, kappa_score] — cho mỗi unique label.
    """
    if len(annotator_a) != len(annotator_b):
        raise ValueError("Lists must have same length")

    n = len(annotator_a)
    categories: set[str] = set(annotator_a) | set(annotator_b)
    results: dict[str, float] = {}

    for label in categories:
        # Binary: 1 = this label, 0 = other
        binary_a = [1 if l == label else 0 for l in annotator_a]
        binary_b = [1 if l == label else 0 for l in annotator_b]
        results[label] = cohen_kappa(binary_a, binary_b)

    return results


def krippendorffs_alpha(
    annotator_a: list[str], annotator_b: list[str]
) -> float:
    """Tính Krippendorff's alpha cho 2 annotators.

    Args:
        annotator_a: labels từ annotator A
        annotator_b: labels từ annotator B

    Returns:
        alpha score (-∞ to 1). 1.0 = perfect agreement.
    """
    if not HAS_KRIPPENDORFF:
        logger.warning("krippendorff library not installed. Using simplified alpha.")
        return _simplified_alpha(annotator_a, annotator_b)

    if len(annotator_a) != len(annotator_b):
        raise ValueError("Lists must have same length")

    n = len(annotator_a)
    if n == 0:
        return 1.0

    # Build data matrix: rows = annotators, cols = items
    # 0 = annotator A, 1 = annotator B
    data = [annotator_a, annotator_b]

    alpha = krippendorff.alpha(
        reliability_data=data,
        level_of_measurement="nominal",
    )
    return alpha


def _simplified_alpha(annotator_a: list[str], annotator_b: list[str]) -> float:
    """Simplified Krippendorff's alpha (Scott's pi formula, nominal, 2 annotators).

    Uses Scott's pi formula:
        α = (P_o - P_e) / (1 - P_e)

    Where:
        P_o = observed agreement = (items where A == B) / n
        P_e = expected agreement = Σ_c P_A(c) × P_B(c)
             (sum over categories of product of marginal proportions)

    For 2 annotators, this equals Krippendorff's alpha (nominal).
    Result range: (-1, 1] for finite cases; 1.0 for perfect agreement.
    """
    if len(annotator_a) != len(annotator_b):
        raise ValueError("Lists must have same length")

    n = len(annotator_a)
    if n == 0:
        return 1.0

    categories: set[str] = set(annotator_a) | set(annotator_b)

    # Count per category per annotator
    cat_counts_a: dict[str, int] = defaultdict(int)
    cat_counts_b: dict[str, int] = defaultdict(int)
    for a, b in zip(annotator_a, annotator_b):
        cat_counts_a[a] += 1
        cat_counts_b[b] += 1

    # Observed agreement P_o
    n_agree = sum(1 for a, b in zip(annotator_a, annotator_b) if a == b)
    P_o = n_agree / n

    # Expected agreement P_e (under independence)
    P_e = 0.0
    for cat in categories:
        p_a = cat_counts_a.get(cat, 0) / n
        p_b = cat_counts_b.get(cat, 0) / n
        P_e += p_a * p_b

    # Scott's pi / Krippendorff's alpha (nominal)
    if P_e >= 1.0:
        return 1.0
    alpha = (P_o - P_e) / (1.0 - P_e)
    return alpha


def compute_iaa(
    csv_path_a: str,
    csv_path_b: str,
) -> dict:
    """Compute IAA metrics từ 2 annotation CSV files.

    Args:
        csv_path_a: path tới annotator A CSV
        csv_path_b: path tới annotator B CSV

    Returns:
        dict với cohen_kappa, cohen_kappa_per_label, krippendorff_alpha,
        item_count, label_distribution, target_met
    """
    ann_a = load_annotations(csv_path_a)
    ann_b = load_annotations(csv_path_b)

    # Match by citation_id
    common_ids = sorted(set(ann_a.keys()) & set(ann_b.keys()))
    if not common_ids:
        raise ValueError("No common citations between annotators")

    labels_a = [ann_a[cid]["label"] for cid in common_ids]
    labels_b = [ann_b[cid]["label"] for cid in common_ids]

    # Cohen's kappa (overall)
    kappa = cohen_kappa(labels_a, labels_b)

    # Cohen's kappa per label
    kappa_per_label = cohen_kappa_per_label(labels_a, labels_b)

    # Krippendorff's alpha
    alpha = krippendorffs_alpha(labels_a, labels_b)

    # Label distribution
    label_dist: dict[str, dict[str, int]] = {
        "annotator_a": defaultdict(int),
        "annotator_b": defaultdict(int),
    }
    for lbl in labels_a:
        label_dist["annotator_a"][lbl] += 1
    for lbl in labels_b:
        label_dist["annotator_b"][lbl] += 1

    # Target check: ≥ 0.7
    min_kappa = min(kappa_per_label.values()) if kappa_per_label else kappa
    target_met = bool(alpha >= 0.7 and min_kappa >= 0.7)

    return {
        "cohen_kappa_overall": round(kappa, 4),
        "cohen_kappa_per_label": {k: round(v, 4) for k, v in kappa_per_label.items()},
        "krippendorff_alpha": round(alpha, 4),
        "item_count": len(common_ids),
        "target_met": target_met,
        "target_threshold": 0.7,
        "label_distribution": {k: dict(v) for k, v in label_dist.items()},
        "citations": [
            {
                "id": cid,
                "essay": ann_a[cid]["essay"],
                "raw": ann_a[cid]["raw"],
                "label_a": ann_a[cid]["label"],
                "label_b": ann_b[cid]["label"],
                "agree": ann_a[cid]["label"] == ann_b[cid]["label"],
            }
            for cid in common_ids
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute IAA metrics (Cohen's kappa + Krippendorff's alpha)"
    )
    parser.add_argument("csv_path_a", help="CSV file cho annotator A")
    parser.add_argument("csv_path_b", help="CSV file cho annotator B")
    parser.add_argument(
        "--output", "-o", help="Output JSON file (optional)"
    )
    args = parser.parse_args()

    try:
        results = compute_iaa(args.csv_path_a, args.csv_path_b)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Print summary
    print("=" * 50)
    print("IAA Results")
    print("=" * 50)
    print(f"Items annotated: {results['item_count']}")
    print(f"Cohen's kappa (overall): {results['cohen_kappa_overall']:.4f}")
    print(f"Krippendorff's alpha:     {results['krippendorff_alpha']:.4f}")
    print(f"\nCohen's kappa per label:")
    for label, kappa in sorted(results["cohen_kappa_per_label"].items()):
        symbol = "✓" if kappa >= 0.7 else "✗"
        print(f"  {symbol} {label:25s} {kappa:+.4f}")
    print(f"\nLabel distribution:")
    for label in sorted(set(results["label_distribution"]["annotator_a"]) |
                         set(results["label_distribution"]["annotator_b"])):
        a = results["label_distribution"]["annotator_a"].get(label, 0)
        b = results["label_distribution"]["annotator_b"].get(label, 0)
        print(f"  {label:20s}  A={a:3d}  B={b:3d}")
    print(f"\nTarget (κ ≥ 0.7 AND α ≥ 0.7): {'MET ✓' if results['target_met'] else 'NOT MET ✗'}")
    print(f"  Cohen's kappa: {results['cohen_kappa_overall']:.4f} {'✓' if results['cohen_kappa_overall'] >= 0.7 else '✗'}")
    print(f"  Krippendorff's α: {results['krippendorff_alpha']:.4f} {'✓' if results['krippendorff_alpha'] >= 0.7 else '✗'}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nFull results → {args.output}")

    return 0 if results["target_met"] else 1


if __name__ == "__main__":
    sys.exit(main())
