"""Source data model — output của retrieval module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SourceCandidate:
    """Một ứng viên được một nguồn trả về.

    Attributes:
        source_name: tên nguồn (Crossref / OpenAlex / Semantic Scholar / arXiv).
        found: True nếu source trả về bản ghi, False nếu lookup thất bại.
        doi, title, authors, year, venue, url: metadata từ source.
        external_ids: dict các định danh ngoài (DOI, arXiv ID, MAG ID, ...).
        score: score do source trả về (relevance), không dùng làm ground truth.
        confidence: 0.0–1.0, do source tự gán (thường heuristic của source).
        error: thông báo lỗi nếu API call thất bại.
        cached: True nếu lấy từ disk cache.
    """

    source_name: str
    found: bool = False

    doi: Optional[str] = None
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    year: Optional[str] = None
    venue: Optional[str] = None
    url: Optional[str] = None
    external_ids: dict[str, str] = field(default_factory=dict)

    score: float = 0.0
    confidence: float = 0.0

    error: Optional[str] = None
    cached: bool = False

    def fingerprint(self) -> str:
        """Hash key để dedupe giữa các nguồn.

        Ưu tiên DOI; fallback normalized title.
        """
        if self.doi:
            return f"doi:{self.doi.lower()}"
        if self.title:
            # lowercase, bỏ punctuation + spaces
            norm = "".join(c for c in self.title.lower() if c.isalnum())
            return f"title:{norm[:120]}"
        return f"raw:{self.source_name}:{id(self)}"


@dataclass
class SourceResult:
    """Kết quả gộp cho 1 citation sau khi truy hồi đa nguồn."""

    citation_raw: str
    candidates: list[SourceCandidate] = field(default_factory=list)
    sources_queried: list[str] = field(default_factory=list)
    sources_succeeded: list[str] = field(default_factory=list)
    sources_failed: dict[str, str] = field(default_factory=dict)  # source → error

    def best_candidate(self) -> Optional[SourceCandidate]:
        """Trả về candidate tốt nhất (highest confidence) trong số found=True."""
        found = [c for c in self.candidates if c.found]
        if not found:
            return None
        return max(found, key=lambda c: c.confidence)

    def consensus_count(self) -> int:
        """Số nguồn đã tìm ra candidate trùng DOI/title (≥1)."""
        seen: set[str] = set()
        for c in self.candidates:
            if c.found and (c.doi or c.title):
                seen.add(c.fingerprint())
        return len(seen)