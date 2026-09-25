#!/usr/bin/env python3
"""Test METADATA_ERROR papers - should be detected as METADATA_ERROR."""
import asyncio
import json
import re
from pathlib import Path
from collections import Counter

# Add parent to path
import sys
basedir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(basedir / "src"))
sys.path.insert(0, str(basedir))

from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient
from integrity_checker.models.citation import Citation
from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker


async def test_metadata_error(max_samples=10):
    """Test METADATA_ERROR papers - expect METADATA_ERROR"""
    print("=" * 60)
    print("TEST: METADATA_ERROR PAPERS")
    print("=" * 60)

    # Load ground truth
    with open(Path(__file__).parent.parent / "ground_truth.json") as f:
        gt = json.load(f)

    metaerr_papers = [g for g in gt if g['ground_truth'] == 'METADATA_ERROR'][:max_samples]
    print(f"Testing {len(metaerr_papers)} METADATA_ERROR papers\n")

    # Initialize system
    crossref = CrossrefClient()
    openalex = OpenAlexClient()
    semantic_scholar = SemanticScholarClient()
    orchestrator = RetrievalOrchestrator(
        crossref=crossref, openalex=openalex,
        semantic_scholar=semantic_scholar, parallel=True
    )
    checker = NeuroSymbolicChecker(enable_content_alignment=False)

    results = []
    for paper in metaerr_papers:
        citation = Citation(raw_text=paper['citation_raw'])

        # Extract year
        year_match = re.search(r'\((\d{4})\)', paper['citation_raw'])
        if year_match:
            citation.year = year_match.group(1)

        # Run retrieval
        source_result = await orchestrator.retrieve(citation)

        # Run checker
        verdict = checker.check(
            citation=citation,
            source=source_result,
            api_exhausted=source_result.api_exhausted
        )

        # Check for future year (should NOT be future year for METADATA_ERROR)
        has_future_year = False
        if year_match:
            year = int(year_match.group(1))
            if year > 2026:
                has_future_year = True

        results.append({
            'id': paper['citation_id'],
            'raw': paper['citation_raw'],
            'predicted': str(verdict.label.name),
            'confidence': verdict.confidence,
            'sources_found': len(source_result.candidates),
            'sources_succeeded': source_result.sources_succeeded,
            'source_type': paper['source'],
            'error_type': paper.get('original_paper', {}).get('title', 'unknown')[:50] if paper.get('original_paper') else 'N/A',
            'has_future_year': has_future_year,
            'reasoning': verdict.reasoning[:100] if verdict.reasoning else None
        })

        # Print result
        is_detected = verdict.label.name == 'METADATA_ERROR'
        status = "✓" if is_detected else "✗"
        print(f"  {status} {paper['citation_id']}: {paper['citation_raw'][:40]}")
        print(f"      source: {paper['source']}, future_year: {has_future_year}")
        if paper.get('original_paper'):
            print(f"      original: {paper['original_paper'].get('authors', '')} ({paper['original_paper'].get('year', '')}) - {paper['original_paper'].get('title', '')[:40]}")
        print(f"      -> {verdict.label.name} (conf={verdict.confidence:.2f})")
        if verdict.reasoning:
            print(f"      reason: {verdict.reasoning[:80]}...")
        print()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    predictions = [r['predicted'] for r in results]
    counts = Counter(predictions)
    print(f"Total: {len(results)}")
    for label, count in counts.items():
        pct = count / len(results) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")

    # Check detection rate
    detected = sum(1 for r in results if r['predicted'] == 'METADATA_ERROR')
    print(f"\nDetection Rate (METADATA_ERROR): {detected}/{len(results)} ({detected/len(results)*100:.1f}%)")

    # By error type
    print("\n--- By Error Type ---")
    by_type = {}
    for r in results:
        src = r['source_type']
        if src not in by_type:
            by_type[src] = {'total': 0, 'detected': 0}
        by_type[src]['total'] += 1
        if r['predicted'] == 'METADATA_ERROR':
            by_type[src]['detected'] += 1

    for src, stats in by_type.items():
        pct = stats['detected'] / stats['total'] * 100
        print(f"  {src}: {stats['detected']}/{stats['total']} ({pct:.1f}%)")

    return results


if __name__ == "__main__":
    results = asyncio.run(test_metadata_error(max_samples=10))
