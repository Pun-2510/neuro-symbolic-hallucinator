#!/usr/bin/env python3
"""
Step 6: Split gold_dataset.json into train/val/test sets.

Usage:
    python scripts/collect_dataset/06_split_dataset.py \
        --input data/gold_dataset.json \
        --output data/ \
        --train 0.7 \
        --val 0.15 \
        --test 0.15 \
        --seed 42 \
        --split-by paper

Split strategies:
    --split-by paper: all citations from same paper go to same split
                     (avoids citation leakage between train/test)
    --split-by citation: random split per citation (for ablation only)

Output:
    data/
    ├── gold_dataset_train.json    (N% citations)
    ├── gold_dataset_val.json      (M% citations)
    ├── gold_dataset_test.json      (K% citations)
    └── data_split_manifest.json    (metadata about the split)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from collections import Counter, defaultdict


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Split gold_dataset into train/val/test")
    p.add_argument("--input", "-i", required=True, help="Input gold_dataset.json")
    p.add_argument("--output", "-o", default="data/", help="Output directory")
    p.add_argument("--train", type=float, default=0.7)
    p.add_argument("--val", type=float, default=0.15)
    p.add_argument("--test", type=float, default=0.15)
    p.add_argument("--split-by", choices=["paper", "citation"], default="paper")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p.add_argument("--stratify", action="store_true", help="Stratify by label distribution")
    return p.parse_args()


def stratified_split(items: list, train_pct: float, val_pct: float, seed: int) -> tuple[list, list, list]:
    """Split with stratification by label."""
    random.seed(seed)
    # Group by label
    groups = defaultdict(list)
    for item in items:
        label = item.get("ground_truth", {}).get("label", "unknown")
        groups[label].append(item)

    train, val, test = [], [], []
    for label, group in groups.items():
        shuffled = group[:]
        random.shuffle(shuffled)
        n = len(shuffled)
        n_train = max(1, int(n * train_pct))
        n_val = max(1, int(n * val_pct))
        train.extend(shuffled[:n_train])
        val.extend(shuffled[n_train:n_train + n_val])
        test.extend(shuffled[n_train + n_val:])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)
    return train, val, test


def random_split(items: list, train_pct: float, val_pct: float, seed: int) -> tuple[list, list, list]:
    """Simple random split."""
    random.seed(seed)
    shuffled = items[:]
    random.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_pct)
    n_val = int(n * val_pct)
    return (
        shuffled[:n_train],
        shuffled[n_train:n_train + n_val],
        shuffled[n_train + n_val:],
    )


def paper_split(citations: list, train_pct: float, val_pct: float, seed: int, stratify: bool) -> tuple[list, list, list]:
    """Split by paper — all citations from same paper stay together."""
    random.seed(seed)

    # Group by paper
    by_paper = defaultdict(list)
    for cit in citations:
        pid = cit.get("source_paper_arxiv_id", "unknown")
        by_paper[pid].append(cit)

    papers = list(by_paper.keys())
    random.shuffle(papers)

    n = len(papers)
    n_train = max(1, int(n * train_pct))
    n_val = max(1, int(n * val_pct))

    train_papers = set(papers[:n_train])
    val_papers = set(papers[n_train:n_train + n_val])
    test_papers = set(papers[n_train + n_val:])

    train, val, test = [], [], []
    for cit in citations:
        pid = cit.get("source_paper_arxiv_id", "unknown")
        if pid in train_papers:
            train.append(cit)
        elif pid in val_papers:
            val.append(cit)
        else:
            test.append(cit)

    return train, val, test


def _patch_dataset(citations: list, dataset_id: str, split: str) -> dict:
    """Build a gold_dataset dict for one split."""
    return {
        "dataset_id": f"{dataset_id}_{split}",
        "description": f"Split: {split}",
        "num_papers": len(set(c.get("source_paper_arxiv_id", "") for c in citations)),
        "num_citations": len(citations),
        "citations": citations,
    }


def main() -> None:
    args = parse_args()
    data = json.loads(Path(args.input).read_text())

    # Extract citations
    citations = data.get("citations", [])
    if not citations:
        print(f"No citations found in {args.input}")
        sys.exit(1)

    dataset_id = data.get("dataset_id", "dataset")

    # Label distribution
    labels = Counter((c.get("ground_truth") or {}).get("label", "unknown") for c in citations)
    print(f"Total citations: {len(citations)}")
    print(f"By paper: {len(set(c.get('source_paper_arxiv_id', '') for c in citations))}")
    print(f"Label distribution: {dict(labels)}")
    print(f"Split: train={args.train} val={args.val} test={args.test}")
    print(f"Strategy: {args.split_by}")

    # Split
    if args.split_by == "paper":
        train, val, test = paper_split(citations, args.train, args.val, args.seed, args.stratify)
    else:
        if args.stratify:
            train, val, test = stratified_split(citations, args.train, args.val, args.seed)
        else:
            train, val, test = random_split(citations, args.train, args.val, args.seed)

    print(f"\nSplit result:")
    print(f"  Train: {len(train)} citations ({len(train)/len(citations)*100:.1f}%)")
    print(f"  Val:   {len(val)} citations ({len(val)/len(citations)*100:.1f}%)")
    print(f"  Test:  {len(test)} citations ({len(test)/len(citations)*100:.1f}%)")

    # Train label dist
    # Train label dist
    for name, split in [("train", train), ("val", val), ("test", test)]:
        dist = Counter((c.get("ground_truth") or {}).get("label", "unknown") for c in split)
        print(f"  {name}: {dict(dist)}")

    # Save
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        out = _patch_dataset(split_data, dataset_id, split_name)
        path = out_dir / f"gold_dataset_{split_name}.json"
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
        print(f"  → {path}")

    # Manifest
    def _gt_label(c): return (c.get("ground_truth") or {}).get("label", "unknown")

    manifest = {
        "dataset_id": dataset_id,
        "seed": args.seed,
        "split_by": args.split_by,
        "stratify": args.stratify,
        "splits": {
            "train": {
                "num_citations": len(train),
                "num_papers": len(set(c.get("source_paper_arxiv_id", "") for c in train)),
                "label_distribution": dict(Counter(_gt_label(c) for c in train)),
            },
            "val": {
                "num_citations": len(val),
                "num_papers": len(set(c.get("source_paper_arxiv_id", "") for c in val)),
                "label_distribution": dict(Counter(_gt_label(c) for c in val)),
            },
            "test": {
                "num_citations": len(test),
                "num_papers": len(set(c.get("source_paper_arxiv_id", "") for c in test)),
                "label_distribution": dict(Counter(_gt_label(c) for c in test)),
            },
        },
        "files": {
            "train": "gold_dataset_train.json",
            "val": "gold_dataset_val.json",
            "test": "gold_dataset_test.json",
        },
    }
    manifest_path = out_dir / "data_split_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\n📄 Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
