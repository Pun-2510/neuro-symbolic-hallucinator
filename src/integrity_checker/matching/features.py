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

        # DOI exact match (normalized + known arXiv/ACL equivalent DOIs + explicit arXiv ID)
        cit_doi_effective = citation.doi
        if not cit_doi_effective:
            from integrity_checker.retrieval.arxiv_client import ArxivClient

            arxiv_id = ArxivClient.extract_arxiv_id(citation)
            if arxiv_id:
                cit_doi_effective = f"10.48550/arxiv.{arxiv_id}"
        doi_match = self._doi_matches(cit_doi_effective, best.doi)

        # Venue similarity
        venue_sim = 0.0
        if citation.venue and best.venue:
            from integrity_checker.matching.venue_normalizer import VenueNormalizer

            venue_sim = VenueNormalizer().similarity(citation.venue, best.venue)

        # Content alignment (NEW v1.3 / v2.1) - Deep Neural Layer
        content_alignment_score = 0.0
        content_alignment_confidence = ""
        content_is_aligned = False
        title_context_sim = 0.0
        abstract_context_sim = 0.0
        best_evidence_sentence = ""
        best_evidence_score = 0.0
        best_cited_sentence = ""
        citation_intent = ""
        stance_label = ""
        cross_lingual_detected = False
        context_source = str(getattr(citation, "_context_source", "") or "")
        occurrence_alignments: list[dict] = []

        if self.enable_content_alignment and citation_context:
            # Resolve abstract across all agreeing candidates if best.abstract is missing
            resolved_abstract = getattr(best, "abstract", None)
            if not resolved_abstract:
                for cand in source.candidates:
                    cand_abs = getattr(cand, "abstract", None)
                    if cand.found and cand_abs:
                        cand_t = (cand.title or "").lower().strip()
                        if (
                            self._doi_matches(best.doi, cand.doi)
                            or self._compute_title_similarity(cand_title, cand_t) >= 0.80
                        ):
                            resolved_abstract = cand_abs
                            best.abstract = cand_abs
                            break

            alignment_result = self.semantic.check_content_alignment(
                cited_context=citation_context,
                source_title=best.title or "",
                source_abstract=resolved_abstract,
            )
            content_alignment_score = alignment_result.similarity
            content_alignment_confidence = alignment_result.confidence
            content_is_aligned = alignment_result.is_aligned
            title_context_sim = getattr(alignment_result, "title_context_sim", 0.0)
            abstract_context_sim = getattr(alignment_result, "abstract_context_sim", 0.0)
            best_evidence_sentence = getattr(alignment_result, "best_evidence_sentence", "")
            best_evidence_score = getattr(alignment_result, "best_evidence_score", 0.0)
            best_cited_sentence = getattr(alignment_result, "best_cited_sentence", "")
            citation_intent = getattr(alignment_result, "citation_intent", "")
            stance_label = getattr(alignment_result, "stance_label", "")
            cross_lingual_detected = bool(getattr(alignment_result, "cross_lingual_detected", False))

            # Evaluate multi-occurrence neural alignment when reference is cited multiple times
            occ_contexts = getattr(citation, "_occurrence_contexts", None)
            if (
                isinstance(occ_contexts, list)
                and len(occ_contexts) >= 1
                and hasattr(self.semantic, "check_multi_context_alignment")
            ):
                occurrence_alignments = self.semantic.check_multi_context_alignment(
                    occ_contexts,
                    source_title=best.title or "",
                    source_abstract=resolved_abstract,
                )
                if len(occurrence_alignments) >= 2:
                    if not context_source:
                        context_source = "multi_occurrence"
                    best_occ = max(occurrence_alignments, key=lambda o: float(o.get("score") or 0.0))
                    best_occ_score = float(best_occ.get("score") or 0.0)
                    if best_occ_score > content_alignment_score:
                        content_alignment_score = best_occ_score
                        content_alignment_confidence = str(best_occ.get("confidence") or content_alignment_confidence)
                        content_is_aligned = bool(best_occ.get("is_aligned"))
                        best_cited_sentence = str(best_occ.get("focal_sentence") or best_cited_sentence)
                        citation_intent = str(best_occ.get("intent") or citation_intent)
                        stance_label = str(best_occ.get("stance") or stance_label)
                        if best_occ.get("best_evidence_sentence"):
                            best_evidence_sentence = str(best_occ["best_evidence_sentence"])
                    # Preserve polarity contradiction if any occurrence explicitly refutes the paper
                    if any(
                        o.get("stance") == "contradiction_risk" and float(o.get("score") or 0.0) >= 0.30
                        for o in occurrence_alignments
                    ):
                        stance_label = "contradiction_risk"
            if not context_source:
                context_source = "in_text_citation"

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
            title_context_sim=title_context_sim,
            abstract_context_sim=abstract_context_sim,
            best_evidence_sentence=best_evidence_sentence,
            best_evidence_score=best_evidence_score,
            best_cited_sentence=best_cited_sentence,
            citation_intent=citation_intent,
            stance_label=stance_label,
            cross_lingual_detected=cross_lingual_detected,
            context_source=context_source,
            occurrence_alignments=occurrence_alignments,
        )

    @staticmethod
    def _year_distance(y1: str | int | None, y2: str | int | None) -> int:
        if not y1 or not y2:
            return 999
        m1 = re.search(r"\d{4}", str(y1))
        m2 = re.search(r"\d{4}", str(y2))
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

        # Normalize whitespace, ampersands, dashes, and trailing punctuation
        c_clean = re.sub(r"\s+", " ", citation_title.strip().rstrip(".,;:?!"))
        cand_clean = re.sub(r"\s+", " ", candidate_title.strip().rstrip(".,;:?!"))
        c_clean = re.sub(r"\s*&\s*", " and ", c_clean).replace("\u2013", "-").replace("\u2014", "-")
        cand_clean = re.sub(r"\s*&\s*", " and ", cand_clean).replace("\u2013", "-").replace("\u2014", "-")
        if not c_clean or not cand_clean:
            return 0.0

        # 1. Direct match (or match after removing hyphens/edition suffix, e.g. "Book Title, 5th Edition" vs "Book Title")
        if c_clean == cand_clean:
            return 1.0
        c_dehyph = re.sub(r"(?<=\w)-(?=\w)", "", c_clean)
        cand_dehyph = re.sub(r"(?<=\w)-(?=\w)", "", cand_clean)
        if c_dehyph == cand_dehyph:
            return 1.0
        from integrity_checker.retrieval.openlibrary_client import OpenLibraryClient
        c_no_ed = OpenLibraryClient.strip_edition_suffix(c_clean).lower().strip()
        cand_no_ed = OpenLibraryClient.strip_edition_suffix(cand_clean).lower().strip()
        if c_no_ed and cand_no_ed and c_no_ed == cand_no_ed:
            return 0.98

        c_base = c_no_ed or c_clean
        cand_base = cand_no_ed or cand_clean
        shorter, longer = (
            (c_base, cand_base)
            if len(c_base) <= len(cand_base)
            else (cand_base, c_base)
        )
        len_ratio = len(shorter) / len(longer) if longer else 0.0

        # 2. Safe prefix/colon-split match: either length ratio >= 0.65, or followed/preceded by a subtitle separator
        if len(shorter) >= 12 and longer.startswith(shorter):
            remainder = longer[len(shorter):].lstrip()
            if len_ratio >= 0.65 or (remainder and remainder[0] in ".:,-—–("):
                return 0.95
        if len(shorter) >= 12 and ":" in longer:
            parts = [p.strip() for p in longer.split(":", 1)]
            if shorter in parts:
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