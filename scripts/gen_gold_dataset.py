#!/usr/bin/env python
"""Sinh gold_dataset.json mồi — annotation cho IAA (Inter-Annotator Agreement).

Format:
{
    "annotation_guideline_version": "1.0",
    "created_at": "2026-01-15T10:00:00Z",
    "items": [
        {
            "essay": "essay_01_real_only.pdf",
            "citations": [
                {
                    "raw_text": "...",
                    "true_label": "verified",
                    "note": "DOI resolves, authors match"
                },
                ...
            ]
        },
        ...
    ]
}

TODO(user): tuần 14 — 2 SV cùng annotate thủ công trên file này,
tính Cohen's kappa, lưu vào `data/ground_truth/iaa_template.csv`.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


# Ground truth mồi (stub — cần 2 SV cùng annotate lại)
GOLD_SEED = {
    "essay_01_real_only.pdf": {
        "citations": [
            {"raw_text": "LeCun, Bengio, & Hinton, 2015", "true_label": "verified"},
            {"raw_text": "He, Zhang, Ren, & Sun, 2016", "true_label": "verified"},
            {"raw_text": "Vaswani et al., 2017", "true_label": "verified"},
            {"raw_text": "Devlin et al., 2019", "true_label": "verified"},
            {"raw_text": "Brown et al., 2020", "true_label": "verified"},
        ],
    },
    "essay_02_mixed.pdf": {
        "citations": [
            {"raw_text": "Vaswani et al., 2017", "true_label": "verified"},
            {"raw_text": "Devlin et al., 2018", "true_label": "metadata_error", "note": "Year wrong"},
            {"raw_text": "He, Zhang, Ren, & Sun, 2016", "true_label": "verified"},
            {"raw_text": "Smith & Doe, 2024", "true_label": "suspected_hallucination"},
        ],
    },
    "essay_03_fabricated.pdf": {
        "citations": [
            {"raw_text": "Smith & Doe, 2024", "true_label": "suspected_hallucination"},
            {"raw_text": "Nguyen et al., 2023", "true_label": "suspected_hallucination"},
            {"raw_text": "Anderson and Brown, 2025", "true_label": "suspected_hallucination"},
        ],
    },
    "essay_04_real_small.pdf": {
        "citations": [
            {"raw_text": "LeCun et al., 2015", "true_label": "verified"},
            {"raw_text": "Vaswani et al., 2017", "true_label": "verified"},
        ],
    },
    "essay_05_edge_doi_only.pdf": {
        "citations": [
            {"raw_text": "10.48550/arXiv.1706.03762", "true_label": "verified"},
            {"raw_text": "10.1038/nature14539", "true_label": "verified"},
        ],
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate gold dataset mồi")
    parser.add_argument(
        "--output",
        default="data/ground_truth/gold_dataset.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    payload = {
        "annotation_guideline_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "annotators": ["523H0054", "523H0096"],
        "items": [
            {"essay": filename, "citations": data["citations"]}
            for filename, data in GOLD_SEED.items()
        ],
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    total = sum(len(item["citations"]) for item in payload["items"])
    print(f"Wrote gold dataset → {out} ({total} citations across {len(payload['items'])} essays)")


if __name__ == "__main__":
    main()