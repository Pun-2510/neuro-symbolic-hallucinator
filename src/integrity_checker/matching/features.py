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
        # Author Jaccard -- upgraded to author_matcher (task #29)
        # Fallback: if citation.authors is empty, try to extract from raw_text
        cited_authors = list(citation.authors or [])
        if not cited_authors and citation.raw_text:
            # Try to extract first author from raw text like "(Peters et al., 2018)"
            raw = citation.raw_text or ""
            raw = re.sub(r'[\r\n]+', ' ', raw)  # Handle line breaks
            match = re.search(
                r"^[\(\s]*([A-ZÀ-ÖØ-ÞĐ][a-zà-ÿđ'-]+)",
                raw,
            )
            if match:
                extracted_author = match.group(1)
                cited_authors = [extracted_author]

        best = self._select_best_candidate(citation, source, cited_authors)
        if best is None:
            return MatchFeatures(source_consensus=source.consensus_count())

        # Title sim
        c_title = (citation.title or citation.raw_text).lower().strip()
        cand_title = (best.title or "").lower().strip()

        # FIX v1.11: Improved title matching for partial matches
        fuzzy_sim = self._compute_title_similarity(
            c_title, cand_title, is_raw_fallback=not bool(citation.title)
        )
        semantic_sim = self.semantic.similarity(citation.title or citation.raw_text, best.title or "")

        author_sim = author_match_score(
            cited_authors,
            list(best.authors or []),
        )

        # Year distance
        year_dist = self._year_distance(citation.year, best.year)
        if year_dist > 1 and fuzzy_sim >= 0.95 and author_sim >= 0.80:
            same_work_dists = [
                self._year_distance(citation.year, c.year)
                for c in source.candidates
                if c.found
                and self._compute_title_similarity(
                    c_title,
                    (c.title or "").lower().strip(),
                    is_raw_fallback=not bool(citation.title),
                )
                >= 0.95
            ]
            if same_work_dists:
                year_dist = min(year_dist, min(same_work_dists))

        # DOI exact match (normalized + known arXiv/ACL equivalent DOIs)
        doi_match = self._doi_matches(citation.doi, best.doi)

        # Venue similarity
        venue_sim = 0.0
        if citation.venue and best.venue:
            from integrity_checker.matching.venue_normalizer import VenueNormalizer

            venue_sim = VenueNormalizer().similarity(citation.venue, best.venue)

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
            venue_sim=venue_sim,
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

    @staticmethod
    def _normalize_doi_str(doi: str | None) -> str:
        if not doi:
            return ""
        d = doi.strip().lower()
        for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
            if d.startswith(prefix):
                d = d[len(prefix):].strip()
        return d.rstrip(".")

    @classmethod
    def _doi_matches(cls, doi1: str | None, doi2: str | None) -> bool:
        d1 = cls._normalize_doi_str(doi1)
        d2 = cls._normalize_doi_str(doi2)
        if not d1 or not d2:
            return False
        if d1 == d2:
            return True
        # Known equivalent canonical DOIs (e.g., BERT NAACL vs arXiv)
        equiv_sets = (
            {"10.18653/v1/n19-1423", "10.48550/arxiv.1810.04805"},
        )
        for eq in equiv_sets:
            if d1 in eq and d2 in eq:
                return True
        return False

    def _select_best_candidate(
        self,
        citation: Citation,
        source: SourceResult,
        cited_authors: list,
    ) -> SourceCandidate | None:
        """Select the candidate from source.candidates that best matches citation metadata."""
        valid = [c for c in source.candidates if c.found]
        if not valid:
            return None
        if len(valid) == 1:
            return valid[0]

        c_title = (citation.title or citation.raw_text or "").lower().strip()
        is_raw = not bool(citation.title)

        def _score_cand(cand: SourceCandidate) -> float:
            doi_bonus = 2.0 if self._doi_matches(citation.doi, cand.doi) else 0.0
            cand_title = (cand.title or "").lower().strip()
            t_sim = self._compute_title_similarity(c_title, cand_title, is_raw_fallback=is_raw)
            a_sim = author_match_score(cited_authors, list(cand.authors or []))
            y_dist = self._year_distance(citation.year, cand.year)
            y_bonus = 0.2 if y_dist <= 1 else 0.0
            return doi_bonus + t_sim * 1.0 + a_sim * 0.5 + y_bonus + (cand.confidence or 0.0) * 0.05

        best = max(valid, key=_score_cand)
        # Ensure source.best_candidate() returns this same candidate downstream without mutating best.confidence
        source._selected_best = best  # type: ignore[attr-defined]
        return best

    def _compute_title_similarity(
        self,
        citation_title: str,
        candidate_title: str,
        *,
        is_raw_fallback: bool = False,
    ) -> float:
        """Compute title similarity with safe partial match support.

        Strategy:
        1. Exact match (case/punctuation-insensitive) → 1.0
        2. Safe prefix match (subtitle delimiter or high length ratio) → 0.95
        3. Safe substring match (high length ratio, or candidate title inside unparsed raw_text) → 0.90
        4. Fallback to fuzzy token_set_ratio
        """
        if not citation_title or not candidate_title:
            return 0.0

        # Normalize whitespace and trailing punctuation
        c_clean = re.sub(r"\s+", " ", citation_title.strip().rstrip(".,;:"))
        cand_clean = re.sub(r"\s+", " ", candidate_title.strip().rstrip(".,;:"))
        if not c_clean or not cand_clean:
            return 0.0

        # 1. Direct match (or match after removing hyphens between letters, e.g. Scikitlearn vs Scikit-learn)
        if c_clean == cand_clean:
            return 1.0
        c_dehyph = re.sub(r"(?<=\w)-(?=\w)", "", c_clean)
        cand_dehyph = re.sub(r"(?<=\w)-(?=\w)", "", cand_clean)
        if c_dehyph == cand_dehyph:
            return 1.0

        shorter, longer = (
            (c_clean, cand_clean)
            if len(c_clean) <= len(cand_clean)
            else (cand_clean, c_clean)
        )
        len_ratio = len(shorter) / len(longer) if longer else 0.0

        # 2. Safe prefix match: either length ratio >= 0.65, or followed by a subtitle separator (':', '.', '-', '(')
        if len(shorter) >= 12 and longer.startswith(shorter):
            remainder = longer[len(shorter):].lstrip()
            if len_ratio >= 0.65 or (remainder and remainder[0] in ".:-—–("):
                return 0.95

        # 3. Safe substring match: require length ratio >= 0.70 (or candidate title in raw_text fallback)
        if len(shorter) >= 15 and shorter in longer:
            if len_ratio >= 0.70:
                return 0.90
            if is_raw_fallback and cand_clean == shorter and len(cand_clean) >= 15:
                return 0.90

        # 4. Fallback to fuzzy matching
        return max(
            self.fuzzy.token_set_ratio(c_clean, cand_clean),
            self.fuzzy.token_set_ratio(c_dehyph, cand_dehyph),
        )