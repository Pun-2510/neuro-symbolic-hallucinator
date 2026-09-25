#!/usr/bin/env python3
"""Test REAL papers - should all be verified/real."""
import asyncio
import json
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


async def test_real_papers(max_samples=10):
    """Test REAL papers - expect mostly VERIFIED/REAL or UNRESOLVED (if APIs fail)"""
    print("=" * 60)
    print("TEST: REAL PAPERS")
    print("=" * 60)

    # Load ground truth
    with open(Path(__file__).parent.parent / "ground_truth.json") as f:
        gt = json.load(f)

    real_papers = [g for g in gt if g['ground_truth'] == 'REAL'][:max_samples]
    print(f"Testing {len(real_papers)} REAL papers\n")

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
    for paper in real_papers:
        citation = Citation(raw_text=paper['citation_raw'])

        # Extract year
        import re
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

        results.append({
            'id': paper['citation_id'],
            'raw': paper['citation_raw'],
            'predicted': str(verdict.label.name),
            'confidence': verdict.confidence,
            'sources_found': len(source_result.candidates),
            'sources_succeeded': source_result.sources_succeeded,
            'best_candidate': source_result.best_candidate().title[:50] if source_result.best_candidate() and source_result.best_candidate().title else None
        })

        # Print result
        status = "✓" if verdict.label.name in ['VERIFIED', 'UNRESOLVED'] else "✗"
        print(f"  {status} {paper['citation_id']}: {paper['citation_raw'][:40]}")
        print(f"      -> {verdict.label.name} (conf={verdict.confidence:.2f})")
        if source_result.sources_succeeded:
            print(f"      sources: {source_result.sources_succeeded}")
        else:
            print(f"      sources: NONE (all failed)")
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

    # Check accuracy
    correct = sum(1 for r in results if r['predicted'] in ['VERIFIED', 'UNRESOLVED'])
    print(f"\nAccuracy (VERIFIED + UNRESOLVED = OK): {correct}/{len(results)} ({correct/len(results)*100:.1f}%)")

    return results


if __name__ == "__main__":
    results = asyncio.run(test_real_papers(max_samples=10))
