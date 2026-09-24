#!/usr/bin/env python3
"""Fix METADATA_ERROR detection - identify and fix the root causes.

This script:
1. Runs real system WITHOUT heuristic override
2. Identifies why METADATA_ERROR cases fail
3. Proposes fixes
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.synthetic_dataset import SyntheticDatasetGenerator


async def run_real_system_evaluation(dataset: list[dict], max_samples: int = None):
    """Run evaluation using ONLY the real system - no heuristic override."""
    from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
    from integrity_checker.retrieval.crossref_client import CrossrefClient
    from integrity_checker.retrieval.openalex_client import OpenAlexClient
    from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient
    from integrity_checker.retrieval.arxiv_client import ArxivClient
    from integrity_checker.models.citation import Citation
    from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
    from integrity_checker.models.validation import ValidationLabel

    print("="*70)
    print("RUNNING PURE REAL SYSTEM EVALUATION (NO HEURISTIC OVERRIDE)")
    print("="*70)

    # Initialize
    print("\nInitializing system...")
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

    if max_samples:
        dataset = dataset[:max_samples]

    results = []

    for i, item in enumerate(dataset):
        cid = item["citation_id"]
        raw = item["citation_raw"]
        ground_truth = item["ground_truth"]

        if (i + 1) % 20 == 0 or i == 0:
            print(f"Progress: {i+1}/{len(dataset)}")

        # Parse citation
        year_match = re.search(r'\((\d{4})\)', raw)
        year = year_match.group(1) if year_match else None
        author_match = re.match(r'^([A-Z][a-z]+)', raw)
        author = author_match.group(1) if author_match else None

        citation = Citation(raw_text=raw)
        citation.year = year
        citation.authors = [author] if author else []

        try:
            # Run retrieval
            source_result = await orchestrator.retrieve(citation)
            sources_found = [c for c in source_result.candidates if c.found]

            # Run checker
            verdict = None
            if sources_found:
                # Pass the ENTIRE SourceResult, not just the candidate
                verdict = checker.check(
                    citation=citation,
                    source=source_result,  # Pass SourceResult, not SourceCandidate
                    api_exhausted=source_result.api_exhausted,
                )

            # Map to evaluation label
            label_map = {
                ValidationLabel.VERIFIED: "REAL",
                ValidationLabel.METADATA_ERROR: "METADATA_ERROR",
                ValidationLabel.SUSPECTED_HALLUCINATION: "HALLUCINATED",
                ValidationLabel.UNRESOLVED: "UNRESOLVED",
            }

            predicted = label_map.get(verdict.label, str(verdict.label)) if verdict else "UNRESOLVED"
            confidence = verdict.confidence if verdict else 0.5

            results.append({
                "citation_id": cid,
                "ground_truth": ground_truth,
                "predicted": predicted,
                "confidence": confidence,
                "raw": raw,
                "sources_found": len(sources_found),
                "api_exhausted": source_result.api_exhausted,
                "best_title": sources_found[0].title[:50] if sources_found and sources_found[0].title else None,
            })

        except Exception as e:
            print(f"\nError on {cid}: {e}")
            results.append({
                "citation_id": cid,
                "ground_truth": ground_truth,
                "predicted": "ERROR",
                "confidence": 0,
                "raw": raw,
                "error": str(e),
            })

        await asyncio.sleep(0.3)  # Rate limit

    return results


def analyze_results(results: list[dict]):
    """Analyze results and identify root causes of METADATA_ERROR failures."""
    print("\n" + "="*70)
    print("ANALYSIS OF METADATA_ERROR CASES")
    print("="*70)

    meta_errors = [r for r in results if r["ground_truth"] == "METADATA_ERROR"]
    hallucinations = [r for r in results if r["ground_truth"] == "HALLUCINATED"]
    reals = [r for r in results if r["ground_truth"] == "REAL"]

    print(f"\n📊 Dataset Breakdown:")
    print(f"   METADATA_ERROR: {len(meta_errors)}")
    print(f"   HALLUCINATED: {len(hallucinations)}")
    print(f"   REAL: {len(reals)}")

    # METADATA_ERROR analysis
    print(f"\n📋 METADATA_ERROR Cases:")
    correct = sum(1 for r in meta_errors if r["predicted"] == "METADATA_ERROR")
    to_hallu = sum(1 for r in meta_errors if r["predicted"] == "HALLUCINATED")
    to_unresolved = sum(1 for r in meta_errors if r["predicted"] == "UNRESOLVED")
    to_real = sum(1 for r in meta_errors if r["predicted"] == "REAL")

    print(f"   ✓ Correct (METADATA_ERROR): {correct}")
    print(f"   ✗ → HALLUCINATED: {to_hallu}")
    print(f"   ✗ → UNRESOLVED: {to_unresolved}")
    print(f"   ✗ → REAL: {to_real}")

    # Show some examples of wrong predictions
    print(f"\n📝 Sample WRONG METADATA_ERROR predictions:")

    wrong_cases = [r for r in meta_errors if r["predicted"] != "METADATA_ERROR"]
    for r in wrong_cases[:5]:
        print(f"\n   [{r['citation_id']}]")
        print(f"   Raw: {r['raw']}")
        print(f"   Predicted: {r['predicted']} (confidence: {r.get('confidence', 'N/A')})")
        print(f"   Sources found: {r.get('sources_found', 'N/A')}")
        if r.get('best_title'):
            print(f"   Best match: {r['best_title']}...")

    # Check for future year issue
    print(f"\n🔍 Future Year Check:")
    future_year_cases = [r for r in wrong_cases if any(c.isdigit() and int(c) > 2026 for c in re.findall(r'\d{4}', r['raw']))]
    print(f"   Cases with future years: {len(future_year_cases)}")

    for r in future_year_cases[:3]:
        years = re.findall(r'\d{4}', r['raw'])
        future_years = [y for y in years if int(y) > 2026]
        print(f"\n   [{r['citation_id']}]")
        print(f"   Raw: {r['raw']}")
        print(f"   Future years found: {future_years}")
        print(f"   Predicted: {r['predicted']}")

    # HALLUCINATION analysis
    print(f"\n📋 HALLUCINATION Cases:")
    hallu_correct = sum(1 for r in hallucinations if r["predicted"] == "HALLUCINATED")
    hallu_to_real = sum(1 for r in hallucinations if r["predicted"] == "REAL")
    hallu_to_unresolved = sum(1 for r in hallucinations if r["predicted"] == "UNRESOLVED")
    hallu_to_meta = sum(1 for r in hallucinations if r["predicted"] == "METADATA_ERROR")

    print(f"   ✓ Correct (HALLUCINATED): {hallu_correct}")
    print(f"   ✗ → REAL: {hallu_to_real}")
    print(f"   ✗ → UNRESOLVED: {hallu_to_unresolved}")
    print(f"   ✗ → METADATA_ERROR: {hallu_to_meta}")

    # REAL analysis
    print(f"\n📋 REAL Cases:")
    real_correct = sum(1 for r in reals if r["predicted"] == "REAL")
    real_to_hallu = sum(1 for r in reals if r["predicted"] == "HALLUCINATED")
    real_to_unresolved = sum(1 for r in reals if r["predicted"] == "UNRESOLVED")

    print(f"   ✓ Correct (REAL): {real_correct}")
    print(f"   ✗ → HALLUCINATED: {real_to_hallu}")
    print(f"   ✗ → UNRESOLVED: {real_to_unresolved}")

    # Calculate metrics
    print(f"\n📈 METRICS (Real System Only):")

    tp = hallu_correct
    fp = real_to_hallu
    fn = hallu_to_real + hallu_to_unresolved + hallu_to_meta
    tn = real_correct

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0

    print(f"   Precision: {precision:.4f}")
    print(f"   Recall: {recall:.4f}")
    print(f"   F1: {f1:.4f}")
    print(f"   Accuracy: {accuracy:.4f}")

    return results


async def main():
    print("="*70)
    print("METADATA_ERROR ROOT CAUSE ANALYSIS")
    print("="*70)

    # Load dataset
    dataset_path = Path(__file__).parent / "ground_truth.json"
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"\nLoaded {len(dataset)} citations")

    # Run real system on METADATA_ERROR cases only
    meta_cases = [d for d in dataset if d["ground_truth"] == "METADATA_ERROR"]
    print(f"METADATA_ERROR cases: {len(meta_cases)}")

    print("\nRunning real system on METADATA_ERROR cases...")
    results = await run_real_system_evaluation(meta_cases)

    # Analyze
    analyze_results(results)

    # Save results
    output_path = Path(__file__).parent / "metadata_error_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
