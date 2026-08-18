#!/usr/bin/env python3
"""
Step 7: Automated verification of citations via OpenAlex API.

Reads:   data/citations_full_enriched.json  (already Crossref-enriched)
Outputs: data/citations_verified.json       (with auto-labels)
         data/citations_needs_review.csv    (uncertain ones for human review)

Auto-labeling rules:
  score >= 0.85 → "verified"         (auto, high confidence)
  0.50 <= score < 0.85 → "needs_review"  (human check)
  score < 0.50 → "suspected_hallucination" (auto, likely fake)

Score = weighted average of:
  - title_similarity  (weight 0.5)   — fuzzy match
  - author_overlap    (weight 0.3)   — Jaccard of author names
  - year_match        (weight 0.2)   — exact or ±1 year

OpenAlex API: https://api.openalex.org
Rate limit: 10 req/s → ~5 min for 2887 citations (sequential)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import defusedxml.ElementTree as ET

OPENALEX_API = "https://api.openalex.org/works?filter=doi:"
HEADERS = {"User-Agent": "EssayIntegrityChecker/1.0 (mailto:student@tdtu.edu.vn)"}

# Label thresholds
THRESHOLD_VERIFIED = 0.85
THRESHOLD_SUSPECTED = 0.50


# ─── Scoring ──────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Normalize text for comparison: lowercase, strip, remove punctuation."""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_similarity(a: str, b: str) -> float:
    """Fuzzy title match using SequenceMatcher."""
    if not a or not b:
        return 0.0
    na, nb = normalize(a), normalize(b)
    if na == nb:
        return 1.0
    # Check if one contains the other
    if na in nb or nb in na:
        return 0.85
    return SequenceMatcher(None, na, nb).ratio()


def author_overlap(authors_claimed: list, authors_found: list) -> float:
    """Jaccard similarity of normalized author names."""
    if not authors_claimed and not authors_found:
        return 1.0
    if not authors_claimed or not authors_found:
        return 0.0

    norm_claimed = {normalize_name(n) for n in authors_claimed}
    norm_found = {normalize_name(n) for n in authors_found}

    if not norm_claimed or not norm_found:
        return 0.0

    intersection = norm_claimed & norm_found
    union = norm_claimed | norm_found
    return len(intersection) / len(union) if union else 0.0


def normalize_name(name: str) -> str:
    """Normalize author name: extract surname + first initial."""
    if not name:
        return ""
    parts = name.lower().split()
    if not parts:
        return ""
    # Assume "First Last" or "Last, First" format
    if "," in name:
        # "Last, First"
        surname = parts[0].rstrip(",")
        initial = parts[1][0] if len(parts) > 1 else ""
    else:
        # "First Last"
        surname = parts[-1]
        initial = parts[0][0] if len(parts) > 1 else ""
    return f"{surname} {initial}".strip()


def year_match(claimed: str, found_year: str | None) -> float:
    """Exact or near-exact year match."""
    if not claimed:
        return 0.5  # neutral if no year claimed
    if not found_year:
        return 0.0
    try:
        c = int(claimed)
        f = int(found_year[:4])
        diff = abs(c - f)
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.7
        elif diff <= 3:
            return 0.3
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def score_citation(
    claimed_title: str,
    claimed_authors: list,
    claimed_year: str,
    found: dict | None,
) -> dict:
    """
    Compute verification score for a citation.
    Returns: {score, title_sim, author_sim, year_sim, matched_fields, verdict}
    """
    if not found:
        return {
            "score": 0.0,
            "title_sim": 0.0,
            "author_sim": 0.0,
            "year_sim": 0.0,
            "matched_fields": [],
            "verdict": "suspected_hallucination",
            "openalex": None,
        }

    found_title = found.get("title", "") or ""
    found_authors = found.get("authors", []) or []
    found_year = found.get("publication_year")

    ts = title_similarity(claimed_title, found_title)
    aus = author_overlap(claimed_authors, found_authors)
    ys = year_match(claimed_year, found_year)

    # Weighted score
    score = ts * 0.5 + aus * 0.3 + ys * 0.2

    # Matched fields
    matched = []
    if ts >= 0.8:
        matched.append("title")
    if aus >= 0.5:
        matched.append("authors")
    if ys >= 0.7:
        matched.append("year")

    # Verdict
    if score >= THRESHOLD_VERIFIED:
        verdict = "verified"
    elif score < THRESHOLD_SUSPECTED:
        verdict = "suspected_hallucination"
    else:
        verdict = "needs_review"

    return {
        "score": round(score, 3),
        "title_sim": round(ts, 3),
        "author_sim": round(aus, 3),
        "year_sim": round(ys, 3),
        "matched_fields": matched,
        "verdict": verdict,
        "openalex": found,
    }


