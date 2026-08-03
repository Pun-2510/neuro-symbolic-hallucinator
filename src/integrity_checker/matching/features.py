"""FeatureCalculator — gộp fuzzy + semantic + author/year/DOI thành MatchFeatures."""

from __future__ import annotations

import re

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
    """

    def __init__(self, fuzzy: FuzzyMatcher | None = None, semantic: SemanticMatcher | None = None) -> None:
        self.fuzzy = fuzzy or FuzzyMatcher()
        self.semantic = semantic or SemanticMatcher()

    def compute(self, citation: Citation, source: SourceResult) -> MatchFeatures:
        """Tính features dựa trên candidate tốt nhất (highest confidence)."""
        best = source.best_candidate()
        if best is None:
            return MatchFeatures(source_consensus=source.consensus_count())

        # Title sim
        c_title = (citation.title or citation.raw_text).lower().strip()
        cand_title = (best.title or "").lower().strip()

        fuzzy_sim = self.fuzzy.token_set_ratio(c_title, cand_title)
        semantic_sim = self.semantic.similarity(citation.title or citation.raw_text, best.title or "")

        # Author Jaccard — upgraded to author_matcher (task #29)
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

        return MatchFeatures(
            title_sim_fuzzy=fuzzy_sim,
            title_sim_semantic=semantic_sim,
            author_jaccard=author_sim,
            year_distance=year_dist,
            doi_exact_match=doi_match,
            source_consensus=source.consensus_count(),
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