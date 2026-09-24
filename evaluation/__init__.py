"""Evaluation Module — Synthetic Dataset + Metrics for Fake Source Detection.

This module provides:
- synthetic_dataset.py: Generate 200 labeled citations (REAL/HALLUCINATED/METADATA_ERROR)
- evaluator.py: Full metrics calculation (Precision, Recall, F1, ROC-AUC, etc.)
- run_evaluation.py: Main script to run evaluation
- real_evaluation.py: Integration with real system (API calls)
- integration.py: Hybrid evaluation approach

Usage:
    # Generate dataset
    python -m evaluation.synthetic_dataset

    # Run heuristic evaluation
    python -m evaluation.run_evaluation --no-api

    # Run real system evaluation
    python -m evaluation.real_evaluation --max 50

    # Run with API integration
    python -m evaluation.real_evaluation
"""

from evaluation.evaluator import FakeDetectionEvaluator, EvaluationResult
from evaluation.synthetic_dataset import SyntheticDatasetGenerator

__all__ = [
    "FakeDetectionEvaluator",
    "EvaluationResult",
    "SyntheticDatasetGenerator",
]
