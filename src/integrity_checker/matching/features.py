"""FeatureCalculator -- gộp fuzzy + semantic + author/year/DOI thành MatchFeatures.

v1.3: Bổ sung content alignment features cho Neural layer.
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.matching.author_matcher import author_match_score
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import MatchFeatures
from integrity_checker.matching.fuzzy import FuzzyMatcher
from integrity_checker.matching.semantic import SemanticMatcher


class FeatureCalculator:
    """Tính vector features giữa Citation và SourceCandidate tốt nhất.

    v1.2 task #29: Author matching dùng ``author_matcher`` (diacritics-fold +
    particle strip + last-name canonical). Trước đó dùng naive lowercase
    (sẽ fail cho "Nguyễn" vs "Nguyen" / "van der Berg" / "Smith J. K.").

    2026-09-15: SemanticMatcher uses singleton pattern to avoid reloading
    the ML model on each instantiation (~5s speedup per pipeline run).

    v1.3: Bổ sung content alignment check -- so sánh citation context
    với source metadata bằng Neural embeddings.
    """

    def __init__(
        self,
        fuzzy: FuzzyMatcher | None = None,
        semantic: SemanticMatcher | None = None,
        enable_content_alignment: bool = True,
    ) -> None:
        self.fuzzy = fuzzy or FuzzyMatcher()
        self.semantic = semantic or SemanticMatcher.get_instance()
        self.enable_content_alignment = enable_content_alignment

    def compute(
        self,
        citation: Citation,
        source: SourceResult,
        citation_context: Optional[str] = None,
    ) -> MatchFeatures:
        """Tính features dựa trên candidate tốt nhất (highest confidence).

        Args:
            citation: Citation từ PDF extraction
            source: SourceResult từ retrieval
            citation_context: Optional context xung quanh citation (cho content alignment)
        """
        best = source.best_candidate()
        if best is None:
            return MatchFeatures(source_consensus=source.consensus_count())

        # Title sim
        c_title = (citation.title or citation.raw_text).lower().strip()
        cand_title = (best.title or "").lower().strip()

        fuzzy_sim = self.fuzzy.token_set_ratio(c_title, cand_title)
        semantic_sim = self.semantic.similarity(citation.title or citation.raw_text, best.title or "")

        # Author Jaccard -- upgraded to author_matcher (task #29)
        author_sim = author_match_score(
            list(citation.authors or []),
            list(best.authors or []),
        )

        # Year distance
        year_dist = self._year_distance(citation.year, best.year)

        # DOI exact match
        doi_match = bool(
            citation.doi and best.doi and citation.doi.lower() == best.doi.lower()
        )

        # Content alignment (NEW v1.3) - Neural layer
        content_alignment_score = 0.0
        content_alignment_confidence = ""
        content_is_aligned = False

        if self.enable_content_alignment and citation_context:
            alignment_result = self.semantic.check_content_alignment(
                cited_context=citation_context,
                source_title=best.title or "",
                source_abstract=best.abstract if hasattr(best, "abstract") else None,
            )
            content_alignment_score = alignment_result.similarity
            content_alignment_confidence = alignment_result.confidence
            content_is_aligned = alignment_result.is_aligned

        return MatchFeatures(
            title_sim_fuzzy=fuzzy_sim,
            title_sim_semantic=semantic_sim,
            author_jaccard=author_sim,
            year_distance=year_dist,
            doi_exact_match=doi_match,
            source_consensus=source.consensus_count(),
            content_alignment_score=content_alignment_score,
            content_alignment_confidence=content_alignment_confidence,
            content_is_aligned=content_is_aligned,
        )

    @staticmethod
    def _year_distance(y1: str | None, y2: str | None) -> int:
        if not y1 or not y2:
            return 999
        m1 = re.search(r"\d{4}", y1)
        m2 = re.search(r"\d{4}", y2)
        if not m1 or not m2:
            return 999
        return abs(int(m1.group(0)) - int(m2.group(0)))