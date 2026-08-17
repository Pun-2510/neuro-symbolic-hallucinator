#!/usr/bin/env python3
"""
Step 5: Compute Inter-Annotator Agreement (IAA) from annotation CSV.

Usage:
    python scripts/collect_dataset/05_compute_iaa.py \
        --csv data/gold_dataset_annotation.csv \
        --annotator1 student_A \
        --annotator2 student_B

Supports:
    - Cohen's kappa (2 annotators, any number of categories)
    - Krippendorff's alpha (2+ annotators, any number of categories)
    - Per-category precision/recall/F1 vs. ground truth

Output:
    - Terminal: formatted report
    - JSON: data/iaa_report.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute IAA from annotation CSV")
    p.add_argument("--csv", "-i", required=True, help="Annotation CSV file")
    p.add_argument("--annotator1", default="annotator", help="Column name for annotator 1")
    p.add_argument("--annotator2", default="annotator_B", help="Column name for annotator 2")
    p.add_argument("--label-col", default="ground_truth_label", help="Column for label values")
    p.add_argument("--output", "-o", default="data/iaa_report.json", help="Output JSON report")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def cohen_kappa(ratings1: list[str], ratings2: list[str]) -> dict[str, Any]:
    """Cohen's kappa for two raters."""
    assert len(ratings1) == len(ratings2)
    n = len(ratings1)
    if n == 0:
        return {"kappa": None, "error": "No items"}

    categories = set(ratings1) | set(ratings2)
    c1 = Counter(ratings1)
    c2 = Counter(ratings2)
    total = Counter(ratings1 + ratings2)
    N = sum(total.values())

    # Observed agreement P_o
    agree = sum(1 for a, b in zip(ratings1, ratings2) if a == b)
    P_o = agree / n if n > 0 else 0

    # Expected agreement P_e
    P_e = sum(
        (c1[cat] / n) * (c2[cat] / n)
        for cat in categories
    ) if n > 0 else 0

    kappa = (P_o - P_e) / (1 - P_e) if (1 - P_e) != 0 else 1.0

    # Per-category breakdown
    per_cat = {}
    for cat in sorted(categories):
        TP = sum(1 for a, b in zip(ratings1, ratings2) if a == b == cat)
        FN = sum(1 for a, b in zip(ratings1, ratings2) if a == cat and b != cat)
        FP = sum(1 for a, b in zip(ratings1, ratings2) if a != cat and b == cat)
        p1 = c1[cat] / n
        p2 = c2[cat] / n
        per_cat[cat] = {
            "count_A": c1[cat],
            "count_B": c2[cat],
            "agreement_count": TP,
            "p_A": round(p1, 4),
            "p_B": round(p2, 4),
            "precision_A_vs_B": round(TP / c1[cat], 4) if c1[cat] > 0 else None,
            "recall_A_vs_B": round(TP / c2[cat], 4) if c2[cat] > 0 else None,
        }

    return {
        "kappa": round(kappa, 4),
        "observed_agreement_Po": round(P_o, 4),
        "expected_agreement_Pe": round(P_e, 4),
        "n_items": n,
        "n_categories": len(categories),
        "per_category": per_cat,
        "rating_counts_A": dict(c1),
        "rating_counts_B": dict(c2),
    }


def krippendorffs_alpha(
    ratings: list[dict[str, str]],
    annotators: list[str],
    categories: list[str],
) -> dict[str, Any]:
    """Krippendorff's alpha for 2+ annotators, nominal metric."""
    items = {}
    for row in ratings:
        cid = row.get("citation_id", "")
        item_ratings = [row.get(ann, "").strip() for ann in annotators]
        valid = [r for r in item_ratings if r and r not in ("", "nan")]
        if valid:
            items[cid] = valid

    if not items:
        return {"alpha": None, "error": "No items with valid ratings"}

    n = len(items)
    D_u = 0.0  # observed disagreements
    N = 0  # total ratings

    cat_counts = Counter()
    for rat in items.values():
        N += len(rat)
        cat_counts.update(rat)

    # D_co (coincidence matrix) — nominal
    cats = sorted(set(categories))
    cat_idx = {c: i for i, c in enumerate(cats)}
    K = len(cats)
    coincidence = [[0] * K for _ in range(K)]

    for rat in items.values():
        for i, c1 in enumerate(rat):
            for j, c2 in enumerate(rat):
                if i != j:
                    coincidence[cat_idx[c1]][cat_idx[c2]] += 1

    # Observed
    D_co_sum = sum(
        coincidence[i][j] * (1 if i != j else 0)
        for i in range(K) for j in range(K)
    )

    # Expected: each category proportion
    total_pairs = N * (N - 1)
    D_ce_sum = 0.0
    for cat in cats:
        nc = cat_counts[cat]
        D_ce_sum += nc * (N - nc)

    D_u = D_co_sum / total_pairs if total_pairs > 0 else 0
    D_ce = D_ce_sum / total_pairs if total_pairs > 0 else 1

    alpha = 1 - D_u / D_ce if D_ce != 0 else 1.0

    return {
        "alpha": round(alpha, 4),
        "n_items": n,
        "n_ratings": N,
        "n_annotators": len(annotators),
        "n_categories": K,
        "D_u": round(D_u, 6),
        "D_ce": round(D_ce, 6),
        "category_counts": dict(cat_counts),
    }


