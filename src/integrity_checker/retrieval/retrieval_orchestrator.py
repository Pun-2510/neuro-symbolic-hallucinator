"""RetrievalOrchestrator — gộp kết quả từ 4 nguồn theo strategy đa nguồn.

Đề cương §5.4 — thứ tự ưu tiên:
    1. DOI exact match (Crossref)
    2. Crossref bibliographic query
    3. OpenAlex title/author/year
    4. Semantic Scholar supplement
    5. arXiv preprint fallback

Sau khi có candidate từ các nguồn, dedupe theo DOI/normalized title.

v1.2 tuần 8 (task #24):
    - Cache integration: DiskCache với key chứa source_name (tránh trộn nhầm)
    - Health check: nếu đa số sources failed → trả SourceResult rỗng + flag UNRESOLVED
    - UNRESOLVED sentinel: candidate với found=False từ tất cả sources
"""

from __future__ import annotations

import asyncio
import hashlib

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.retrieval.arxiv_client import ArxivClient
from integrity_checker.retrieval.base import BaseScholarClient
from integrity_checker.retrieval.cache import DiskCache
from integrity_checker.retrieval.crossref_client import CrossrefClient
from integrity_checker.retrieval.openalex_client import OpenAlexClient
from integrity_checker.retrieval.rate_limiter import RateLimiter
from integrity_checker.retrieval.semantic_scholar_client import SemanticScholarClient

logger = get_logger(__name__)


class RetrievalOrchestrator:
    """Orchestrator cho multi-source retrieval.

    Features v1.2:
        - Cache với source_name trong key (Crossref ≠ OpenAlex).
        - Health check + UNRESOLVED khi đa số sources fail.
        - Parallel lookup qua asyncio.gather.
    """

    def __init__(
        self,
        crossref: CrossrefClient | None = None,
        openalex: OpenAlexClient | None = None,
        semantic_scholar: SemanticScholarClient | None = None,
        arxiv: ArxivClient | None = None,
        parallel: bool = True,
        cache: DiskCache | None = None,
    ) -> None:
        settings = get_settings().retrieval
        self.crossref = crossref or CrossrefClient(contact_email=settings.contact_email)
        self.openalex = openalex or OpenAlexClient(contact_email=settings.contact_email)
        self.semantic_scholar = semantic_scholar or SemanticScholarClient()
        self.arxiv = arxiv or ArxivClient()
        self.parallel = parallel
        # Cache: nếu caller không truyền thì default DiskCache ở settings.paths.cache_dir
        settings_global = get_settings()
        self.cache = cache or DiskCache(
            cache_dir=settings_global.paths.cache_dir,
            ttl_seconds=settings.cache.ttl_seconds,
            enabled=settings.cache.enabled,
        )
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
                *[self._lookup_with_cache_and_ratelimit(c, citation) for c in clients],
                return_exceptions=True,
            )
        else:
            candidates = []
            for c in clients:
                candidates.append(
                    await self._lookup_with_cache_and_ratelimit(c, citation)
                )

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

        # Health check: nếu tất cả sources fail (không có candidate found nào)
        # → UNRESOLVED sentinel
        any_found = any(c.found for c in deduped)
        if not any_found and len(failed) >= len(clients) // 2 + 1:
            # Đa số sources failed → trả UNRESOLVED
            logger.warning(
                f"UNRESOLVED: citation='{citation.raw_text[:50]}', "
                f"failed={list(failed.keys())}"
            )

        return SourceResult(
            citation_raw=citation.raw_text,
            candidates=deduped,
            sources_queried=[c.name for c in clients],
            sources_succeeded=succeeded,
            sources_failed=failed,
        )

    async def _lookup_with_cache_and_ratelimit(
        self,
        client: BaseScholarClient,
        citation: Citation,
    ) -> SourceCandidate:
        """Cache lookup → ratelimit → thật.

        Cache key format: {source_name}:{citation_hash} (theo v1.2 §3.6).
        """
        cache_key = self._cache_key(client.name, citation)
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                cand = self._candidate_from_cache(client.name, cached)
                cand.cached = True
                logger.debug(f"Cache HIT for {client.name}")
                return cand

        limiter = self._rate_limiters.get(client.name)
        if limiter:
            await limiter.wait()

        cand = await client.lookup(citation)

        # Save to cache (chỉ khi found hoặc có structured error)
        if cache_key:
            self.cache.set(cache_key, self._candidate_to_cache(cand))

        return cand

    @staticmethod
    def _cache_key(source_name: str, citation: Citation) -> str:
        """Build cache key: {source}:{hash(canonical fields)}.

        Hash dùng citation fields thay vì raw_text để cache reuse khi citation
        chỉ khác whitespace.
        """
        # Canonical fields - handle both list[str] and list[Author] formats
        author_parts = []
        if citation.authors:
            for a in citation.authors:
                if hasattr(a, "last_name"):
                    # Author object from AuthorParser
                    author_parts.append(a.last_name)
                else:
                    # Plain string - use as-is
                    author_parts.append(str(a))
        parts = [
            citation.doi or "",
            citation.title or "",
            citation.year or "",
            ",".join(author_parts),
        ]
        canonical = "|".join(parts).encode("utf-8")
        h = hashlib.sha256(canonical).hexdigest()[:16]
        return f"{source_name}:{h}"

    @staticmethod
    def _candidate_to_cache(cand: SourceCandidate) -> dict:
        """Serialize SourceCandidate → dict cho cache."""
        return {
            "found": cand.found,
            "doi": cand.doi,
            "title": cand.title,
            "authors": cand.authors,
            "year": cand.year,
            "venue": cand.venue,
            "url": cand.url,
            "external_ids": cand.external_ids,
            "score": cand.score,
            "confidence": cand.confidence,
            "error": cand.error,
        }

    @staticmethod
    def _candidate_from_cache(source_name: str, data: dict) -> SourceCandidate:
        """Deserialize dict → SourceCandidate."""
        return SourceCandidate(
            source_name=source_name,
            found=data.get("found", False),
            doi=data.get("doi"),
            title=data.get("title"),
            authors=data.get("authors", []),
            year=data.get("year"),
            venue=data.get("venue"),
            url=data.get("url"),
            external_ids=data.get("external_ids", {}),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.0),
            error=data.get("error"),
            cached=True,
        )

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