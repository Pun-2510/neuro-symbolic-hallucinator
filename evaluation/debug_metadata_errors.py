#!/usr/bin/env python3
"""Debug METADATA_ERROR cases - trace root causes.

Run this to understand why METADATA_ERROR cases are being misclassified.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from integrity_checker.models.citation import Citation
from integrity_checker.models.validation import ValidationLabel


def load_metadata_error_cases():
    """Load METADATA_ERROR cases from dataset."""
    with open("evaluation/ground_truth.json", encoding="utf-8") as f:
        data = json.load(f)

    return [item for item in data if item["ground_truth"] == "METADATA_ERROR"]


async def debug_single_case(raw_text: str, citation_id: str, original_paper: dict):
    """Debug a single METADATA_ERROR case."""
    from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
    from integrity_checker.retrieval.crossref_client import CrossrefClient
    from integrity_checker.retrieval.openalex_client import OpenAlexClient
    from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient
    from integrity_checker.retrieval.arxiv_client import ArxivClient
    from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker

    print(f"\n{'='*70}")
    print(f"CASE: {citation_id}")
    print(f"{'='*70}")

    # Parse citation
    year_match = re.search(r'\((\d{4})\)', raw_text)
    year = year_match.group(1) if year_match else None

    author_match = re.match(r'^([A-Z][a-z]+)', raw_text)
    author = author_match.group(1) if author_match else None

    print(f"\n📝 Input Citation: {raw_text}")
    print(f"   Parsed author: {author}")
    print(f"   Parsed year: {year}")

    print(f"\n📋 Original Paper (what it SHOULD match):")
    print(f"   Author: {original_paper.get('authors', 'N/A')}")
    print(f"   Year: {original_paper.get('year', 'N/A')}")
    print(f"   Title: {original_paper.get('title', 'N/A')}")

    # Determine error type
    if original_paper:
        orig_year = str(original_paper.get('year', ''))
        orig_author = original_paper.get('authors', '')

        if year and orig_year and year != orig_year:
            error_type = f"WRONG_YEAR (cited: {year}, correct: {orig_year})"
        elif author and orig_author and author not in orig_author:
            error_type = f"WRONG_AUTHOR (cited: {author}, correct: {orig_author})"
        else:
            error_type = "WRONG_TITLE or other"
    else:
        error_type = "UNKNOWN"

    print(f"\n⚠️ Error Type: {error_type}")

    # Create citation object
    citation = Citation(raw_text=raw_text)
    citation.year = year
    citation.authors = [author] if author else []

    # Initialize clients
    crossref = CrossrefClient()
    openalex = OpenAlexClient()
    semantic_scholar = SemanticScholarClient()
    arxiv = ArxivClient()

    orchestrator = RetrievalOrchestrator(
        crossref=crossref,
        openalex=openalex,
        semantic_scholar=semantic_scholar,
        arxiv=arxiv,
        parallel=False,
    )

    checker = NeuroSymbolicChecker(enable_content_alignment=False)

    # Run retrieval
    print(f"\n🔍 Running Retrieval...")
    try:
        source_result = await orchestrator.retrieve(citation)
        sources_found = [c for c in source_result.candidates if c.found]

        print(f"   Sources queried: {source_result.sources_queried}")
        print(f"   Sources succeeded: {source_result.sources_succeeded}")
        print(f"   Candidates found: {len(sources_found)}")

        if sources_found:
            for i, c in enumerate(sources_found[:3], 1):
                print(f"\n   Candidate {i}:")
                print(f"      Title: {c.title[:60] if c.title else 'N/A'}...")
                print(f"      Authors: {c.authors[:2] if c.authors else 'N/A'}")
                print(f"      Year: {c.year}")
                print(f"      Confidence: {c.confidence:.2f}")

            # Run checker
            best_source = source_result.best_candidate()
            verdict = checker.check(
                citation=citation,
                source=best_source,
                api_exhausted=source_result.api_exhausted,
            )

            print(f"\n🎯 Verdict: {verdict.label}")
            print(f"   Confidence: {verdict.confidence:.2f}")

        else:
            print(f"\n⚠️ No sources found!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main debug function."""
    print("="*70)
    print("DEBUGGING METADATA_ERROR CASES")
    print("="*70)

    # Load cases
    cases = load_metadata_error_cases()
    print(f"\nFound {len(cases)} METADATA_ERROR cases")

    # Group by error type
    wrong_year_cases = []
    wrong_author_cases = []
    wrong_title_cases = []

    for case in cases:
        raw = case["citation_raw"]
        original = case.get("original_paper")

        if original:
            year_match = re.search(r'\((\d{4})\)', raw)
            cited_year = year_match.group(1) if year_match else None
            orig_year = str(original.get("year", ""))

            if cited_year and orig_year and cited_year != orig_year:
                wrong_year_cases.append(case)
            else:
                wrong_title_cases.append(case)
        else:
            wrong_author_cases.append(case)

    print(f"\n📊 Error Type Breakdown:")
    print(f"   Wrong Year:    {len(wrong_year_cases)} cases")
    print(f"   Wrong Author:   {len(wrong_author_cases)} cases")
    print(f"   Wrong Title:   {len(wrong_title_cases)} cases")

    # Debug first 5 cases of each type
    print(f"\n{'='*70}")
    print("DEBUGGING WRONG YEAR CASES (sample)")
    print("="*70)

    for case in wrong_year_cases[:3]:
        await debug_single_case(
            case["citation_raw"],
            case["citation_id"],
            case.get("original_paper"),
        )

    print(f"\n{'='*70}")
    print("DEBUGGING WRONG AUTHOR CASES (sample)")
    print("="*70)

    for case in wrong_author_cases[:3]:
        await debug_single_case(
            case["citation_raw"],
            case["citation_id"],
            case.get("original_paper"),
        )

    print(f"\n{'='*70}")
    print("DEBUGGING WRONG TITLE CASES (sample)")
    print("="*70)

    for case in wrong_title_cases[:3]:
        await debug_single_case(
            case["citation_raw"],
            case["citation_id"],
            case.get("original_paper"),
        )


if __name__ == "__main__":
    asyncio.run(main())
