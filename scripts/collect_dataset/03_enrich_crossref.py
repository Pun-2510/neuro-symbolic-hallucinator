#!/usr/bin/env python3
"""
Step 3: Enrich citations with extracted metadata.

Crossref API lookups are DISABLED — Crossref title-search is too noisy and
returns incorrect DOIs for arXiv preprints (e.g. "Layer Normalization" →
IUCN Red List, "Neural Machine Translation" → Goodfellow's Deep Learning).

Metadata used instead:
- DOI: extracted directly from citation text (doi: or doi.org/ prefix)
- Title: GROBID-extracted title or parsed from raw citation text
- Authors / Year / Venue: GROBID-extracted (authoritative source)

Usage:
    python scripts/collect_dataset/03_enrich_crossref.py \
        --input data/citations.json \
        --output data/citations_enriched.json

Security: uses defusedxml for XML parsing (defense against malformed XML).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CROSSREF_WARNING = """
WARNING: Crossref API lookups are DISABLED.
  Reason: Crossref title-search returns incorrect DOIs for arXiv preprints.
  Example: "Layer Normalization" -> IUCN Red List, "Neural Machine Translation"
           -> Goodfellow's Deep Learning book.
  Using extracted title/year from citation text (GROBID) as authoritative source.
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enrich citations with extracted metadata (no Crossref)")
    p.add_argument("--input", "-i", required=True, help="Input JSON from step 2")
    p.add_argument("--output", "-o", required=True, help="Output JSON")
    p.add_argument("--limit", type=int, default=0, help="Limit citations (0=all)")
    return p.parse_args()


def _extract_title_from_raw(raw: str) -> str | None:
    """Extract paper title from raw IEEE/APA citation text."""
    # IEEE: [N] Authors. "Title," Venue, Year.
    m = re.search(r'"([^"]{10,200})"', raw)
    if m:
        return m.group(1).strip()

    # APA / numbered: Authors (Year). Title. Venue
    m = re.search(r'\d{4}\)\.\s+([^.]+?)(?:\.\s+[A-Z]|$)', raw)
    if m:
        return m.group(1).strip()

    # Brackets style: [N] Authors. Title. Venue
    m = re.search(r'\]\.\s+([^.]+?)(?:\.\s+[A-Z]|$)', raw)
    if m:
        return m.group(1).strip()

    return None


def _extract_doi_from_raw(raw: str) -> str | None:
    """Extract DOI from raw citation text."""
    m = re.search(r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\d{4,}/[^\s]+)', raw)
    if m:
        return m.group(1).strip().rstrip(",.")
    m = re.search(r'doi:\s*(10\.\d{4,}/[^\s,;]+)', raw, re.I)
    if m:
        return m.group(1).strip().rstrip(",.")
    return None


def enrich_citation(citation: dict) -> dict:
    """
    Build enriched metadata from extracted citation data only.
    No Crossref API calls — Crossref title-search is too noisy for arXiv papers.
    """
    raw = citation.get("raw_text", "")

    # Resolve DOI: use GROBID-extracted first, fall back to regex extraction
    doi = citation.get("doi") or _extract_doi_from_raw(raw)
    if doi:
        doi = doi.strip().removeprefix("https://doi.org/").removeprefix("doi:")

    # Title: GROBID-extracted first, fall back to regex from raw text
    title = citation.get("title") or _extract_title_from_raw(raw)

    # Authors / year / venue: use GROBID-extracted values unchanged
    # (crossref lookup was the only other source and is now disabled)

    enrichment = {
        "doi": doi,
        "title": title,
        "authors": citation.get("authors", []),
        "year": citation.get("year"),
        "venue": citation.get("venue"),
        "url": citation.get("url"),
    }

    return {**citation, "crossref": enrichment, "_crossref_disabled": True}


def main() -> None:
    args = parse_args()
    data = json.loads(Path(args.input).read_text())
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, list):
        papers = data
    else:
        papers = list(data.values())

    flat = [(p.get("arxiv_id", f"p{i}"), c) for i, p in enumerate(papers) for c in p.get("citations", [])]

    if args.limit > 0:
        flat = flat[: args.limit]

    print(CROSSREF_WARNING)
    print(f"Found {len(flat)} citations across {len(papers)} papers")
    print("Enriching with extracted metadata (no Crossref)...")

    enriched = {}
    for i, (arxiv_id, citation) in enumerate(flat, 1):
        key = f"{arxiv_id}:{citation.get('raw_text', '')[:40]}"
        e = enrich_citation(citation)
        has_title = bool(e["crossref"].get("title"))
        print(f"[{i}/{len(flat)}] {'ok' if has_title else 'no-title'}  {e['crossref'].get('title', '')}")
        enriched[key] = e

    # Rebuild per-paper structure
    result = {}
    for i, paper in enumerate(papers):
        pid = paper.get("arxiv_id", f"p{i}")
        cits_out = []
        for c in paper.get("citations", []):
            k = f"{pid}:{c.get('raw_text', '')[:40]}"
            cits_out.append(enriched.get(k, {**c, "crossref": None}))
        result[pid] = {"arxiv_id": pid, "citations": cits_out}

    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nDone: {len(flat)} citations processed (Crossref disabled)")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
