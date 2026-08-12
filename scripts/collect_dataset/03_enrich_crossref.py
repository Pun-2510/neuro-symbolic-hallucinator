#!/usr/bin/env python3
"""
Step 3: Enrich citations with Crossref metadata lookup.

Usage:
    python scripts/collect_dataset/03_enrich_crossref.py \
        --input data/citations.json \
        --output data/citations_enriched.json

Search strategy:
1. DOI if present
2. Title extracted from raw citation text (best quality)
3. Last-resort: raw citation text as query (noisy but catches more)

Security: uses defusedxml for XML parsing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import defusedxml.ElementTree as ET

CROSSREF_API = "https://api.crossref.org/works/"
HEADERS = {"User-Agent": "EssayIntegrityChecker/1.0 (mailto:student@tdtu.edu.vn)"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enrich citations via Crossref API")
    p.add_argument("--input", "-i", required=True, help="Input JSON from step 2")
    p.add_argument("--output", "-o", required=True, help="Output JSON")
    p.add_argument("--delay", type=float, default=0.33, help="Delay between requests (s)")
    p.add_argument("--limit", type=int, default=0, help="Limit citations (0=all)")
    return p.parse_args()


def _get(url: str) -> dict | None:
    """GET JSON from URL safely."""
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 404:
            return None
        return None
    except Exception:
        return None


def _extract_title_from_raw(raw: str) -> str | None:
    """Extract paper title from raw IEEE/APA citation text."""
    # IEEE: [N] Authors. "Title," Venue, Year.
    m = re.search(r'\"([^\"]{10,200})\"', raw)
    if m:
        return m.group(1).strip()

    # APA / numbered: Authors (Year). Title. Venue
    # Title usually follows year and ends before period or comma+venue
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


def _crossref_lookup(query: str, rows: int = 1) -> dict | None:
    """Search Crossref by title query."""
    q = "+".join(query.split()[:8])  # first 8 words
    url = f"{CROSSREF_API}?query.title={q}&rows={rows}&sort=relevance"
    data = _get(url)
    if not data or not data.get("message", {}).get("items"):
        return None
    return data["message"]["items"][0]


def _parse_crossref_item(item: dict) -> dict:
    """Parse Crossref item into normalized dict."""
    def first(arr):
        return arr[0] if arr else None

    def year(d):
        if not d:
            return None
        parts = d.get("date-parts", [[]])
        y = parts[0][0] if parts and parts[0] else None
        return str(y) if y else None

    authors = []
    for a in item.get("author", []):
        given = a.get("given", "")
        family = a.get("family", "")
        name = f"{given} {family}".strip() if given else family
        if name:
            authors.append(name)

    return {
        "doi": item.get("DOI"),
        "title": first(item.get("title")),
        "authors": authors,
        "year": year(item.get("created")),
        "venue": first(item.get("container-title")),
        "publisher": item.get("publisher"),
        "type": item.get("type"),
        "url": f"https://doi.org/{item.get('DOI', '')}",
    }


def enrich_citation(citation: dict, delay: float) -> dict:
    """Look up Crossref metadata for one citation."""
    result = {**citation, "crossref": None}

    raw = citation.get("raw_text", "")

    # Strategy 1: DOI in raw text
    doi = citation.get("doi") or _extract_doi_from_raw(raw)
    if doi:
        doi = doi.strip().removeprefix("https://doi.org/").removeprefix("doi:")
        data = _get(f"{CROSSREF_API}{doi}")
        time.sleep(delay)
        if data and "message" in data:
            result["crossref"] = {**_parse_crossref_item(data["message"]), "source": "doi"}
            return result

    # Strategy 2: Extract title from raw citation
    title = citation.get("title") or _extract_title_from_raw(raw)
    if title:
        item = _crossref_lookup(title)
        time.sleep(delay)
        if item:
            result["crossref"] = {**_parse_crossref_item(item), "source": "title_search"}
            return result

    # Strategy 3: Use first meaningful words of raw text
    # Strip common prefixes: [N], numbers, authors+year at start
    query_text = re.sub(r"^\[\d+\]\s*", "", raw)  # [1] prefix
    query_text = re.sub(r"^\d+\.\s*", "", query_text)  # 1. prefix
    query_text = re.sub(r"\d{4}\)\.\s*", "", query_text)  # (2015). prefix
    query_text = re.sub(r"https?://\S+", "", query_text)  # URLs
    query_text = re.sub(r"doi:\s*\S+", "", query_text, flags=re.I)  # doi:xxx
    query_text = re.sub(r"\s+", " ", query_text).strip()
    words = query_text.split()[:12]  # first 12 words
    if len(words) >= 3:
        item = _crossref_lookup(" ".join(words))
        time.sleep(delay)
        if item:
            result["crossref"] = {**_parse_crossref_item(item), "source": "raw_search"}
            return result

    return result


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

    print(f"Found {len(flat)} citations across {len(papers)} papers")
    print(f"Enriching via Crossref (delay={args.delay}s)...")

    enriched = {}
    matched = 0
    for i, (arxiv_id, citation) in enumerate(flat, 1):
        key = f"{arxiv_id}:{citation.get('raw_text', '')[:40]}"
        print(f"[{i}/{len(flat)}] ", end="", flush=True)
        e = enrich_citation(citation, args.delay)
        src = e["crossref"]["source"] if e["crossref"] else "✗"
        print(f"{src}")
        if e["crossref"]:
            matched += 1
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
    print(f"\n✓ Enriched: {matched}/{len(flat)} citations matched Crossref")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
