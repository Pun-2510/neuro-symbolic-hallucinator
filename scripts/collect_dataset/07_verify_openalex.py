#!/usr/bin/env python3
"""
Step 7: Citation verification via OpenAlex + Semantic Scholar (parallel).

Uses both APIs for maximum coverage:
  - OpenAlex (https://api.openalex.org) — free, no key
  - Semantic Scholar (https://api.semanticscholar.org) — free, no key (rate: 100/s)

Strategy per citation:
  1. DOI lookup on both APIs simultaneously
  2. Title search on best available API
  3. Take the best result from either source

Usage:
    pip install aiohttp
    python scripts/collect_dataset/07_verify_openalex.py \\
        --input data/citations_full_enriched.json \\
        --output data/citations_verified.json
"""

from __future__ import annotations

import asyncio
import argparse
import csv
import json
import re
import time
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import aiohttp

# ─── Config ────────────────────────────────────────────────────────────────
THRESHOLD_VERIFIED = 0.85
THRESHOLD_SUSPECTED = 0.50
CONCURRENCY = 3       # requests/second per API
REQUEST_DELAY = 0.3   # seconds between batches
HEADERS = {"User-Agent": "EssayIntegrityChecker/1.0 (mailto:student@tdtu.edu.vn)"}

# ─── Scoring ────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", s.lower())).strip()


def title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    na, nb = normalize(a), normalize(b)
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.85
    return SequenceMatcher(None, na, nb).ratio()


def author_overlap(claimed: list, found: list) -> float:
    if not claimed and not found:
        return 0.5
    if not claimed or not found:
        return 0.0
    nc = {norm_name(n) for n in claimed if n}
    nf = {norm_name(n) for n in found if n}
    if not nc or not nf:
        return 0.0
    return len(nc & nf) / len(nc | nf)


def norm_name(name: str) -> str:
    if not name:
        return ""
    parts = name.lower().split()
    if "," in name:
        surname = parts[0].rstrip(",")
        initial = parts[1][0] if len(parts) > 1 else ""
    else:
        surname = parts[-1] if parts else ""
        initial = parts[0][0] if len(parts) > 1 else ""
    return f"{surname} {initial}".strip()


def year_match(c: str, f: str | None) -> float:
    if not c:
        return 0.5
    if not f:
        return 0.0
    try:
        diff = abs(int(c) - int(str(f)[:4]))
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.7
        elif diff <= 3:
            return 0.3
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def score_result(found: dict | None, claimed_title: str = "", claimed_authors: list = None, claimed_year: str = "") -> dict:
    """Score a found result against claimed citation."""
    if claimed_authors is None:
        claimed_authors = []
    if not found:
        return {"score": 0.0, "title_sim": 0.0, "author_sim": 0.0, "year_sim": 0.0, "matched_fields": [], "verdict": "suspected_hallucination"}

    ts = title_similarity(claimed_title, found.get("title", ""))
    aus = author_overlap(claimed_authors, found.get("authors", []))
    ys = year_match(claimed_year, found.get("year"))

    score = ts * 0.5 + aus * 0.3 + ys * 0.2
    matched = []
    if ts >= 0.8:
        matched.append("title")
    if aus >= 0.5:
        matched.append("authors")
    if ys >= 0.7:
        matched.append("year")

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
    }


# ─── Extractors ────────────────────────────────────────────────────────────

