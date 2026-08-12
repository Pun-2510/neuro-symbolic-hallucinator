#!/usr/bin/env python3
"""
Step 2: Extract citations from PDFs using GROBID.

Usage:
    python scripts/collect_dataset/02_extract_citations.py \
        --pdf-dir data/raw/pdf \
        --output data/citations.json \
        --grobid http://localhost:8070

Requires: GROBID running at --grobid URL.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

GROBID_EXTRACT = "/api/processReferences"

DEFAULT_FIELDS = [
    "raw_text", "citation_type", "style",
    "authors", "year", "title", "venue",
    "doi", "url", "page_num", "confidence",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract citations from PDFs via GROBID")
    p.add_argument("--pdf-dir", "-i", required=True, help="Directory containing PDFs")
    p.add_argument("--output", "-o", required=True, help="Output JSON file")
    p.add_argument("--grobid", default="http://localhost:8070", help="GROBID base URL")
    p.add_argument("--overwrite", action="store_true", help="Re-process existing")
    p.add_argument("--limit", type=int, default=0, help="Limit number of PDFs (0=all)")
    return p.parse_args()


def extract_pdf(pdf_path: Path, grobid_url: str) -> dict | None:
    """Send PDF to GROBID, extract references section. Returns list of CitationDicts."""
    url = f"{grobid_url}{GROBID_EXTRACT}References"
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        boundary = "----formdata" + str(int(time.time()))
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="input"; filename="{pdf_path.name}"'
            f"\r\nContent-Type: application/pdf\r\n\r\n"
        ).encode() + pdf_bytes + f"\r\n--{boundary}--\r\n".encode()
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/xml",
            },
        )
        with urlopen(req, timeout=120) as resp:
            xml_bytes = resp.read()
    except (HTTPError, URLError, OSError) as e:
        print(f"    ✗ {pdf_path.name}: {e}")
        return None

    # Parse TEI XML
    try:
        import defusedxml.ElementTree as ET
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        print(f"    ✗ {pdf_path.name}: XML parse error: {e}")
        return None

    ns = {
        "tei": "http://www.tei-c.org/ns/1.0",
        "xml": "http://www.w3.org/XML/1998/namespace",
    }
    citations = []
    for bibl in root.findall(".//tei:biblStruct", ns):
        try:
            raw = ""
            for el in bibl.iter():
                if el.text and el.text.strip():
                    raw = (raw + " " + el.text.strip()).strip()
            raw = raw[:500]  # truncate very long raw text

            # Authors
            authors = []
            for author in bibl.findall(".//tei:author/tei:persName", ns):
                parts = []
                for tag in ["forename", "surname"]:
                    el = author.find(f"tei:{tag}", ns)
                    if el is not None and el.text:
                        parts.append(el.text)
                if parts:
                    authors.append(" ".join(parts))

            # Year
            date = bibl.find(".//tei:date", ns)
            year = date.get("when", "")[:4] if date is not None else None

            # Title
            title_el = bibl.find(".//tei:title[@level='a']", ns)
            title = title_el.text.strip() if title_el is not None and title_el.text else None

            # DOI
            idno = bibl.find('.//tei:idno[@type="DOI"]', ns)
            doi = idno.text if idno is not None and idno.text else None

            # URL
            ref = bibl.find('.//tei:ref[@type="URL"]', ns)
            url_val = ref.get("target") if ref is not None else None

            citations.append({
                "raw_text": raw,
                "citation_type": "reference_list",
                "style": "auto_detected",
                "authors": authors,
                "year": year,
                "title": title,
                "venue": None,
                "doi": doi,
                "url": url_val,
                "page_num": 0,
                "confidence": 0.5,
            })
        except Exception:
            continue

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

    # Load existing results
    if out_path.exists() and not args.overwrite:
        existing = json.loads(out_path.read_text())
    else:
        existing = {}

    results = []
    for i, pdf_path in enumerate(pdfs, 1):
        arxiv_id = pdf_path.stem
        print(f"[{i}/{len(pdfs)}] {arxiv_id}: ", end="", flush=True)
        if arxiv_id in existing and not args.overwrite:
            print(f"skipped (exists)")
            results.append(existing[arxiv_id])
            continue
        t0 = time.time()
        citations = extract_pdf(pdf_path, args.grobid)
        elapsed = time.time() - t0
        if citations is None:
            results.append({"arxiv_id": arxiv_id, "pdf": str(pdf_path), "citations": [], "error": "GROBID failed"})
        else:
            print(f"{len(citations)} citations ({elapsed:.1f}s)")
            results.append({"arxiv_id": arxiv_id, "pdf": str(pdf_path), "citations": citations})
            existing[arxiv_id] = results[-1]

    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    total_cits = sum(len(r["citations"]) for r in results)
    errors = sum(1 for r in results if "error" in r)
    print(f"\n✓ Processed {len(results)} PDFs, {total_cits} citations, {errors} errors")
    print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
