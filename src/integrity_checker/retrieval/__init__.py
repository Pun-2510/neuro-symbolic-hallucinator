"""Retrieval module — multi-source scholarly data.

Bao gồm:
- BaseScholarClient (abstract)
- CrossrefClient, OpenAlexClient, SemanticScholarClient, ArxivClient
- RetrievalOrchestrator (gộp kết quả)
- RateLimiter (async-safe token bucket)
- DiskCache (JSON file cache)
"""

from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.retrieval.base import BaseScholarClient
from integrity_checker.retrieval.cache import DiskCache
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.rate_limiter import RateLimiter
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient

__all__ = [
    "BaseScholarClient",
    "CrossrefClient",
    "OpenAlexClient",
    "SemanticScholarClient",
    "ArxivClient",
    "RetrievalOrchestrator",
    "RateLimiter",
    "DiskCache",
]