def extract_title(raw: str) -> str | None:
    if not raw:
        return None
    # Quoted title
    m = re.search(r'"([^"]{15,300})"', raw)
    if m:
        return m.group(1).strip()
    # After year+period: "...(YYYY). Title. Venue"
    m = re.search(r'\d{4}\)\.\s+(.+?)(?:\.\s*(?:arXiv|Preprint)|,\s*\d{4})', raw, re.DOTALL)
    if m:
        t = m.group(1).strip().rstrip(".")
        if len(t) > 15:
            return t
    # IEEE: "[N] Authors. Title. Venue"
    m = re.search(r'^\[[\d]+\]\s*[^.]+\.\s+(.+?)(?:\s*arXiv|,\s*\d)', raw, re.DOTALL)
    if m:
        t = m.group(1).strip().rstrip(".")
        if len(t) > 15:
            return t
    # Fallback: before known source markers
    for marker in ['arXiv', 'arxiv', 'NeurIPS', 'ICML', 'ACL', 'EMNLP', 'NAACL']:
        idx = raw.find(marker)
        if idx > 50:
            segment = raw[:idx].strip()
            ld = segment.rfind('. ')
            if ld > 30:
                cand = segment[ld+1:].strip().rstrip(".")
                if len(cand) > 15:
                    return cand
    return None


def extract_year(raw: str) -> str | None:
    m = re.search(r"\b(19|20)\d{2}\b", raw)
    return m.group(0) if m else None


def extract_doi(raw: str) -> str | None:
    m = re.search(r"(?:https?://)?(?:dx\.)?doi\.org/(10\.\S+)", raw)
    if m:
        return m.group(1).rstrip(",.>;")
    m = re.search(r"doi:\s*(10\.\S+)", raw, re.I)
    if m:
        return m.group(1).rstrip(",.>;")
    return None


def _extract_authors(raw: str) -> list:
    """Extract author names from raw citation text.

    Pattern: everything before the TITLE (stop at first major period
    followed by a capitalized word, or at arXiv/journal markers).
    Then split on comma/ampersand/and.
    """
    if not raw:
        return []
    # Remove leading [N] bracket
    text = re.sub(r'^\[[\d]+\]\s*', '', raw)

    # Find where title starts: first period followed by a capitalized word
    # or an arXiv/journal marker
    title_stops = [
        'arxiv', 'coRR', 'neurIPS', 'icml', 'acl', 'emnlp', 'naacl',
        'journal', 'proceedings', 'conference',
    ]
    end_idx = len(text)
    lower = text.lower()
    for stop in title_stops:
        idx = lower.find(stop)
        if idx > 10:
            end_idx = min(end_idx, idx)

    # Also stop at first period followed by capitalized word (likely title start)
    m = re.search(r'\.\s+[A-Z][a-z]', text)
    if m and m.start() < end_idx:
        end_idx = min(end_idx, m.start())

    author_part = text[:end_idx].strip()

    # Split on ", and " first (most reliable for IEEE style)
    parts = re.split(r',\s+and\s+', author_part)
    for part in parts[:]:
        # Then split each part on comma (within an author group)
        sub = re.split(r',\s*(?!and\s)', part)
        parts.remove(part)
        parts.extend(sub)
    # Also split remaining parts on "&" or ";"
    new_parts = []
    for p in parts:
        if '&' in p or ';' in p:
            new_parts.extend(re.split(r'\s*&\s*|\s*;\s*', p))
        else:
            new_parts.append(p)
    parts = new_parts

    authors = []
    seen = set()
    for p in parts:
        p = re.sub(r'\s+', ' ', p.strip()).strip('.,; &')
        if len(p) < 3 or re.match(r'^\d', p):
            continue
        if 'http' in p.lower() or 'doi' in p.lower():
            continue
        if p.lower() in seen:
            continue
        seen.add(p.lower())
        authors.append(p)
        if len(authors) >= 6:
            break

    return authors


# ─── API Clients ───────────────────────────────────────────────────────────

