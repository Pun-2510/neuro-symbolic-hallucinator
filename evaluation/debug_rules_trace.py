#!/usr/bin/env python3
"""Trace which rules are triggered for METADATA_ERROR cases."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def debug_rules():
    """Debug which rules are triggered."""
    from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
    from integrity_checker.retrieval.crossref_client import CrossrefClient
    from integrity_checker.retrieval.openalex_client import OpenAlexClient
    from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient
    from integrity_checker.retrieval.arxiv_client import ArxivClient
    from integrity_checker.models.citation import Citation
    from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
    from integrity_checker.models.validation import ValidationLabel

    # Load METADATA_ERROR cases
    with open("evaluation/ground_truth.json", encoding="utf-8") as f:
        dataset = json.load(f)

    meta_cases = [d for d in dataset if d["ground_truth"] == "METADATA_ERROR"][:5]

    # Initialize
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

    for case in meta_cases:
        cid = case["citation_id"]
        raw = case["citation_raw"]

        print(f"\n{'='*70}")
        print(f"CASE: {cid}")
        print(f"RAW: {raw}")
        print(f"ORIGINAL PAPER: {case.get('original_paper', {}).get('title', 'N/A')}")

        # Parse
        year_match = re.search(r'\((\d{4})\)', raw)
        year = year_match.group(1) if year_match else None
        author_match = re.match(r'^([A-Z][a-z]+)', raw)
        author = author_match.group(1) if author_match else None

        citation = Citation(raw_text=raw)
        citation.year = year
        citation.authors = [author] if author else []

        # Run retrieval
        source_result = await orchestrator.retrieve(citation)
        sources = [c for c in source_result.candidates if c.found]

        print(f"\n📊 Sources found: {len(sources)}")

        for i, c in enumerate(sources[:3], 1):
            print(f"\n   Candidate {i}:")
            print(f"      Title: {c.title[:80] if c.title else 'N/A'}...")
            print(f"      Year: {c.year}")
            print(f"      Authors: {c.authors[:2] if c.authors else 'N/A'}")

        if sources:
            verdict = checker.check(
                citation=citation,
                source=source_result,
                api_exhausted=source_result.api_exhausted,
            )

            print(f"\n🎯 VERDICT: {verdict.label}")
            print(f"   Confidence: {verdict.confidence:.4f}")
            print(f"   Reasoning: {verdict.reasoning[:200]}...")
            print(f"   Triggered Rules: {verdict.triggered_rules}")

        await asyncio.sleep(0.3)


if __name__ == "__main__":
    asyncio.run(debug_rules())
