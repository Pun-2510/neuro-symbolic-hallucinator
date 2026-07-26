"""RetrievalOrchestrator — gộp kết quả từ 4 nguồn theo strategy đa nguồn.

Đề cương §5.4 — thứ tự ưu tiên:
    1. DOI exact match (Crossref)
    2. Crossref bibliographic query
    3. OpenAlex title/author/year
    4. Semantic Scholar supplement
    5. arXiv preprint fallback

Sau khi có candidate từ các nguồn, dedupe theo DOI/normalized title.
"""

from __future__ import annotations

import asyncio

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.retrieval.base import BaseScholarClient
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.rate_limiter import RateLimiter
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient

logger = get_logger(__name__)


class RetrievalOrchestrator:
    """Orchestrator cho multi-source retrieval.

    # TODO(user): tuần 9–10 — implement:
        - Pre-filter: nếu citation có DOI → ưu tiên Crossref DOI exact lookup
        - Song song hóa các nguồn không có DOI (asyncio.gather)
        - Cache results trước khi gộp
    """

    def __init__(
        self,
        crossref: CrossrefClient | None = None,
        openalex: OpenAlexClient | None = None,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
        parallel: bool = True,
    ) -> None:
        settings = get_settings().retrieval
        self.crossref = crossref or CrossrefClient(contact_email=settings.contact_email)
        self.openalex = openalex or OpenAlexClient(contact_email=settings.contact_email)
        self.semantic_scholar = semantic_scholar or SemanticScholarClient()
        self.arxiv = arxiv or ArxivClient()
        self.parallel = parallel
        self._rate_limiters: dict[str, RateLimiter] = {
            self.crossref.name: RateLimiter(settings.rate_limits.crossref_per_sec),
            self.openalex.name: RateLimiter(settings.rate_limits.openalex_per_sec),
            self.semantic_scholar.name: RateLimiter(settings.rate_limits.semantic_scholar_per_sec),
            self.arxiv.name: RateLimiter(settings.rate_limits.arxiv_per_sec),
        }

    def clients(self) -> list[BaseScholarClient]:
        return [self.crossref, self.openalex, self.semantic_scholar, self.arxiv]

    async def retrieve(self, citation: Citation) -> SourceResult:
        """Truy hồi tất cả nguồn cho 1 citation."""
        clients = self.clients()
        if self.parallel:
            candidates = await asyncio.gather(
                *[self._lookup_with_ratelimit(c, citation) for c in clients],
                return_exceptions=True,
            )
        else:
            candidates = []
            for c in clients:
                candidates.append(await self._lookup_with_ratelimit(c, citation))

        # Filter exceptions
        valid: list[SourceCandidate] = []
        succeeded: list[str] = []
        failed: dict[str, str] = {}
        for client, cand in zip(clients, candidates):
            if isinstance(cand, Exception):
                failed[client.name] = str(cand)
                continue
            valid.append(cand)  # type: ignore[arg-type]
            if cand.found:
                succeeded.append(client.name)
            elif cand.error:
                failed[client.name] = cand.error

        deduped = self._dedupe_candidates(valid)

        return SourceResult(
            citation_raw=citation.raw_text,
            candidates=deduped,
            sources_queried=[c.name for c in clients],
            sources_succeeded=succeeded,
            sources_failed=failed,
        )

    async def _lookup_with_ratelimit(
        self,
        client: BaseScholarClient,
        citation: Citation,
    ) -> SourceCandidate:
        limiter = self._rate_limiters.get(client.name)
        if limiter:
            await limiter.wait()
        return await client.lookup(citation)

    @staticmethod
    def _dedupe_candidates(candidates: list[SourceCandidate]) -> list[SourceCandidate]:
        """Dedupe theo fingerprint (DOI > normalized title). Giữ candidate confidence cao nhất."""
        bucket: dict[str, SourceCandidate] = {}
        for c in candidates:
            fp = c.fingerprint()
            if not c.found:
                # vẫn lưu failed candidate để debug
                bucket.setdefault(f"raw:{id(c)}", c)
                continue
            existing = bucket.get(fp)
            if existing is None or c.confidence > existing.confidence:
                bucket[fp] = c
        return list(bucket.values())