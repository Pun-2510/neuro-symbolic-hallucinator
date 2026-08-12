#!/usr/bin/env python3
"""
Step 4: Format enriched citations into gold_dataset.json + CSV for manual annotation.

Usage:
    python scripts/collect_dataset/04_format_gold_dataset.py \
        --input data/citations_enriched.json \
        --output data/gold_dataset.json \
        --csv data/gold_dataset_annotation.csv

Output gold_dataset.json follows v1.2 schema:
{
  "dataset_id": "arxiv_v1",
  "description": "...",
  "num_papers": N,
  "num_citations": M,
  "citations": [
    {
      "citation_id": "c001",
      "source_paper_arxiv_id": "2301.00001",
      "citation_raw": "LeCun, Y., et al. (2015). Deep learning. Nature, 521, 436-444.",
      "citation_normalized": "lecun y et al 2015 deep learning nature",
      "style": "APA_LIKE",
      "authors": ["Yann LeCun"],
      "year": "2015",
      "title": "Deep learning",
      "doi": "10.1038/nature14539",
      "crossref": { ... },
      "ground_truth": {
        "label": "verified",          # verified | suspected_hallucination | metadata_error
        "mapping_status": "matched",  # matched | missing_reference | duplicate_reference | ...
        "annotator": "human_A",
        "annotated_at": "2026-08-12",
        "notes": "..."
      }
    },
    ...
  ]
}

CSV format for easy annotation in Google Sheets / Excel:
citation_id | source_paper | citation_raw | doi | crossref_title | ground_truth_label | notes
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse


# v1.2 CitationMappingStatus values
MAPPING_STATUS_OPTIONS = [
    "matched",
    "missing_reference",
    "uncited_reference",
    "in_text_mismatch",
    "duplicate_reference",
    "ambiguous_mapping",
    "style_inconsistent",
    "unresolved",
]

# v1.2 ValidationLabel values
LABEL_OPTIONS = [
    "verified",
    "suspected_hallucination",
    "metadata_error",
    "unresolved",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Format gold_dataset.json + annotation CSV")
    p.add_argument("--input", "-i", required=True, help="Input JSON from step 3")
    p.add_argument("--output", "-o", required=True, help="Output gold_dataset.json")
    p.add_argument("--csv", help="Output CSV for annotation (optional)")
    p.add_argument("--dataset-id", default="arxiv_v1", help="Dataset identifier")
    p.add_argument("--description", default="arXiv papers, Crossref-enriched, human-annotated", help="Dataset description")
    return p.parse_args()


def _norm(text: str | None) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    import re
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _pick_authors(citation: dict) -> list[str]:
    """Pick best authors from available sources."""
    if citation.get("authors"):
        return citation["authors"]
    crossref = citation.get("crossref") or {}
    if crossref.get("authors"):
        return crossref["authors"]
    return []


def _pick_year(citation: dict) -> str | None:
    """Pick best year."""
    if citation.get("year"):
        return citation["year"]
    cr = citation.get("crossref") or {}
    if cr.get("year"):
        return cr["year"]
    return None


def _pick_title(citation: dict) -> str | None:
    if citation.get("title"):
        return citation["title"]
    cr = citation.get("crossref") or {}
    if cr.get("title"):
        return cr["title"]
    return None


def _pick_doi(citation: dict) -> str | None:
    if citation.get("doi"):
        doi = citation["doi"].strip()
        if doi.startswith("http"):
            doi = urlparse(doi).path.strip("/")
        return doi
    cr = citation.get("crossref") or {}
    if cr.get("doi"):
        return cr["doi"]
    return None


def _pick_venue(citation: dict) -> str | None:
    if citation.get("venue"):
        return citation["venue"]
    cr = citation.get("crossref") or {}
    if cr.get("venue"):
        return cr["venue"]
    return None


def main() -> None:
    args = parse_args()
    data = json.loads(Path(args.input).read_text())
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Handle both dict and list formats
    if isinstance(data, list):
        papers = {p.get("arxiv_id", f"paper_{i}"): p for i, p in enumerate(data)}
    else:
        papers = data

    citations_out = []
    for arxiv_id, paper in papers.items():
        paper_cits = paper.get("citations", [])
        for i, cit in enumerate(paper_cits):
            cid = f"{arxiv_id}_{i+1:03d}"
            crossref = cit.get("crossref")
            authors = _pick_authors(cit)
            year = _pick_year(cit)
            title = _pick_title(cit)
            doi = _pick_doi(cit)
            venue = _pick_venue(cit)
            raw = cit.get("raw_text", "")
            if not raw:
                continue

            entry = {
                "citation_id": cid,
                "source_paper_arxiv_id": arxiv_id,
                "citation_raw": raw,
                "citation_normalized": _norm(raw),
                "style": cit.get("style", "UNKNOWN"),
                "authors": authors,
                "year": year,
                "title": title,
                "doi": doi,
                "venue": venue,
                "crossref": crossref,
                "ground_truth": None,  # Filled by human annotator
            }
            citations_out.append(entry)

    total = len(citations_out)
    unmatched = sum(1 for c in citations_out if c["crossref"] is None)
    matched = total - unmatched

    dataset = {
        "dataset_id": args.dataset_id,
        "description": args.description,
        "num_papers": len(papers),
        "num_citations": total,
        "stats": {
            "crossref_matched": matched,
            "crossref_unmatched": unmatched,
        },
        "citation_level_schema": {
            "label": LABEL_OPTIONS,
            "mapping_status": MAPPING_STATUS_OPTIONS,
        },
        "instructions": {
            "label": {
                "verified": "Citation verified — title, authors, year match Crossref/S2.",
                "suspected_hallucination": "Citation fabricated — not found in any source.",
                "metadata_error": "Citation exists but title/author/year is wrong.",
                "unresolved": "Cannot determine.",
            },
            "mapping_status": {
                "matched": "Citation in text links correctly to reference list.",
                "missing_reference": "Citation in text but no matching reference entry.",
                "uncited_reference": "Reference exists but no in-text citation.",
                "in_text_mismatch": "In-text citation differs from reference list entry.",
                "duplicate_reference": "Same citation listed multiple times.",
                "ambiguous_mapping": "Cannot determine which reference is cited.",
                "style_inconsistent": "In-text and reference list use different styles.",
                "unresolved": "Cannot determine mapping.",
            },
        },
        "citations": citations_out,
    }

    out_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False))
    print(f"✓ gold_dataset.json: {total} citations from {len(papers)} papers")
    print(f"  Crossref matched: {matched}/{total}")
    print(f"  Crossref unmatched: {unmatched}/{total}")
    print(f"  Output: {out_path}")

    # CSV for annotation
    if args.csv:
        csv_path = Path(args.csv)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "citation_id",
                    "source_paper",
                    "citation_raw",
                    "doi",
                    "crossref_title",
                    "crossref_authors",
                    "crossref_year",
                    "crossref_venue",
                    "ground_truth_label",
                    "ground_truth_mapping_status",
                    "annotator",
                    "notes",
                ],
            )
            writer.writeheader()
            for c in citations_out:
                cr = c.get("crossref") or {}
                writer.writerow({
                    "citation_id": c["citation_id"],
                    "source_paper": c["source_paper_arxiv_id"],
                    "citation_raw": c["citation_raw"],
                    "doi": c.get("doi") or cr.get("doi") or "",
                    "crossref_title": cr.get("title") or "",
                    "crossref_authors": "; ".join(cr.get("authors", [])),
                    "crossref_year": c.get("year") or cr.get("year") or "",
                    "crossref_venue": c.get("venue") or cr.get("venue") or "",
                    "ground_truth_label": "",
                    "ground_truth_mapping_status": "",
                    "annotator": "",
                    "notes": "",
                })
        print(f"  CSV for annotation: {csv_path}")

    print(f"\n📋 Next step: Open {csv_path if args.csv else out_path}")
    print(f"   Fill in 'ground_truth_label' + 'ground_truth_mapping_status' columns.")


if __name__ == "__main__":
    main()
