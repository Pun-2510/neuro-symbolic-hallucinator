"""NeuroSymbolicChecker -- orchestrate neural features + symbolic rules.

v1.3: Bổ sung content alignment check (Neural layer) để kiểm tra semantic
alignment giữa đoạn văn được trích dẫn và paper nguồn.

Đây là component chính thể hiện tính "Neuro-Symbolic":
    - Neural: Sentence-BERT embeddings cho content-context alignment
    - Symbolic: Bộ quy tắc regex, logic validation cho decision making
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from integrity_checker.config import get_settings
from integrity_checker.extraction.patterns.apa import is_vn_legal_reference
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import CitationVerdict, MatchFeatures, ValidationLabel
from integrity_checker.matching.features import FeatureCalculator
from integrity_checker.logic.calibration import HybridMLScorer
from integrity_checker.logic.rules import SymbolicRules, _is_fake_url
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator

if TYPE_CHECKING:
    from integrity_checker.linking.statuses import CitationMappingStatus, StyleProfile

logger = get_logger(__name__)

# Precompiled module-level web/non-scholarly resource patterns (avoid re-compiling per citation)
_WEB_RESOURCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Company, "Product/Service Name," Company
    re.compile(
        r'^(Google|Microsoft|Amazon|Apple|Facebook|Meta|Twitter|GitHub|IBM|Intel|'
        r'Nvidia|Adobe|Atlassian|Oracle|Salesforce|'
        r'OpenAI|Anthropic|Hugging\s*Face|Replicate|Cohere),?\s*["“]',
        re.IGNORECASE,
    ),
    # "Product/Service Name," Organization (title-first pattern)
    re.compile(
        r'^["“](YouTube\s*Data\s*API|Google\s*API|AWS\s*SDK|'
        r'Rest\s*API|GraphQL|Webhook|Twilio|Stripe|OpenAI|Anthropic)\b',
        re.IGNORECASE,
    ),
    # Developer/Documentation keyword sau citation
    re.compile(
        r'(Google\s+for\s+Developers|Developer\s+Documentation|'
        r'API\s+Reference|API\s+Documentation|REST\s+API\s+Documentation|'
        r'Academic\s+Graph\s+API|Getting\s+Started|REST\s+API|'
        r'The\s+DOI\s+Handbook)\s*[.,]',
        re.IGNORECASE,
    ),
    # Web portal / online documentation / archive with explicit URL and no DOI
    re.compile(
        r'\b(ACL\s+Anthology|Crossref\s+REST\s+API|Semantic\s+Scholar\s+(?:Academic\s+Graph\s+API|Open\s+Research\s+Corpus)|'
        r'OpenAlex\s*:\s*An\s+open\s+catalogue|Handbook\s+of\s+the\s+DOI\s+Resolution\s+System|'
        r'The\s+DOI\s+Handbook)\b.*?(?:\bRe-?\s*trieved\s+from\s+)?https?://',
        re.IGNORECASE,
    ),
    re.compile(
        r'https?://(?:www\.)?who\.int/(?:news-room|fact-sheets)/',
        re.IGNORECASE,
    ),
    # Company name + API/SDK/Tool keyword (short form từ GROBID)
    re.compile(
        r'^(Google|Amazon|Microsoft|GitHub|IBM|Intel|Nvidia)\s+'
        r'(YouTube|Maps|AWS|Vertex|TensorFlow|BERT|Cloud|Compute|S3|'
        r'Data\s*API|API|SDK|Tool)\b',
        re.IGNORECASE,
    ),
    # Common API/SDK patterns: "X API v3" hoặc "X Data API"
    re.compile(
        r'^(Google\s+YouTube\s+Data\s*API|YouTube\s+Data\s*API|'
        r'Google\s+API|Vertex\s+AI|Google\s+Cloud)',
        re.IGNORECASE,
    ),
    # Product/API documentation anywhere in citation
    re.compile(
        r'\b(YouTube\s+Data\s*API\s+v\d+|Google\s+for\s+Developers)\b',
        re.IGNORECASE,
    ),
    # Computer software / GitHub repository without academic venue
    re.compile(
        r'(\[Computer\s+software\]|\bGitHub\.\s*Retrieved\b)',
        re.IGNORECASE,
    ),
    # Classical / scriptural / public-domain / dictionary reference works
    re.compile(
        r'\b(The\s+Bible|ESV\s+ed\.|Project\s+Gutenberg|gutenberg\.org|'
        r'Dictionary\.com|Merriam-Webster|Encyclop(?:ae|e)dia\s+Britannica)\b',
        re.IGNORECASE,
    ),
    # Non-scholarly consumer / book-review / blog / magazine / media web domains & paths
    re.compile(
        r'(?:goodreads\.com|barnesandnoble\.com|blogspot\.com|wordpress\.com|substack\.com|'
        r'pbs\.org|popsugar\.com|publishersweekly\.com|eviemagazine\.com|swooon\.com|'
        r'fightthenewdrug\.org|publicsquaremag\.org|wheatley\.byu\.edu|'
        r'clarendonhousebooks\.com|shamelessbookdeals\.com|sexandpsychology\.com|'
        r'libbylife\.com|beforewegoblog\.com|thebooknookchronicles\.com|'
        r'peanutblossombookclub\.com|prettylittlememoirs\.com|beachreadsandbubbly\.com|'
        r'bookishgoblin\.com|estapinto\.com|amysuto\.com|penguinrandomhouse\.com/the-read-down|'
        r'/book-blog/|/book-review|spicy-chapters|#BookTok)',
        re.IGNORECASE,
    ),
)


class NeuroSymbolicChecker:
    """Kết hợp:
        - Neural: feature vector từ FeatureCalculator (bao gồm semantic content alignment)
        - Symbolic: SymbolicRules decision table

    v1.3: Bổ sung citation context để compute content alignment.
    Citation context = đoạn văn xung quanh citation trong essay,
    dùng để kiểm tra semantic alignment với paper nguồn.

    v1.2 §3.2.2 (task #33): check() giờ nhận thêm ``mapping_status`` +
    ``style_profile`` để SymbolicRules có đủ input cho rules mở rộng.

    2026-09-15: Uses SemanticMatcher singleton for ~5s performance improvement
    by avoiding model reload on each instantiation.

    FIX Bug 5: Now checks for known seminal papers and returns VERIFIED
    with high confidence even when APIs fail.

    # TODO(user): tuần 12–13 -- bổ sung:
        - Thêm classifier ML (LogisticRegression / XGBoost) như baseline B4
        - Calibration layer (Platt scaling) cho confidence
    """

    _feature_calculator: FeatureCalculator | None = None
    _hybrid_scorer: HybridMLScorer | None = None

    def __init__(
        self,
        feature_calculator: FeatureCalculator | None = None,
        rules: SymbolicRules | None = None,
        enable_content_alignment: bool = True,
        hybrid_scorer: HybridMLScorer | None = None,
        enable_calibration: bool = True,
    ) -> None:
        # Reuse shared FeatureCalculator instance to benefit from SemanticMatcher singleton
        if feature_calculator is not None:
            self.feature_calculator = feature_calculator
        else:
            if NeuroSymbolicChecker._feature_calculator is None:
                NeuroSymbolicChecker._feature_calculator = FeatureCalculator(
                    enable_content_alignment=enable_content_alignment
                )
            self.feature_calculator = NeuroSymbolicChecker._feature_calculator
        self.rules = rules or SymbolicRules()
        self.enable_content_alignment = enable_content_alignment
        self.enable_calibration = enable_calibration
        if hybrid_scorer is not None:
            self.hybrid_scorer = hybrid_scorer
        else:
            if NeuroSymbolicChecker._hybrid_scorer is None:
                NeuroSymbolicChecker._hybrid_scorer = HybridMLScorer.load_default()
            self.hybrid_scorer = NeuroSymbolicChecker._hybrid_scorer

    def check(
        self,
        citation: Citation,
        source: SourceResult,
        mapping_status: "CitationMappingStatus | None" = None,
        style_profile: "StyleProfile | None" = None,
        citation_context: Optional[str] = None,
        # NEW v1.3: Provenance tracking
        api_exhausted: bool = False,
        used_local_db: bool = False,
    ) -> CitationVerdict:
        """Trả CitationVerdict đầy đủ (label + confidence + reasoning + features).

        Args:
            citation: Citation từ PDF extraction
            source: SourceResult từ retrieval (API calls)
            mapping_status: CitationMappingStatus từ CitationLinker
            style_profile: StyleProfile từ StyleDetector
            citation_context: Đoạn văn xung quanh citation (cho Neural content alignment)

        FIX Bug 5: If citation matches a known seminal paper, return VERIFIED
        with high confidence even when all APIs fail.
        """
        # FIX v1.4 + v1.5: Check for URL/resource citations - classify as RESOURCE.
        # Robust against trailing punctuation (e.g. URL at end of sentence
        # like "see https://github.com/foo/bar.") by stripping trailing
        # `.,;:)]"'` before matching the URL prefix.
        import re
        raw_text = citation.raw_text or ""
        stripped_text = raw_text.strip()
        # Strip trailing punctuation that commonly follows a URL in running text.
        url_candidate = stripped_text.rstrip(".,;:)\"'")
        # Match if the candidate starts with an URL scheme. The previous regex
        # required the whole string to be one URL (`^...$`), which failed when
        # trailing punctuation was present.
        url_prefix_pattern = re.compile(r'^(https?://|www\.)[^\s]+', re.IGNORECASE)
        # Require the URL body to be at least 10 chars after the scheme prefix
        # to reduce false positives (e.g. a sentence starting with "www").
        prefix_match = re.match(r'^(https?://|www\.)', url_candidate, re.IGNORECASE)
        url_body_match = re.match(
            r'^(?:https?://|www\.)(\S{10,})$', url_candidate, re.IGNORECASE
        )
        if prefix_match and url_body_match and not url_candidate[len(prefix_match.group(0)):].startswith((" ", "\n", "\t")):
            logger.debug(
                f"URL/RESOURCE detected: raw='{raw_text[:80]}' "
                f"-> url_candidate='{url_candidate[:80]}'"
            )
            return CitationVerdict(
                citation=citation,
                label=ValidationLabel.RESOURCE,
                confidence=0.95,
                matched_source=source,
                features=MatchFeatures(),
                reasoning=f"URL/Reference link detected: {raw_text[:60]}... (not an academic citation)",
                triggered_rules=["R-URL-RESOURCE"],
                mismatched_fields=[],
            )

        # --- Check 2: Web resource/API citations (không bắt đầu bằng URL) ---
        check_resource_str = " ".join(
            part
            for part in (raw_text, citation.title or "", citation.url or "", citation.venue or "")
            if part
        )
        for pattern in _WEB_RESOURCE_PATTERNS:
            if not citation.doi and pattern.search(check_resource_str):
                logger.debug(
                    f"Web resource/API detected: raw='{raw_text[:80]}' "
                    f"matched pattern: {pattern.pattern[:50]}"
                )
                return CitationVerdict(
                    citation=citation,
                    label=ValidationLabel.RESOURCE,
                    confidence=0.95,
                    matched_source=source,
                    features=MatchFeatures(),
                    reasoning=f"Web resource/API citation detected: {raw_text[:60]}... (not an academic paper)",
                    triggered_rules=["R-WEB-RESOURCE"],
                    mismatched_fields=[],
                )

        # --- Check 3: Vietnamese legal documents (TDTU §2.6.1) ---
        if citation.matched_pattern == "vn_legal_document" or is_vn_legal_reference(raw_text):
            logger.debug(f"Vietnamese legal document detected: raw='{raw_text[:80]}'")
            return CitationVerdict(
                citation=citation,
                label=ValidationLabel.RESOURCE,
                confidence=0.95,
                matched_source=source,
                features=MatchFeatures(),
                reasoning=f"Vietnamese legal document detected: {raw_text[:60]}... (statutory/regulatory source)",
                triggered_rules=["R-LEGAL-DOCUMENT"],
                mismatched_fields=[],
            )

        # --- Check 4: Unified RetrievalOrchestrator web/documentation resource check ---
        has_fake_url_early, _ = _is_fake_url(citation.url)
        is_dead_url_early = getattr(source, "url_status", None) == "dead_link"
        if (
            not has_fake_url_early
            and not is_dead_url_early
            and RetrievalOrchestrator.is_web_or_legal_resource(citation)
        ):
            http_note = (
                f" (HTTP {getattr(source, 'url_status_code', None) or 200} OK)"
                if getattr(source, "url_status", None) in ("alive", "restricted_alive")
                else ""
            )
            return CitationVerdict(
                citation=citation,
                label=ValidationLabel.RESOURCE,
                confidence=0.95,
                matched_source=source,
                features=MatchFeatures(),
                reasoning=f"Web/documentation resource detected{http_note}: {raw_text[:70]}... (non-scholarly URL resource)",
                triggered_rules=["R-WEB-RESOURCE"],
                mismatched_fields=[],
            )

        # Debug aid: if raw_text starts with URL scheme but didn't match, log it.
        if re.match(r'^(https?://|www\.)', stripped_text, re.IGNORECASE):
            logger.debug(
                f"URL-like raw_text but no RESOURCE match: raw='{raw_text[:80]}' "
                f"url_candidate='{url_candidate[:80]}'"
            )

        # FIX Bug 5: Check for known seminal papers first (skip if fake URL or fabricated DOI)
        # FIX v1.5: Now checks title similarity to detect METADATA_ERROR
        has_fake_url, _ = _is_fake_url(citation.url)
        has_fabricated_doi = self.rules._is_fabricated_doi(citation.doi)
        is_known, paper_info = RetrievalOrchestrator.is_known_paper(citation)
        if is_known and paper_info and not has_fake_url and not has_fabricated_doi:
            known_year = paper_info.get("year") or (
                str(citation.year)[:4] if citation.year else None
            )
            # Create a synthetic SourceCandidate from known paper info (preserving abstract)
            existing_abs = paper_info.get("abstract") or next(
                (c.abstract for c in source.candidates if getattr(c, "abstract", None)),
                None,
            )
            known_candidate = SourceCandidate(
                source_name="known_papers",
                found=True,
                title=paper_info.get("title"),
                doi=paper_info.get("doi"),
                authors=paper_info.get("authors", []),
                year=known_year,
                abstract=existing_abs,
                confidence=0.95,
                score=1.0,
            )

            # Avoid duplicating known_papers if RetrievalOrchestrator already injected it
            other_cands = [
                c for c in source.candidates if c.source_name != "known_papers"
            ]
            other_queried = [
                s for s in source.sources_queried if s != "known_papers"
            ]
            other_succeeded = [
                s for s in source.sources_succeeded if s != "known_papers"
            ]

            # FIX v1.5: Check title similarity to detect METADATA_ERROR
            # If citation has a title and it doesn't match the known paper's title:
            # First check if a live/local_db source already found a real paper matching citation.title
            # (e.g., another paper by the same first author in the same year, like Kaiser & Bengio 2016).
            citation_title = citation.title
            known_title = paper_info.get("title", "")

            if citation_title and known_title:
                # Calculate title similarity using FuzzyMatcher
                title_sim = self.rules.fuzzy.token_set_ratio(
                    citation_title.lower(), known_title.lower()
                )
                title_sim_threshold = 0.5  # Below this = likely wrong title

                if title_sim < title_sim_threshold:
                    # Check if a live/local_db source already found a real paper matching citation.title
                    # (e.g., another paper by the same first author in the same year, like Kaiser & Bengio 2016)
                    has_real_matching_candidate = any(
                        cand.found
                        and cand.title
                        and self.rules.fuzzy.token_set_ratio(
                            citation_title.lower(), cand.title.lower()
                        )
                        >= 0.70
                        for cand in other_cands
                    )
                    if not has_real_matching_candidate:
                        # Title doesn't match and no other real paper matched → METADATA_ERROR
                        enhanced_source = SourceResult(
                            citation_raw=source.citation_raw,
                            candidates=[known_candidate] + other_cands,
                            sources_queried=["known_papers"] + other_queried,
                            sources_succeeded=["known_papers"] + other_succeeded,
                            sources_failed=source.sources_failed,
                            api_exhausted=source.api_exhausted,
                            url_status=source.url_status,
                            url_status_code=source.url_status_code,
                        )
                        features = self.feature_calculator.compute(citation, enhanced_source, citation_context)

                        return self._apply_dead_link_exception(
                            CitationVerdict(
                                citation=citation,
                                label=ValidationLabel.METADATA_ERROR,
                                confidence=0.75,
                                matched_source=enhanced_source,
                                features=features,
                                reasoning=f"Known author '{citation.authors[0] if citation.authors else 'unknown'}' found, "
                                          f"but title '{citation_title}' does not match known paper '{known_title}' "
                                          f"(similarity: {title_sim:.2f}). This appears to be a wrong title attribution.",
                                triggered_rules=["R-KNOWN-PAPER", "R-TITLE-MISMATCH"],
                                mismatched_fields=["title"],
                            ),
                            enhanced_source,
                        )
                    # Otherwise fall through to normal verification of the real matching candidate
                else:
                    # Title matches known paper → VERIFIED
                    enhanced_source = SourceResult(
                        citation_raw=source.citation_raw,
                        candidates=[known_candidate] + other_cands,
                        sources_queried=["known_papers"] + other_queried,
                        sources_succeeded=["known_papers"] + other_succeeded,
                        sources_failed=source.sources_failed,
                        api_exhausted=source.api_exhausted,
                        url_status=source.url_status,
                        url_status_code=source.url_status_code,
                    )
                    features = self.feature_calculator.compute(citation, enhanced_source, citation_context)
                    known_rules = ["R-KNOWN-PAPER"]
                    if (
                        self.enable_content_alignment
                        and citation_context
                        and getattr(features, "stance_label", "") == "contradiction_risk"
                        and not getattr(features, "cross_lingual_detected", False)
                    ):
                        known_rules.append("R-CONTENT-MISMATCH")
                    base_reason = (
                        f"Known seminal paper verified via known papers database: '{paper_info.get('title')}'. "
                        "APIs failed but paper is well-documented."
                    )

                    return self._apply_dead_link_exception(
                        CitationVerdict(
                            citation=citation,
                            label=ValidationLabel.VERIFIED,
                            confidence=0.90,
                            matched_source=enhanced_source,
                            features=features,
                            reasoning=self._enhance_reasoning_with_neural(
                                base_reason, features, known_rules
                            ),
                            triggered_rules=known_rules,
                            mismatched_fields=[],
                        ),
                        enhanced_source,
                    )
            else:
                # Citation has no title (in-text citation) → VERIFIED via known paper
                enhanced_source = SourceResult(
                    citation_raw=source.citation_raw,
                    candidates=[known_candidate] + other_cands,
                    sources_queried=["known_papers"] + other_queried,
                    sources_succeeded=["known_papers"] + other_succeeded,
                    sources_failed=source.sources_failed,
                    api_exhausted=source.api_exhausted,
                    url_status=source.url_status,
                    url_status_code=source.url_status_code,
                )
                features = self.feature_calculator.compute(citation, enhanced_source, citation_context)
                known_rules = ["R-KNOWN-PAPER"]
                if (
                    self.enable_content_alignment
                    and citation_context
                    and getattr(features, "stance_label", "") == "contradiction_risk"
                    and not getattr(features, "cross_lingual_detected", False)
                ):
                    known_rules.append("R-CONTENT-MISMATCH")
                base_reason = (
                    f"Known seminal paper verified via known papers database: '{paper_info.get('title')}'. "
                    "APIs failed but paper is well-documented."
                )

                return self._apply_dead_link_exception(
                    CitationVerdict(
                        citation=citation,
                        label=ValidationLabel.VERIFIED,
                        confidence=0.90,
                        matched_source=enhanced_source,
                        features=features,
                        reasoning=self._enhance_reasoning_with_neural(
                            base_reason, features, known_rules
                        ),
                        triggered_rules=known_rules,
                        mismatched_fields=[],
                    ),
                    enhanced_source,
                )

        # Compute features với context (nếu có) cho Neural content alignment
        features = self.feature_calculator.compute(citation, source, citation_context)

        # Apply symbolic rules với content alignment features
        outcome = self.rules.apply(
            features,
            source,
            mapping_status=mapping_status,
            style_profile=style_profile,
            citation_doi=citation.doi,
            citation_url=citation.url,
            # NEW v1.3: Provenance tracking
            api_exhausted=api_exhausted,
            used_local_db=used_local_db,
            # NEW v1.3: Citation info for METADATA_ERROR detection
            citation_authors=citation.authors,
            citation_year=citation.year,
            citation_raw=citation.raw_text,
        )

        final_rules = list(outcome.triggered_rules)
        if (
            self.enable_content_alignment
            and citation_context
            and getattr(features, "stance_label", "") == "contradiction_risk"
            and not getattr(features, "cross_lingual_detected", False)
            and "R-CONTENT-MISMATCH" not in final_rules
        ):
            final_rules.append("R-CONTENT-MISMATCH")

        # Enhance reasoning với content alignment info (Neural layer feedback)
        enhanced_reasoning = self._enhance_reasoning_with_neural(
            outcome.reasoning, features, final_rules
        )

        final_confidence = outcome.confidence
        if self.enable_calibration and self.hybrid_scorer is not None and outcome.confidence > 0.0:
            has_cand = any(getattr(c, "found", True) for c in (source.candidates or []))
            final_confidence = self.hybrid_scorer.calibrate_verdict_confidence(
                symbolic_label=outcome.label.value,
                symbolic_confidence=outcome.confidence,
                features=features,
                has_candidate=has_cand,
                style_penalty=outcome.style_penalty,
            )
            if "R-AMBIGUOUS-MAPPING" in final_rules:
                final_confidence = min(final_confidence, self.rules.ambiguous_confidence_cap)

        return self._apply_dead_link_exception(
            CitationVerdict(
                citation=citation,
                label=outcome.label,
                confidence=final_confidence,
                matched_source=source,
                features=features,
                reasoning=enhanced_reasoning,
                triggered_rules=final_rules,
                mismatched_fields=list(outcome.mismatched_fields),
                style_penalty=outcome.style_penalty,
                domain_exception=outcome.domain_exception,
            ),
            source,
        )

    @staticmethod
    def _apply_dead_link_exception(
        verdict: CitationVerdict,
        source: SourceResult,
    ) -> CitationVerdict:
        """If scholarly record is verified/matched but the cited URL is dead, flag domain_exception."""
        if (
            getattr(source, "url_status", None) == "dead_link"
            and verdict.label in (ValidationLabel.VERIFIED, ValidationLabel.METADATA_ERROR)
        ):
            verdict.domain_exception = True
            if "R-DOMAIN-EXCEPTION" not in verdict.triggered_rules:
                verdict.triggered_rules.append("R-DOMAIN-EXCEPTION")
            if "R-BROKEN-LINK" not in verdict.triggered_rules:
                verdict.triggered_rules.append("R-BROKEN-LINK")
            if "url" not in verdict.mismatched_fields:
                verdict.mismatched_fields.append("url")
            verdict.reasoning += (
                " [Link check: Cited URL is dead/unreachable, but scholarly record exists in academic registries.]"
            )
        return verdict

    def _enhance_reasoning_with_neural(
        self,
        symbolic_reasoning: str,
        features: MatchFeatures,
        triggered_rules: list[str],
    ) -> str:
        """Enhance symbolic reasoning với Neural content alignment & evidence info."""
        if not self.enable_content_alignment:
            return symbolic_reasoning

        stance = getattr(features, "stance_label", "")
        if features.content_alignment_score > 0 or stance == "contradiction_risk":
            alignment_info = (
                f" [Neural: content alignment score={features.content_alignment_score:.2f} "
                f"({features.content_alignment_confidence})"
            )
            intent = getattr(features, "citation_intent", "")
            ev_score = getattr(features, "best_evidence_score", 0.0)
            if intent:
                alignment_info += f", intent={intent}"
            if stance:
                alignment_info += f", stance={stance}"
            if ev_score and ev_score > 0:
                alignment_info += f", evidence_sim={ev_score:.2f}"
            if getattr(features, "cross_lingual_detected", False):
                alignment_info += ", cross_lingual=VI->EN"

            if stance == "contradiction_risk":
                alignment_info += " - WARNING: citation claim may contradict or be off-topic from source"
            elif features.content_is_aligned and "VERIFIED" not in triggered_rules:
                alignment_info += " - content semantically aligned with source"
            elif not features.content_is_aligned and features.content_alignment_score > 0.3:
                alignment_info += " - WARNING: content may not align with source"

            alignment_info += "]"
            return symbolic_reasoning + alignment_info

        return symbolic_reasoning