def agreement_vs_ground_truth(
    ratings: list[dict],
    label_col: str,
    gt_col: str = "ground_truth_label",
) -> dict[str, Any]:
    """Compute per-category P/R/F1 vs ground truth."""
    cats = set()
    tp_total = fp_total = fn_total = 0

    results = {}
    for cat in sorted(cats):
        tp = fp = fn = 0
        for row in ratings:
            pred = row.get(label_col, "").strip()
            gt = row.get(gt_col, "").strip()
            if pred == cat and gt == cat:
                tp += 1
            elif pred == cat and gt != cat:
                fp += 1
            elif pred != cat and gt == cat:
                fn += 1
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        results[cat] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
                       "tp": tp, "fp": fp, "fn": fn}

    return results


def main() -> None:
    args = parse_args()
    rows = load_csv(args.csv)

    if not rows:
        print(f"No data found in {args.csv}")
        sys.exit(1)

    # Check columns
    col1 = args.annotator1
    col2 = args.annotator2
    label_col = args.label_col

    has_ann1 = col1 in rows[0] or "annotator" in rows[0]
    has_ann2 = col2 in rows[0]

    print(f"CSV columns: {list(rows[0].keys())}")
    print(f"Total rows: {len(rows)}")

    # Use label col as ratings
    ratings1 = [r.get(col1, r.get(label_col, "")).strip() for r in rows]
    ratings2 = [r.get(col2, "").strip() for r in rows]

    # Filter empty
    pairs = [(r1, r2) for r1, r2 in zip(ratings1, ratings2) if r1 and r2]

    if not pairs:
        # No second annotator → use Crossref match as pseudo-prediction
        print("No second annotator found. Computing Crossref-based predictions vs human labels...")
        pairs = []
        for r in rows:
            gt = r.get(label_col, "").strip()
            # Crossref match → predict "verified" if matched
            crossref_matched = bool(r.get("crossref_title") or r.get("doi"))
            pred = "verified" if crossref_matched else "suspected_hallucination"
            if gt:  # only include if human has labeled
                pairs.append((pred, gt))
        print(f"  Pairs with human labels: {len(pairs)}")
        if not pairs:
            print("\n  ⚠️  CSV not yet annotated. Showing crossref match statistics instead.")
            matched = sum(1 for r in rows if r.get("crossref_title") or r.get("doi"))
            unmatched = len(rows) - matched
            print(f"  Crossref matched:  {matched}/{len(rows)} ({matched/len(rows)*100:.1f}%)")
            print(f"  Crossref unmatched: {unmatched}/{len(rows)} ({unmatched/len(rows)*100:.1f}%)")
            print("\n  After annotating, re-run this script to compute Cohen's kappa.")
            sys.exit(0)

    print(f"Valid pairs: {len(pairs)}")

    r1, r2 = zip(*pairs)
    kappa_result = cohen_kappa(list(r1), list(r2))
    print("\n" + "=" * 50)
    print("COHEN'S KAPPA")
    print("=" * 50)
    print(f"  κ = {kappa_result['kappa']}")
    print(f"  P(observed agreement) = {kappa_result['observed_agreement_Po']}")
    print(f"  P(expected agreement) = {kappa_result['expected_agreement_Pe']}")
    print(f"  N items = {kappa_result['n_items']}")
    print(f"  Categories = {kappa_result['n_categories']}")

    # Interpretation
    k = kappa_result["kappa"]
    if k is not None:
        if k >= 0.8:
            interp = "Almost perfect"
        elif k >= 0.6:
            interp = "Substantial"
        elif k >= 0.4:
            interp = "Moderate"
        elif k >= 0.2:
            interp = "Fair"
        else:
            interp = "Slight / Poor"
        print(f"  Interpretation: {interp}")
        if k >= 0.7:
            print("  ✅ PASSES threshold (κ ≥ 0.7)")
        else:
            print("  ❌ BELOW threshold (κ ≥ 0.7)")

    # Per-category
    print("\nPer-category breakdown:")
    for cat, info in kappa_result.get("per_category", {}).items():
        print(f"  [{cat}]")
        print(f"    Annotator A: {info['count_A']} ({info['p_A']:.1%})")
        print(f"    Annotator B: {info['count_B']} ({info['p_B']:.1%})")
        print(f"    Agreement: {info['agreement_count']}")
        if info.get("precision_A_vs_B") is not None:
            print(f"    P(prec)={info['precision_A_vs_B']:.1%} R(rec)={info.get('recall_A_vs_B', 0):.1%}")

    # Krippendorff if we have more columns
    all_cols = list(rows[0].keys())
    ann_cols = [c for c in all_cols if "annotator" in c.lower() and c != label_col]
    if len(ann_cols) >= 2:
        cats = sorted(set(r.get(label_col, "") for r in rows if r.get(label_col, "")))
        krip = krippendorffs_alpha(rows, ann_cols, cats)
        print("\n" + "=" * 50)
        print("KRIPPENDORFF'S ALPHA")
        print("=" * 50)
        print(f"  α = {krip.get('alpha', 'N/A')}")
        print(f"  N items = {krip.get('n_items')}")
        print(f"  N annotators = {krip.get('n_annotators')}")
        print(f"  D_u = {krip.get('D_u')}, D_ce = {krip.get('D_ce')}")
        if krip.get("alpha", 0) >= 0.8:
            print("  ✅ Good reliability")
        elif krip.get("alpha", 0) >= 0.667:
            print("  ⚠️ Acceptable (≥ 0.667)")
        else:
            print("  ❌ Low reliability")

    # Save JSON report
    report = {
        "cohens_kappa": kappa_result,
        "krippendorffs_alpha": krip if len(ann_cols) >= 2 else None,
        "metadata": {
            "csv": str(args.csv),
            "annotator1_col": col1,
            "annotator2_col": col2,
            "label_col": label_col,
            "n_rows": len(rows),
            "n_valid_pairs": len(pairs),
        },
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n📄 Report saved: {out_path}")

    return report


if __name__ == "__main__":
    main()