# ─── OpenAlex lookup ──────────────────────────────────────────────────────

def lookup_doi(doi: str) -> dict | None:
    """Look up a DOI in OpenAlex."""
    doi = doi.strip().removeprefix("https://doi.org/").removeprefix("doi:")
    url = f"{OPENALEX_API}{doi}"
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return None
        w = results[0]
        authors = []
        for a in w.get("authorships", []):
            au = a.get("author", {})
            display = au.get("display_name", "")
            if display:
                authors.append(display)
        return {
            "doi": doi,
            "title": w.get("title", ""),
            "authors": authors,
            "publication_year": str(w.get("publication_year", "")),
            "venue": w.get("primary_location", {}).get("source", {}).get("display_name", ""),
            "url": w.get("doi", ""),
            "openalex_id": w.get("id", ""),
            "cited_by_count": w.get("cited_by_count", 0),
        }
    except (HTTPError, TimeoutError, OSError):
        return None
    except Exception:
        return None


def lookup_title(title: str) -> dict | None:
    """Search by title in OpenAlex."""
    if not title or len(title) < 10:
        return None
    q = "+".join(title.split()[:6])
    url = f"https://api.openalex.org/works?search={q}&per_page=1"
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = data.get("results", [])
        if not results:
            return None
        w = results[0]
        authors = []
        for a in w.get("authorships", []):
            au = a.get("author", {})
            display = au.get("display_name", "")
            if display:
                authors.append(display)
        return {
            "title": w.get("title", ""),
            "authors": authors,
            "publication_year": str(w.get("publication_year", "")),
            "venue": w.get("primary_location", {}).get("source", {}).get("display_name", ""),
            "doi": w.get("doi", ""),
            "openalex_id": w.get("id", ""),
            "cited_by_count": w.get("cited_by_count", 0),
        }
    except Exception:
        return None


# ─── Main ────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify citations via OpenAlex")
    p.add_argument("--input", "-i", default="data/citations_full_enriched.json")
    p.add_argument("--output", "-o", default="data/citations_verified.json")
    p.add_argument("--review-csv", default="data/citations_needs_review.csv")
    p.add_argument("--delay", type=float, default=0.1, help="Delay between requests (s)")
    p.add_argument("--limit", type=int, default=0, help="Limit citations (0=all)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    raw_data = json.loads(Path(args.input).read_text())

    # Flatten to citations — data is {arxiv_id: {arxiv_id, citations: [...]}}
    citations = []
    for arxiv_id, paper in raw_data.items():
        for i, cit in enumerate(paper.get("citations", [])):
            citations.append({**cit, "_arxiv_id": arxiv_id, "_idx": i})

    if args.limit > 0:
        citations = citations[:args.limit]

    print(f"Verifying {len(citations)} citations via OpenAlex...")
    print(f"Threshold: verified >= {THRESHOLD_VERIFIED}, suspected < {THRESHOLD_SUSPECTED}")
    print()

    verified = 0
    suspected = 0
    needs_review = 0
    not_found = 0

    results = {}

    for i, cit in enumerate(citations, 1):
        key = f"{cit['_arxiv_id']}_{cit['_idx']+1:03d}"
        raw = cit.get("raw_text", "") or cit.get("citation_raw", "")

        # Prefer crossref enrichment, else extract from raw
        crossref = cit.get("crossref") or {}
        claimed_title = (
            crossref.get("title")
            or cit.get("title")
            or _extract_title(raw)
        )
        claimed_authors = (
            _parse_authors(crossref.get("authors"))
            or _parse_authors(cit.get("authors"))
            or _extract_authors(raw)
        )
        claimed_year = (
            crossref.get("year")
            or cit.get("year")
            or _extract_year(raw)
        )
        doi = (
            crossref.get("doi")
            or cit.get("doi")
            or _extract_doi(raw)
        )

        found = None
        reason = ""

        # Strategy 1: DOI lookup (most reliable)
        if doi:
            found = lookup_doi(doi)
            if found:
                reason = f"doi:{doi[:30]}"
            time.sleep(args.delay)

        # Strategy 2: title search (fallback)
        if not found and claimed_title:
            found = lookup_title(claimed_title)
            if found:
                reason = "title_search"
            time.sleep(args.delay)

        # Score
        scored = score_citation(claimed_title, claimed_authors, claimed_year, found)
        scored["_key"] = key
        scored["_arxiv_id"] = cit["_arxiv_id"]
        scored["_raw"] = raw[:200]
        scored["_claimed_title"] = claimed_title
        scored["_claimed_authors"] = claimed_authors
        scored["_claimed_year"] = claimed_year
        scored["_doi"] = doi
        scored["_reason"] = reason

        results[key] = scored

        v = scored["verdict"]
        if v == "verified":
            verified += 1
            symbol = "✓"
        elif v == "suspected_hallucination":
            suspected += 1
            symbol = "✗"
        else:
            needs_review += 1
            symbol = "?"

        print(f"[{i:4d}/{len(citations)}] {symbol} {key}: score={scored['score']:.2f} "
              f"(title={scored['title_sim']:.2f} auth={scored['author_sim']:.2f} year={scored['year_sim']:.2f}) "
              f"{v} | {reason[:40]}")

    print()
    print("─" * 60)
    print(f"Results:")
    print(f"  ✓ verified:               {verified:5d} ({verified/len(citations)*100:.1f}%)")
    print(f"  ? needs_review:            {needs_review:5d} ({needs_review/len(citations)*100:.1f}%)")
    print(f"  ✗ suspected_hallucination: {suspected:5d} ({suspected/len(citations)*100:.1f}%)")
    print(f"  Total:                    {len(citations):5d}")

    # Save verified results
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n✓ Saved: {out_path}")

    # Save needs_review to CSV for human check
    review_path = Path(args.review_csv)
    needs_review_cits = [
        r for r in results.values() if r["verdict"] == "needs_review"
    ]
    if needs_review_cits:
        with open(review_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "key", "arxiv_id", "citation_raw", "claimed_title",
                "claimed_authors", "claimed_year", "doi",
                "openalex_title", "openalex_authors", "openalex_year",
                "title_sim", "author_sim", "year_sim", "score",
                "final_verdict",
            ])
            writer.writeheader()
            for r in sorted(needs_review_cits, key=lambda x: x["score"]):
                oa = r.get("openalex") or {}
                writer.writerow({
                    "key": r["_key"],
                    "arxiv_id": r["_arxiv_id"],
                    "citation_raw": r["_raw"],
                    "claimed_title": r["_claimed_title"],
                    "claimed_authors": "; ".join(r["_claimed_authors"]),
                    "claimed_year": r["_claimed_year"],
                    "doi": r["_doi"],
                    "openalex_title": oa.get("title", ""),
                    "openalex_authors": "; ".join(oa.get("authors", [])),
                    "openalex_year": oa.get("publication_year", ""),
                    "title_sim": r["title_sim"],
                    "author_sim": r["author_sim"],
                    "year_sim": r["year_sim"],
                    "score": r["score"],
                    "final_verdict": "",
                })
        print(f"  Review CSV: {review_path} ({len(needs_review_cits)} citations)")
        print(f"  Fill in 'final_verdict': verified | suspected_hallucination | metadata_error")


