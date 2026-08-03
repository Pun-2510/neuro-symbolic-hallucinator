"""DuplicateDetector — phát hiện reference entries trùng nhau (v1.2 §3.5).

Thuật toán 2 bước:

    1. Exact match: nếu ≥1 reference có DOI/arXiv ID:
        - Group theo DOI (lowercase, normalized).
        - Group theo arXiv ID (lowercase).
    2. Fuzzy fallback: nếu thiếu identifier, dùng normalized title
        + first author last name + year. Threshold cẩn trọng
        (config.linking.duplicate_detection.title_year_author_similarity,
        default 0.92).

Trả DuplicateGroup: mỗi group có 1 canonical_id + list duplicate_ids.
ReferenceEntry KHÔNG thuộc group nào → unique.

Reference:
    v1.2 §3.5 (đối chiếu hai chiều, duplicate detection)
    v1.2 §3.6 (khử trùng lặp giữa các nguồn retrieval — cùng pattern, khác layer)
    config.linking.duplicate_detection.*
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz  # type: ignore[import-untyped]

from integrity_checker.config import get_settings
from integrity_checker.linking.statuses import ReferenceEntry

logger = logging.getLogger(__name__)


# --- Normalization helpers (v1.2 §3.4) ---

def _normalize_title(title: str) -> str:
    """Chuẩn hoá title để so khớp: lowercase, bỏ punctuation, gộp spaces."""
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _normalize_author_last_name(authors: list[str]) -> str:
    """Lấy last name của first author để so khớp."""
    if not authors:
        return ""
    first = authors[0].strip()
    if not first:
        return ""
    if "," in first:
        return first.split(",")[0].strip().lower()
    return first.split()[-1].strip().lower() if first.split() else ""


@dataclass
class DuplicateGroup:
    """Một nhóm reference entries trùng nhau.

    Attributes:
        canonical_id: reference_id được chọn làm canonical (mặc định: id đầu tiên).
        duplicate_ids: các reference_id còn lại trong nhóm.
        match_method: 'doi_exact' | 'arxiv_exact' | 'title_author_year_fuzzy'.
        similarity: 1.0 cho exact, 0.0–1.0 cho fuzzy.
    """

    canonical_id: str
    duplicate_ids: list[str] = field(default_factory=list)
    match_method: str = "unknown"
    similarity: float = 1.0


class DuplicateDetector:
    """Phát hiện reference entries mô tả cùng một công trình."""

    def __init__(self) -> None:
        s = get_settings()
        self.use_exact_identifier = s.linking.duplicate_detection.exact_identifier_match
        self.threshold = s.linking.duplicate_detection.title_year_author_similarity

    def find_duplicates(
        self, references: list[ReferenceEntry]
    ) -> list[DuplicateGroup]:
        """Tìm các nhóm duplicate trong danh sách reference entries.

        Returns:
            list[DuplicateGroup] — mỗi nhóm có ≥2 reference_id.
            Reference unique không xuất hiện.
        """
        groups: list[DuplicateGroup] = []
        assigned: set[str] = set()

        # --- Bước 1: exact DOI ---
        if self.use_exact_identifier:
            doi_groups = self._group_by_exact_identifier(
                references, key_attr="doi", method="doi_exact"
            )
            for g in doi_groups:
                groups.append(g)
                assigned.add(g.canonical_id)
                assigned.update(g.duplicate_ids)

        # --- Bước 1b: exact arXiv ID (cho entries chưa có DOI) ---
        if self.use_exact_identifier:
            remaining = [r for r in references if r.reference_id not in assigned]
            arxiv_groups = self._group_by_exact_identifier(
                remaining, key_attr="arxiv_id", method="arxiv_exact"
            )
            for g in arxiv_groups:
                groups.append(g)
                assigned.add(g.canonical_id)
                assigned.update(g.duplicate_ids)

        # --- Bước 2: fuzzy fallback cho entries còn lại ---
        remaining = [r for r in references if r.reference_id not in assigned]
        fuzzy_groups = self._group_by_title_author_year(remaining)
        groups.extend(fuzzy_groups)

        if groups:
            logger.info(
                "DuplicateDetector: %d duplicate groups out of %d references",
                len(groups),
                len(references),
            )
        return groups

    # -- internals --

    @staticmethod
    def _group_by_exact_identifier(
        references: list[ReferenceEntry],
        key_attr: str,
        method: str,
    ) -> list[DuplicateGroup]:
        """Group theo DOI hoặc arXiv ID exact (lowercase)."""
        buckets: dict[str, list[ReferenceEntry]] = {}
        for ref in references:
            key = getattr(ref, key_attr, None)
            if not key:
                continue
            key_norm = key.lower().strip()
            buckets.setdefault(key_norm, []).append(ref)

        groups: list[DuplicateGroup] = []
        for key, members in buckets.items():
            if len(members) < 2:
                continue
            canonical = members[0]
            duplicates = [m.reference_id for m in members[1:]]
            groups.append(
                DuplicateGroup(
                    canonical_id=canonical.reference_id,
                    duplicate_ids=duplicates,
                    match_method=method,
                    similarity=1.0,
                )
            )
            logger.debug(
                "Duplicate group %s: canonical=%s duplicates=%s",
                method,
                canonical.reference_id,
                duplicates,
            )
        return groups

    def _group_by_title_author_year(
        self, references: list[ReferenceEntry]
    ) -> list[DuplicateGroup]:
        """Group bằng normalized title + first author + year + threshold fuzzy."""
        # Index theo (last_name, year) trước để giảm cặp so sánh
        buckets: dict[tuple[str, str], list[ReferenceEntry]] = {}
        for ref in references:
            last = _normalize_author_last_name(ref.authors)
            year = (ref.year or "").strip()
            if not last or not year:
                continue
            buckets.setdefault((last, year), []).append(ref)

        groups: list[DuplicateGroup] = []
        for (last, year), members in buckets.items():
            if len(members) < 2:
                continue
            # O(n²) trong cùng bucket — bucket thường nhỏ (1–5 entries)
            n = len(members)
            parent = list(range(n))

            def find(x: int) -> int:
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x

            def union(a: int, b: int) -> None:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb

            for i in range(n):
                for j in range(i + 1, n):
                    sim = self._title_similarity(members[i], members[j])
                    if sim >= self.threshold:
                        union(i, j)

            # Gom cluster
            clusters: dict[int, list[int]] = {}
            for i in range(n):
                clusters.setdefault(find(i), []).append(i)

            for cluster_indices in clusters.values():
                if len(cluster_indices) < 2:
                    continue
                canonical = members[cluster_indices[0]]
                duplicates = [members[k].reference_id for k in cluster_indices[1:]]
                # Similarity = max pairwise trong cluster
                max_sim = 0.0
                for i_idx in cluster_indices:
                    for j_idx in cluster_indices:
                        if i_idx < j_idx:
                            max_sim = max(
                                max_sim,
                                self._title_similarity(members[i_idx], members[j_idx]),
                            )
                groups.append(
                    DuplicateGroup(
                        canonical_id=canonical.reference_id,
                        duplicate_ids=duplicates,
                        match_method="title_author_year_fuzzy",
                        similarity=round(max_sim, 4),
                    )
                )
        return groups

    @staticmethod
    def _title_similarity(a: ReferenceEntry, b: ReferenceEntry) -> float:
        """So khớp 2 title bằng token_set_ratio (RapidFuzz).

        Schema v1.2 §3.7: title lexical features = Levenshtein, token set/sort
        ratio, character n-gram. Ở đây dùng token_set_ratio làm đại diện.
        """
        ta = _normalize_title(a.title or "")
        tb = _normalize_title(b.title or "")
        if not ta or not tb:
            return 0.0
        return fuzz.token_set_ratio(ta, tb) / 100.0
