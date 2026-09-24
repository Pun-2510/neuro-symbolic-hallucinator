#!/usr/bin/env python3
"""Quick evaluation script - saves results to file."""
import asyncio
import json
import sys
import re
sys.path.insert(0, '.')

from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient
from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.models.citation import Citation
from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
from integrity_checker.models.validation import ValidationLabel

async def test():
    with open('evaluation/ground_truth.json') as f:
        data = json.load(f)

    orchestrator = RetrievalOrchestrator(
        crossref=CrossrefClient(),
        openalex=OpenAlexClient(),
        semantic_scholar=SemanticScholarClient(),
        arxiv=ArxivClient(),
        parallel=False,
    )
    checker = NeuroSymbolicChecker(enable_content_alignment=False)

    predictions = []

    for i, case in enumerate(data):
        raw = case['citation_raw']
        citation = Citation(raw_text=raw)

        year_match = re.search(r'\((\d{4})\)', raw)
        if year_match:
            citation.year = year_match.group(1)

        result = await orchestrator.retrieve(citation)
        verdict = checker.check(citation, result, api_exhausted=result.api_exhausted)

        predictions.append({
            'citation_id': case['citation_id'],
            'ground_truth': case['ground_truth'],
            'predicted': str(verdict.label),
            'raw': raw,
            'confidence': verdict.confidence,
            'rules': verdict.triggered_rules,
        })

        print(f'{i+1}/{len(data)}: {case["ground_truth"]} -> {str(verdict.label)[:30]}')
        await asyncio.sleep(0.3)

    # Save results
    with open('evaluation/quick_predictions.json', 'w') as f:
        json.dump(predictions, f, indent=2)

    # Compute confusion matrix
    confusion = {}
    for p in predictions:
        gt = p['ground_truth']
        pred = p['predicted']
        if gt not in confusion:
            confusion[gt] = {}
        confusion[gt][pred] = confusion[gt].get(pred, 0) + 1

    print('\n=== CONFUSION MATRIX ===')
    for gt in sorted(confusion.keys()):
        print(f'{gt}: {confusion[gt]}')

    # METADATA_ERROR accuracy
    meta_preds = [p for p in predictions if p['ground_truth'] == 'METADATA_ERROR']
    meta_correct = sum(1 for p in meta_preds if 'METADATA_ERROR' in p['predicted'])
    print(f'\nMETADATA_ERROR accuracy: {meta_correct}/{len(meta_preds)} ({100*meta_correct/len(meta_preds):.1f}%)')

asyncio.run(test())