def _extract_title(raw: str) -> str:
    """Extract title from raw citation text."""
    # In quotes: "Title"
    m = re.search(r'"([^"]{10,200})"', raw)
    if m:
        return m.group(1).strip()
    # After year in parens or after period
    m = re.search(r'\d{4}\)\.\s+([^.]+)', raw)
    if m:
        return m.group(1).strip()
    # In brackets or plain
    m = re.search(r'[\d]\s+(.+?)(?:\.|,)', raw)
    if m:
        return m.group(1).strip()[:200]
    return raw[:100]


def _parse_authors(val) -> list:
    """Parse authors from various formats (string, list, None)."""
    if not val:
        return []
    if isinstance(val, list):
        return [str(a) for a in val if a]
    if isinstance(val, str):
        if not val.strip():
            return []
        # Split on common separators
        return [a.strip() for a in re.split(r'[;,&]| and ', val) if a.strip()]
    return []


def _extract_authors(raw: str) -> list:
    """Extract author names from raw citation text."""
    # Pattern: "Last, First" or "First Last" before year/title
    # "Smith, J. and Jones, B. and Wang, X."
    authors = []
    # Before first period + year (e.g., "Smith, J., & Jones, B. (2020)")
    m = re.match(r'([^)]+?)', raw)
    if m:
        segment = m.group(1)
        parts = re.split(r',\s*|\s+and\s+|&|;', segment)
        for p in parts:
            p = p.strip()
            if 2 < len(p) < 60 and not re.match(r'^\d', p):
                authors.append(p)
    return authors[:6]  # limit to first 6


def _extract_year(raw: str) -> str | None:
    """Extract year from raw citation text."""
    m = re.search(r'\b(19|20)\d{2}\b', raw)
    return m.group(0) if m else None


def _extract_doi(raw: str) -> str | None:
    """Extract DOI from raw citation text."""
    m = re.search(r'(?:https?://)?(?:dx\.)?doi\.org/(10\.\S+)', raw)
    if m:
        return m.group(1).rstrip(",.>;")
    m = re.search(r'doi:\s*(10\.\S+)', raw, re.I)
    if m:
        return m.group(1).rstrip(",.>;")
    return None


if __name__ == "__main__":
    main()
