"""NeuroSymbolicChecker -- orchestrate neural features + symbolic rules.

v1.3: Bổ sung content alignment check (Neural layer) để kiểm tra semantic
alignment giữa đoạn văn được trích dẫn và paper nguồn.

Đây là component chính thể hiện tính "Neuro-Symbolic":
    - Neural: Sentence-BERT embeddings cho content-context alignment
    - Symbolic: Bộ quy tắc regex, logic validation cho decision making
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from integrity_checker.config import get_settings
from integrity_checker.extraction.patterns.apa import is_vn_legal_reference
from integrity_checker.logging import get_logger
from integrity_checker.models.citation import Citation
from integrity_checker.models.source import SourceCandidate, SourceResult
from integrity_checker.models.validation import CitationVerdict, MatchFeatures, ValidationLabel
from integrity_checker.matching.features import FeatureCalculator
from integrity_checker.logic.rules import SymbolicRules, _is_fake_url
from integrity_checker.retrieval.retrieval_orchestrator import RetrievalOrchestrator

if TYPE_CHECKING:
    from integrity_checker.linking.statuses import CitationMappingStatus, StyleProfile

logger = get_logger(__name__)


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

    def __init__(
        self,
        feature_calculator: FeatureCalculator | None = None,
        rules: SymbolicRules | None = None,
        enable_content_alignment: bool = True,
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
        # Ví dụ: "Google, 'YouTube Data API v3,' Google for Developers."
        # Hoặc: "Google YouTube Data API v3" (GROBID short form)
        # Nhận diện: organization name + product/service name + developer/API keyword
        web_resource_patterns = [
            # Company, "Product/Service Name," Company
            re.compile(
                r'^(Google|Microsoft|Amazon|Apple|Facebook|Meta|Twitter|GitHub|IBM|Intel|'
                r'Nvidia|Adobe|Atlassian|Oracle|Salesforce|'
                r'OpenAI|Anthropic|Hugging\s*Face|Replicate|Cohere),?\s*["“]',
                re.IGNORECASE
            ),
            # "Product/Service Name," Organization (title-first pattern)
            re.compile(
                r'^["“](YouTube\s*Data\s*API|Google\s*API|AWS\s*SDK|'
                r'Rest\s*API|GraphQL|Webhook|Twilio|Stripe|OpenAI|Anthropic)\b',
                re.IGNORECASE
            ),
            # Developer/Documentation keyword sau citation
            re.compile(
                r'(Google\s+for\s+Developers|Developer\s+Documentation|'
                r'API\s+Reference|API\s+Documentation|REST\s+API\s+Documentation|'
                r'Academic\s+Graph\s+API|Getting\s+Started|REST\s+API|'
                r'The\s+DOI\s+Handbook)\s*[.,]',
                re.IGNORECASE
            ),
            # Web portal / online documentation / archive with explicit URL and no DOI
            re.compile(
                r'\b(ACL\s+Anthology|Crossref\s+REST\s+API|Semantic\s+Scholar\s+(?:Academic\s+Graph\s+API|Open\s+Research\s+Corpus)|'
                r'OpenAlex\s*:\s*An\s+open\s+catalogue|Handbook\s+of\s+the\s+DOI\s+Resolution\s+System|'
                r'The\s+DOI\s+Handbook)\b.*?\bRetrieved\s+from\s+https?://',
                re.IGNORECASE
            ),
            # Company name + API/SDK/Tool keyword (short form từ GROBID)
            # Ví dụ: "Google YouTube Data API v3", "Google Maps API", "AWS SDK"
            re.compile(
                r'^(Google|Amazon|Microsoft|GitHub|IBM|Intel|Nvidia)\s+'
                r'(YouTube|Maps|AWS|Vertex|TensorFlow|BERT|Cloud|Compute|S3|'
                r'Data\s*API|API|SDK|Tool)\b',
                re.IGNORECASE
            ),
            # Common API/SDK patterns: "X API v3" hoặc "X Data API"
            re.compile(
                r'^(Google\s+YouTube\s+Data\s*API|YouTube\s+Data\s*API|'
                r'Google\s+API|Vertex\s+AI|Google\s+Cloud)',
                re.IGNORECASE
            ),
            # Product/API documentation anywhere in citation (e.g., "Google. (2024). YouTube Data API v3. Google for Developers.")
            re.compile(
                r'\b(YouTube\s+Data\s*API\s+v\d+|Google\s+for\s+Developers)\b',
                re.IGNORECASE
            ),
            # Computer software / GitHub repository without academic venue
            re.compile(
                r'(\[Computer\s+software\]|\bGitHub\.\s*Retrieved\b)',
                re.IGNORECASE
            ),
        ]
        for pattern in web_resource_patterns:
            if pattern.search(raw_text):
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
            # Create a synthetic SourceCandidate from known paper info
            known_candidate = SourceCandidate(
                source_name="known_papers",
                found=True,
                title=paper_info.get("title"),
                doi=paper_info.get("doi"),
                authors=paper_info.get("authors", []),
                year=known_year,
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

                    return self._apply_dead_link_exception(
                        CitationVerdict(
                            citation=citation,
                            label=ValidationLabel.VERIFIED,
                            confidence=0.90,
                            matched_source=enhanced_source,
                            features=features,
                            reasoning=f"Known seminal paper verified via known papers database: '{paper_info.get('title')}'. APIs failed but paper is well-documented.",
                            triggered_rules=["R-KNOWN-PAPER"],
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

                return self._apply_dead_link_exception(
                    CitationVerdict(
                        citation=citation,
                        label=ValidationLabel.VERIFIED,
                        confidence=0.90,
                        matched_source=enhanced_source,
                        features=features,
                        reasoning=f"Known seminal paper verified via known papers database: '{paper_info.get('title')}'. APIs failed but paper is well-documented.",
                        triggered_rules=["R-KNOWN-PAPER"],
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

        # Enhance reasoning với content alignment info (Neural layer feedback)
        enhanced_reasoning = self._enhance_reasoning_with_neural(
            outcome.reasoning, features, outcome.triggered_rules
        )

        return self._apply_dead_link_exception(
            CitationVerdict(
                citation=citation,
                label=outcome.label,
                confidence=outcome.confidence,
                matched_source=source,
                features=features,
                reasoning=enhanced_reasoning,
                triggered_rules=list(outcome.triggered_rules),
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
        """Enhance symbolic reasoning với Neural content alignment info.

        Thêm thông tin về content alignment vào reasoning để giảng viên
        hiểu được tại sao Neural layer đưa ra kết luận.
        """
        if not self.enable_content_alignment:
            return symbolic_reasoning

        # Nếu có content alignment info, thêm vào reasoning
        if features.content_alignment_score > 0:
            alignment_info = (
                f" [Neural: content alignment score={features.content_alignment_score:.2f} "
                f"({features.content_alignment_confidence})"
            )

            # Thêm signal nếu content alignment khác với symbolic decision
            if features.content_is_aligned and "VERIFIED" not in triggered_rules:
                alignment_info += " - content semantically aligned with source"
            elif not features.content_is_aligned and features.content_alignment_score > 0.3:
                alignment_info += " - WARNING: content may not align with source"

            alignment_info += "]"
            return symbolic_reasoning + alignment_info

        return symbolic_reasoning
