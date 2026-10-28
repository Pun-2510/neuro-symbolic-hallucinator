"""Retrieval module — multi-source scholarly data.

Bao gồm:
- BaseScholarClient (abstract)
- CrossrefClient, OpenAlexClient, SemanticScholarClient, CoreAPIClient
- RetrievalOrchestrator (gộp kết quả)
- RateLimiter (async-safe token bucket)
- LocalDatabase (SQLite với FTS5)
"""

from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.retrieval.base import BaseScholarClient
from integrity_checker.retrieval.coreapi_client import CoreAPIClient
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.datacite_client import DataCiteClient
from integrity_checker.retrieval.dblp_client import DBLPClient
from integrity_checker.retrieval.doaj_client import DOAJClient
from integrity_checker.retrieval.doi_ra_client import DoiRaClient
from integrity_checker.retrieval.europepmc_client import EuropePMCClient
from integrity_checker.retrieval.huggingface_client import HuggingFaceClient
from integrity_checker.retrieval.ncbi_biorxiv_client import NcbiBiorxivClient
from integrity_checker.retrieval.openaire_hal_client import OpenAIREHalClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.openlibrary_client import OpenLibraryClient
from integrity_checker.retrieval.rate_limiter import RateLimiter
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient
from integrity_checker.retrieval.tech_standard_client import TechStandardClient

__all__ = [
    "ArxivClient",
    "BaseScholarClient",
    "CoreAPIClient",
    "CrossrefClient",
    "DataCiteClient",
    "DBLPClient",
    "DOAJClient",
    "DoiRaClient",
    "EuropePMCClient",
    "HuggingFaceClient",
    "NcbiBiorxivClient",
    "OpenAIREHalClient",
    "OpenAlexClient",
    "OpenLibraryClient",
    "SemanticScholarClient",
    "TechStandardClient",
    "RetrievalOrchestrator",
    "RateLimiter",
]
