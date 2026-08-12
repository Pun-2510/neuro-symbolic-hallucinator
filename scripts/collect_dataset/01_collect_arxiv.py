#!/usr/bin/env python3
"""
Step 1: Collect arXiv papers as PDFs (direct download — no API rate limit).

Usage:
    python scripts/collect_dataset/01_collect_arxiv.py \
        --output data/raw/pdf \
        --n 50 \
        --search "cs.CL"

        python scripts/collect_dataset/01_collect_arxiv.py \
        --ids 1810.04805 1706.03762 \
        --output data/raw/pdf

Approach: Download PDFs directly from arXiv PDF server (no API key needed).
Metadata: scrape from arXiv abstract pages (1 request per paper only).

arXiv rate limit: ~2-3 connections per second max.
Use --delay 1 between PDF downloads.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

import defusedxml.ElementTree as ET

ARXIV_ABS = "https://arxiv.org/abs/"
ARXIV_PDF = "https://arxiv.org/pdf/"
USER_AGENT = "Mozilla/5.0 (compatible; EssayIntegrityChecker/1.0)"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download arXiv papers as PDFs")
    p.add_argument("--output", "-o", default="data/raw/pdf", help="Output dir for PDFs")
    p.add_argument("--n", type=int, default=50, help="Number of papers (search mode)")
    p.add_argument("--search", "-s", help="arXiv search query (e.g. 'cs.CL' or 'all:machine learning')")
    p.add_argument("--ids", nargs="+", help="Specific arXiv IDs (e.g. 2301.12345)")
    p.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    p.add_argument("--overwrite", action="store_true", help="Re-download existing files")
    return p.parse_args()


def _get(url: str, timeout: int = 30) -> bytes | None:
    """GET URL with retry on 429."""
    for attempt in range(1, 4):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except HTTPError as e:
            if e.code == 429:
                print(f"    Rate limited. Waiting {10 * attempt}s...")
                time.sleep(10 * attempt)
                continue
            print(f"    HTTP {e.code}: {url}")
            return None
        except Exception as e:
            print(f"    Error: {e}")
            return None
    return None


def _scrape_abstract(arxiv_id: str) -> dict:
    """Scrape metadata from arXiv abstract page (1 request, no API needed)."""
    url = f"{ARXIV_ABS}{arxiv_id}"
    html = _get(url, timeout=15)
    if not html:
        return {"arxiv_id": arxiv_id, "title": None, "authors": [], "published": None,
                "doi": None, "categories": [], "summary": None, "pdf_url": url}

    text = html.decode("utf-8", errors="replace")

    # Extract title: <h1 class="title mathjax">Title</h1>
    title = None
    m = re.search(r'<h1[^>]*class="title[^"]*"[^>]*>(.*?)</h1>', text, re.DOTALL)
    if m:
        title = re.sub(r"^(Title:|Tiêu đề:)\s*", "", m.group(1), flags=re.IGNORECASE)
        title = re.sub(r"\s+", " ", title).strip()

    # Extract authors: <div class="authors">...</div>
    authors = []
    m = re.search(r'<div[^>]*class="authors"[^>]*>(.*?)</div>', text, re.DOTALL)
    if m:
        for a in re.findall(r'<a[^>]*>([^<]+)</a>', m.group(1)):
            a = a.strip()
            if a and not a.startswith("mailto:"):
                authors.append(a)

    # Extract submitted date
    published = None
    m = re.search(r'Submitted on ([^(]+)', text)
    if m:
        published = m.group(1).strip()

    # Extract DOI
    doi = None
    m = re.search(r'DOI:\s*<a[^>]*>([^<]+)</a>', text)
    if m:
        doi = m.group(1).strip()

    # Extract categories
    categories = []
    for m in re.finditer(r'<a[^>]*href="/abs/([a-z]+\.[A-Z]+)"[^>]*>([^<]+)</a>', text):
        cat = m.group(2).strip()
        if cat and cat not in categories:
            categories.append(cat)

    # Extract summary/abstract
    summary = None
    m = re.search(r'<blockquote[^>]*class="abstract[^"]*"[^>]*>(.*?)</blockquote>', text, re.DOTALL)
    if m:
        summary = re.sub(r"^(Abstract|Summary):\s*", "", m.group(1), flags=re.IGNORECASE)
        summary = re.sub(r"<[^>]+>", "", summary)
        summary = re.sub(r"\s+", " ", summary).strip()

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "published": published,
        "doi": doi,
        "categories": categories[:5],
        "summary": summary,
        "pdf_url": f"{ARXIV_PDF}{arxiv_id}.pdf",
    }


def download_pdf(arxiv_id: str, out_dir: Path, delay: float, overwrite: bool) -> Path | None:
    """Download PDF for one arXiv ID."""
    out_path = out_dir / f"{arxiv_id}.pdf"
    if out_path.exists() and not overwrite:
        return out_path

    pdf_url = f"{ARXIV_PDF}{arxiv_id}.pdf"
    content = _get(pdf_url, timeout=120)
    if content:
        out_path.write_bytes(content)
        kb = len(content) // 1024
        print(f"  ✓ {arxiv_id}.pdf ({kb} KB)")
        time.sleep(delay)
        return out_path
    return None


def search_arxiv_ids(query: str, max_results: int, delay: float) -> list[str]:
    """Find arXiv IDs via OpenSearch-like HTML page scraping."""
    import html as html_lib
    ids = []
    page = 0
    while len(ids) < max_results:
        start = page * 50
        url = f"https://export.arxiv.org/api/query?search_query={query}&start={start}&max_results=50&sortBy=submittedDate&sortOrder=descending"
        data = _get(url, timeout=60)
        if not data:
            break
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)
        if not entries:
            break
        for entry in entries:
            eid = entry.find("atom:id", ns)
            if eid is not None and eid.text:
                aid = eid.text.rsplit("/", 1)[-1]
                ids.append(aid)
                if len(ids) >= max_results:
                    break
        if len(entries) < 50:
            break
        page += 1
        time.sleep(delay)
    return ids[:max_results]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Get list of arXiv IDs
    if args.ids:
        arxiv_ids = [a.strip().replace("https://arxiv.org/abs/", "").replace("arXiv:", "") for a in args.ids]
    elif args.search:
        q = args.search.replace(" ", "+")
        print(f"[1/3] Searching arXiv: {args.search!r} → {args.n} papers...")
        arxiv_ids = search_arxiv_ids(q, args.n, args.delay)
        print(f"  Found {len(arxiv_ids)} arXiv IDs")
    else:
        print("Error: specify --search or --ids")
        sys.exit(1)

    if not arxiv_ids:
        print("No arXiv IDs found.")
        sys.exit(1)

    # Scrape metadata
    print(f"[2/3] Scraping metadata for {len(arxiv_ids)} papers...")
    papers = []
    for i, aid in enumerate(arxiv_ids, 1):
        print(f"  [{i}/{len(arxiv_ids)}] {aid}: ", end="", flush=True)
        meta = _scrape_abstract(aid)
        papers.append(meta)
        print(f"{meta.get('title', '???')[:60]}")
        time.sleep(args.delay)

    # Download PDFs
    print(f"\n[3/3] Downloading {len(papers)} PDFs → {out_dir}/")
    for i, paper in enumerate(papers, 1):
        aid = paper["arxiv_id"]
        print(f"  [{i}/{len(papers)}] {aid}: ", end="", flush=True)
        path = download_pdf(aid, out_dir, args.delay, args.overwrite)
        if path:
            paper["pdf_path"] = str(path.relative_to(out_dir.parent))
        else:
            paper["pdf_path"] = None

    # Save metadata
    meta_path = out_dir.parent / "arxiv_metadata.json"
    meta_path.write_text(json.dumps(papers, indent=2, ensure_ascii=False))
    downloaded = sum(1 for p in papers if p.get("pdf_path"))
    print(f"\n✓ Downloaded {downloaded}/{len(papers)} PDFs")
    print(f"  Metadata: {meta_path}")
    print(f"  PDFs: {out_dir}/")


if __name__ == "__main__":
    main()