class OpenAlexClient:
    """OpenAlex API with caching and retry."""

    def __init__(self, session: aiohttp.ClientSession, cache: dict):
        self.session = session
        self.cache = cache  # doi_lower -> result

    async def lookup_doi(self, doi: str) -> dict | None:
        if not doi:
            return None
        key = doi.lower()
        if key in self.cache:
            return self.cache[key]
        try:
            url = f"https://api.openalex.org/works?filter=doi:{doi}"
            data = await self._get(url)
            if not data:
                self.cache[key] = None
                return None
            results = data.get("results", [])
            if not results:
                self.cache[key] = None
                return None
            result = self._parse_work(results[0])
            result["doi"] = doi
            self.cache[key] = result
            return result
        except Exception:
            self.cache[key] = None
            return None

    async def lookup_title(self, title: str, claimed_title: str, claimed_authors: list, claimed_year: str) -> dict | None:
        if not title or len(title) < 15:
            return None
        try:
            q = "+".join(title.split()[:6])
            url = f"https://api.openalex.org/works?search={q}&per_page=3"
            data = await self._get(url)
            if not data:
                return None
            best = None
            best_score = 0.0
            for w in data.get("results", []):
                r = self._parse_work(w)
                r["claimed_title"] = claimed_title
                r["claimed_authors"] = claimed_authors
                r["claimed_year"] = claimed_year
                ts = title_similarity(claimed_title, r["title"])
                if ts > best_score:
                    best_score = ts
                    best = r
            return best
        except Exception:
            return None

    async def _get(self, url: str) -> dict | None:
        for attempt in range(3):
            try:
                async with self.session.get(
                    url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if resp.status != 200:
                        return None
                    return await resp.json()
            except Exception:
                await asyncio.sleep(1)
                continue
        return None

    def _parse_work(self, w: dict) -> dict:
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in w.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        location = w.get("primary_location") or {}
        source = location.get("source") or {}
        return {
            "title": w.get("title", ""),
            "authors": authors,
            "year": str(w.get("publication_year", "")),
            "venue": source.get("display_name", ""),
            "doi": w.get("doi", ""),
            "openalex_id": w.get("id", ""),
            "cited_by_count": w.get("cited_by_count", 0),
            "source": "openalex",
        }


class SemanticScholarClient:
    """Semantic Scholar Graph API — free, no key needed."""

    FIELDS = "title,authors,year,externalIds,venue,citationCount"

    def __init__(self, session: aiohttp.ClientSession, cache: dict):
        self.session = session
        self.cache = cache  # doi_lower -> result

    async def lookup_doi(self, doi: str) -> dict | None:
        if not doi:
            return None
        key = doi.lower()
        if key in self.cache:
            return self.cache[key]
        try:
            url = (
                f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
                f"?fields={self.FIELDS}"
            )
            data = await self._get(url)
            if not data:
                self.cache[key] = None
                return None
            result = self._parse(data)
            result["doi"] = doi
            self.cache[key] = result
            return result
        except Exception:
            self.cache[key] = None
            return None

    async def lookup_title(self, title: str, claimed_title: str, claimed_authors: list, claimed_year: str) -> dict | None:
        if not title or len(title) < 15:
            return None
        try:
            url = (
                "https://api.semanticscholar.org/graph/v1/paper/search"
                f"?query={self._q(title)}&limit=3&fields={self.FIELDS}"
            )
            data = await self._get(url)
            if not data or not data.get("data"):
                return None
            best = None
            best_score = 0.0
            for paper in data["data"]:
                r = self._parse(paper)
                r["claimed_title"] = claimed_title
                r["claimed_authors"] = claimed_authors
                r["claimed_year"] = claimed_year
                ts = title_similarity(claimed_title, r["title"])
                if ts > best_score:
                    best_score = ts
                    best = r
            return best
        except Exception:
            return None

    async def _get(self, url: str) -> dict | None:
        for attempt in range(3):
            try:
                async with self.session.get(
                    url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if resp.status == 404:
                        return None
                    if resp.status != 200:
                        return None
                    return await resp.json()
            except Exception:
                await asyncio.sleep(1)
                continue
        return None

    def _parse(self, p: dict) -> dict:
        authors = [a.get("name", "") for a in p.get("authors", []) if a.get("name")]
        return {
            "title": p.get("title", ""),
            "authors": authors,
            "year": str(p.get("year", "")),
            "venue": p.get("venue", ""),
            "doi": (p.get("externalIds") or {}).get("DOI", ""),
            "openalex_id": (p.get("externalIds") or {}).get("OpenAlex", ""),
            "cited_by_count": p.get("citationCount", 0),
            "source": "semantic_scholar",
        }

    @staticmethod
    def _q(s: str) -> str:
        return "+".join(s.split()[:6])


# ─── Citation worker ──────────────────────────────────────────────────────

async def verify_one(
    clients: tuple[OpenAlexClient, SemanticScholarClient],
    sem: asyncio.Semaphore,
    cit: dict,
    idx: int,
    total: int,
) -> dict:
    async with sem:
        raw = (cit.get("raw_text", "") or cit.get("citation_raw", ""))[:300]
        title_c = extract_title(raw)
        authors_c = _extract_authors(raw)
        year_c = extract_year(raw)
        doi = extract_doi(raw)

        # Use enrichment-extracted title/year (reliable) before crossref
        # Crossref enrichment is buggy for arXiv papers; use extracted fields
        enriched_title = cit.get("title")   # from pdf extraction
        enriched_year = cit.get("year")     # from pdf extraction
        crossref = cit.get("crossref") or {}

        if not title_c:
            title_c = enriched_title or crossref.get("title")
        if not authors_c:
            authors_c = _extract_authors(raw) if raw else []   # re-extract properly
            if not authors_c:
                authors_c = [str(a) for a in (cit.get("authors") or []) if a]
        if not year_c:
            year_c = enriched_year or crossref.get("year") or cit.get("year")
        if not doi:
            doi = extract_doi(raw) if raw else None  # re-extract
            if not doi:
                doi = cit.get("doi") or crossref.get("doi")

        oa_client, ss_client = clients

        best = None
        reason = ""

        # ── Step 1: Title search (most reliable for arXiv papers) ──
        if title_c:
            await asyncio.sleep(REQUEST_DELAY)
            title_tasks = [
                oa_client.lookup_title(title_c, title_c, authors_c, year_c),
                ss_client.lookup_title(title_c, title_c, authors_c, year_c),
            ]
            title_results = await asyncio.gather(*title_tasks)
            title_oa, title_ss = title_results
            if title_oa and title_ss:
                ts_oa = title_similarity(title_c, title_oa["title"])
                ts_ss = title_similarity(title_c, title_ss["title"])
                best = title_oa if ts_oa >= ts_ss else title_ss
                reason = "title_both"
            elif title_oa:
                best = title_oa
                reason = "title_oa"
            elif title_ss:
                best = title_ss
                reason = "title_ss"

        # ── Step 2: DOI lookup (only if title search failed) ──
        if not best and doi:
            doi_tasks = [
                oa_client.lookup_doi(doi),
                ss_client.lookup_doi(doi),
            ]
            doi_results = await asyncio.gather(*doi_tasks)
            doi_oa, doi_ss = doi_results
            if doi_oa:
                best = doi_oa
                reason = "doi_oa"
            elif doi_ss:
                best = doi_ss
                reason = "doi_ss"

        # Score
        scored = score_result(best, title_c or "", authors_c, year_c)
        scored["_key"] = f"{cit['_arxiv_id']}_{cit['_idx']+1:03d}"
        scored["_arxiv_id"] = cit["_arxiv_id"]
        scored["_raw"] = raw[:150]
        scored["_claimed_title"] = title_c
        scored["_claimed_authors"] = authors_c
        scored["_claimed_year"] = year_c
        scored["_doi"] = doi
        scored["_reason"] = reason
        scored["_best_result"] = best

        if idx % 50 == 0:
            print(f"[{idx:4d}/{total}] processed")

        return scored


# ─── Main ─────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify citations via OpenAlex + Semantic Scholar")
    p.add_argument("--input", "-i", default="data/citations_full_enriched.json")
    p.add_argument("--output", "-o", default="data/citations_verified.json")
    p.add_argument("--review-csv", default="data/citations_needs_review.csv")
    p.add_argument("--concurrency", type=int, default=CONCURRENCY)
    p.add_argument("--limit", type=int, default=0, help="0=all")
    return p.parse_args()


async def run(args: argparse.Namespace) -> None:
    raw_data = json.loads(Path(args.input).read_text())

    citations = []
    for arxiv_id, paper in raw_data.items():
        for i, cit in enumerate(paper.get("citations", [])):
            citations.append({**cit, "_arxiv_id": arxiv_id, "_idx": i})

    if args.limit > 0:
        citations = citations[:args.limit]

    total = len(citations)
    print(f"Verifying {total} citations via OpenAlex + Semantic Scholar...")
    print(f"Threshold: verified >= {THRESHOLD_VERIFIED}, suspected < {THRESHOLD_SUSPECTED}")
    print()

    oa_cache: dict = {}
    ss_cache: dict = {}
    sem = asyncio.Semaphore(args.concurrency)

    t0 = time.time()

    async with aiohttp.ClientSession() as session:
        oa_client = OpenAlexClient(session, oa_cache)
        ss_client = SemanticScholarClient(session, ss_cache)
        clients = (oa_client, ss_client)

        tasks = [
            verify_one(clients, sem, cit, i, total)
            for i, cit in enumerate(citations)
        ]
        results_list = await asyncio.gather(*tasks)

    elapsed = time.time() - t0
    results = {r["_key"]: r for r in results_list}

    counts = Counter(r["verdict"] for r in results.values())
    verified = counts.get("verified", 0)
    suspected = counts.get("suspected_hallucination", 0)
    needs_review = counts.get("needs_review", 0)

    print()
    print("─" * 55)
    print(f"Elapsed: {elapsed:.1f}s ({total/elapsed:.1f} citations/sec)")
    print(f"Results:")
    print(f"  ✓ verified:                {verified:5d} ({verified/total*100:.1f}%)")
    print(f"  ? needs_review:            {needs_review:5d} ({needs_review/total*100:.1f}%)")
    print(f"  ✗ suspected_hallucination: {suspected:5d} ({suspected/total*100:.1f}%)")
    print(f"  Total:                    {total:5d}")

    Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n✓ Saved: {args.output}")

    # CSV for human review
    needs = [r for r in results.values() if r["verdict"] == "needs_review"]
    if needs:
        with open(args.review_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "key", "arxiv_id", "citation_raw", "claimed_title",
                "claimed_authors", "claimed_year", "doi",
                "found_title", "found_authors", "found_year",
                "title_sim", "author_sim", "year_sim", "score",
                "final_verdict",
            ])
            writer.writeheader()
            for r in sorted(needs, key=lambda x: x["score"]):
                b = r.get("_best_result") or {}
                writer.writerow({
                    "key": r["_key"],
                    "arxiv_id": r["_arxiv_id"],
                    "citation_raw": r["_raw"],
                    "claimed_title": r["_claimed_title"] or "",
                    "claimed_authors": "; ".join(r["_claimed_authors"]),
                    "claimed_year": r["_claimed_year"] or "",
                    "doi": r["_doi"] or "",
                    "found_title": b.get("title", ""),
                    "found_authors": "; ".join(b.get("authors", [])),
                    "found_year": b.get("year", ""),
                    "title_sim": r["title_sim"],
                    "author_sim": r["author_sim"],
                    "year_sim": r["year_sim"],
                    "score": r["score"],
                    "final_verdict": "",
                })
        print(f"  Review CSV: {args.review_csv} ({len(needs)} citations)")

    # Summary JSON
    summary = {
        r["_key"]: {
            "verdict": r["verdict"],
            "score": r["score"],
            "matched_fields": r.get("matched_fields", []),
            "reason": r["_reason"],
            "best_result": {
                "title": (r["_best_result"] or {}).get("title", ""),
                "authors": (r["_best_result"] or {}).get("authors", []),
                "year": (r["_best_result"] or {}).get("year", ""),
                "doi": (r["_best_result"] or {}).get("doi", ""),
                "source": (r["_best_result"] or {}).get("source", ""),
            },
        }
        for r in results.values()
    }
    summary_path = Path(args.output).with_name("citations_verdict_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"  Summary: {summary_path}")


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")


if __name__ == "__main__":
    main()
