#!/usr/bin/env python3
"""
Step 2 (fallback): Extract citations from PDFs using PyMuPDF + regex.
NO external service needed — works offline.

Usage:
    python scripts/collect_dataset/02_extract_citations_mupdf.py \
        --pdf-dir data/raw/pdf \
        --output data/citations.json

Output format is identical to step 2 (GROBID version).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


APA_YEAR = re.compile(r"\b(19|20)\d{2}\b")
APA_CITATION = re.compile(
    r"(?P<authors>[A-Z][a-zA-ZÀ-ÿ'-,]+(?:\s+(?:van\s+|von\s+|de\s+|la\s+)?[A-Z][a-zA-ZÀ-ÿ'-]+)*)"
    r"[\s,]+(?:&\s+[^,]+,\s+)?(?P<year>\d{4})\b",
    re.U,
)
IEEE_NUM = re.compile(r"\[\d+\]\s*")
IEEE_CITATION = re.compile(
    r"(?P<authors>[A-Z][a-zA-ZÀ-ÿ'-]+(?:\s*,?\s*(?:and|&)\s*[A-Z][a-zA-ZÀ-ÿ'-]+)*)"
    r"[\s,]+[\"\"']*(?P<title>[^\"\"'\n,]+)[\"\"']*[\s,]+\d{4}",
    re.U,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract citations from PDFs using PyMuPDF")
    p.add_argument("--pdf-dir", "-i", required=True)
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    return p.parse_args()


def extract_page_text(pdf_path: Path) -> str:
    """Extract text from all pages using PyMuPDF."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        pages.append(text)
    doc.close()
    return "\n".join(pages)


def find_references_section(text: str) -> str:
    """Isolate the references/bibliography section."""
    # Common header patterns for references section
    patterns = [
        r"(?im)^(references|bibliography|works cited|literature cited)\s*$",
        r"(?im)^\d+\.\s*(?:references|bibliography)\s*$",
        r"(?im)^—\s*(?:references|bibliography)\s*—\s*$",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            start = m.start()
            # Skip section number
            after = re.match(r"\d+\.\s*", text[start + m.end():])
            if after:
                start += m.end() + after.end()
            return text[start:]

    # Fallback: return last 40% of document (references are usually at end)
    cutoff = int(len(text) * 0.6)
    return text[cutoff:]


def split_entries(text: str) -> list[str]:
    """Split references section into individual entries."""
    # IEEE style: [1] Title...
    entries = re.split(r"\n(?=\[\d+\])", text)
    if len(entries) > 1:
        return [e.strip() for e in entries if e.strip()]

    # APA style: Author, A. (Year). Title
    # Split on double newline or on year pattern at start of line
    entries = re.split(r"\n(?=[A-Z][a-zA-ZÀ-ÿ]+[^,\n]*,?\s*(?:&|,)\s*[A-Z])", text)
    if len(entries) > 1:
        return [e.strip() for e in entries if e.strip()]

    # Fallback: split on double newline
    return [e.strip() for e in re.split(r"\n\n+", text) if e.strip()]


def normalize_entry(text: str) -> str:
    """Collapse multi-line entries into single lines."""
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_style(text: str) -> str:
    """Guess citation style from formatting."""
    has_brackets = bool(re.search(r"\[\d+\]", text))
    has_paren_year = bool(re.search(r"\([12]\d{3}\)", text))
    if has_brackets and not has_paren_year:
        return "IEEE_LIKE"
    if has_paren_year and not has_brackets:
        return "APA_LIKE"
    return "UNKNOWN"


def extract_citation(text: str) -> dict:
    """Parse one citation entry into structured fields."""
    norm = normalize_entry(text)
    style = detect_style(norm)

    authors = []
    year = None
    title = None

    if style == "APA_LIKE":
        m = APA_CITATION.search(norm)
        if m:
            authors_str = m.group("authors")
            year = m.group("year")
            authors = [a.strip() for a in re.split(r",\s*&\s*|&\s*|,\s*", authors_str) if a.strip()]
            # Title is usually after year or in quotes
            title_m = re.search(rf'[{chr(34)}{chr(39)}](.+?)[{chr(34)}{chr(39)}]', norm)
            if title_m:
                title = title_m.group(1)
            else:
                after_year = norm[m.end():].strip()
                parts = re.split(r"\.\s+", after_year)
                title = parts[0][:200] if parts else None

    elif style == "IEEE_LIKE":
        # Extract title in quotes or italics
        title_m = re.search(r'"([^"]+)"', norm) or re.search(r'<i>([^<]+)</i>', norm)
        if title_m:
            title = title_m.group(1)
        year_m = APA_YEAR.search(norm)
        if year_m:
            year = year_m.group(0)

    return {
        "raw_text": norm[:500],
        "citation_type": "reference_list",
        "style": style,
        "authors": authors,
        "year": year,
        "title": title,
        "venue": None,
        "doi": None,
        "url": None,
        "page_num": 0,
        "confidence": 0.5,
    }


def process_pdf(pdf_path: Path) -> list[dict]:
    """Extract all citations from one PDF."""
    try:
        text = extract_page_text(pdf_path)
    except Exception as e:
        print(f"    ✗ {pdf_path.name}: {e}")
        return []

    ref_text = find_references_section(text)
    if not ref_text or len(ref_text) < 50:
        print(f"    ! no references section found")
        return []

    entries = split_entries(ref_text)
    citations = []
    for entry in entries:
        if len(entry) < 20:
            continue
        cit = extract_citation(entry)
        if cit.get("raw_text"):
            citations.append(cit)

    return citations


def main() -> None:
    args = parse_args()
    pdf_dir = Path(args.pdf_dir)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {pdf_dir}")
        sys.exit(1)
    if args.limit > 0:
        pdfs = pdfs[: args.limit]
    print(f"Found {len(pdfs)} PDFs in {pdf_dir}")

    # Load existing
    if out_path.exists() and not args.overwrite:
        existing = {p["arxiv_id"]: p for p in json.loads(out_path.read_text())}
    else:
        existing = {}

    results = []
    for i, pdf_path in enumerate(pdfs, 1):
        arxiv_id = pdf_path.stem
        print(f"[{i}/{len(pdfs)}] {arxiv_id}: ", end="", flush=True)
        if arxiv_id in existing and not args.overwrite:
            print("skipped (exists)")
            results.append(existing[arxiv_id])
            continue

        import time
        t0 = time.time()
        citations = process_pdf(pdf_path)
        elapsed = time.time() - t0
        result = {"arxiv_id": arxiv_id, "pdf": str(pdf_path), "citations": citations}
        results.append(result)
        print(f"{len(citations)} citations ({elapsed:.1f}s)")

    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    total_cits = sum(len(r["citations"]) for r in results)
    empty = sum(1 for r in results if not r["citations"])
    print(f"\n✓ Processed {len(results)} PDFs, {total_cits} citations")
    if empty:
        print(f"  ({empty} PDFs had no citations found)")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
