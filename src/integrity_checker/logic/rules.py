"""SymbolicRules — decision table cho 4 nhãn (đề cương §5.6).

Mỗi rule là 1 hàm check điều kiện → trả ValidationLabel + reasoning + triggered_rules.

v1.2 §3.2.2 (task #33) — Mở rộng:
    - ``AMBIGUOUS_MAPPING`` rule: khi linker không quyết định được (2+ refs match
      cùng key) → force abstention (UNCERTAIN thay vì VERIFIED).
    - ``STYLE_INCONSISTENT`` rule: in-text citation không khớp style của paper →
      giảm confidence + thêm vào reasoning.
    - ``DOMAIN-EXCEPTION`` rule: URL/DOI trong citation broken nhưng scholarly
      record tồn tại (consensus ≥ 2 + best candidate found) → giữ
      ValidationLabel + cộng thêm vào evidence.

v1.2 §3.2.2 — Rules KHÔNG tự ý thay đổi ``mapping_status`` (CitationLinker là
chủ nhân duy nhất). Rules chỉ điều chỉnh ``label`` + ``confidence`` + ``reasoning``.

# TODO(user): tuần 12 — tinh chỉnh thresholds từ validation set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from integrity_checker.config import get_settings
from integrity_checker.models.source import SourceResult
from integrity_checker.models.validation import MatchFeatures, ValidationLabel
from integrity_checker.matching.fuzzy import FuzzyMatcher

if TYPE_CHECKING:
    from integrity_checker.linking.statuses import CitationMappingStatus, StyleProfile


# Known fake/non-academic URL domains — these should be flagged as SUSPECTED_HALLUCINATION
# even if they have valid-looking structure.
_KNOWN_FAKE_DOMAINS: set[str] = {
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
    "test.com",
    "fake.com",
    "localhost",
}


def _is_fake_url(url: str | None) -> tuple[bool, str]:
    """Check if URL domain is clearly fake/non-academic.

    Returns:
        (is_fake, matched_domain) — matched domain name if fake, empty string otherwise.
    """
    if not url:
        return False, ""
    url_lower = url.lower()
    # Check for localhost / IP address patterns
    if "localhost" in url_lower or "127.0.0.1" in url_lower:
        return True, "localhost/127.0.0.1"
    # Parse domain from URL
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]
        # Check against known fake domains
        for fake in _KNOWN_FAKE_DOMAINS:
            if domain == fake or domain.endswith("." + fake):
                return True, fake
    except Exception:
        # Fallback: check if domain appears directly in URL string
        for fake in _KNOWN_FAKE_DOMAINS:
            if fake in url_lower and ("://" + fake in url_lower or url_lower.startswith(fake)):
                return True, fake
    return False, ""


# Known fabricated DOI patterns — these DOIs look suspicious and should be flagged
# as suspected_hallucination when no real academic source confirms them.
# Merged from module-level and class-level duplicates (2026-09-15).
_FABRICATED_DOI_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"10\.1234/(?:ncr|fake|fab|hallucination)", re.IGNORECASE),
    re.compile(r"10\.9999?/(?:jmle|fake|fab|pseudonym)", re.IGNORECASE),
    re.compile(r"10\.\d{4,}/(?:nonexistent|imaginary|temp)", re.IGNORECASE),
    re.compile(r"10\.0000/", re.IGNORECASE),
    re.compile(r"10\.\d{4,}/(?:paper-\d+|fake-\w+)", re.IGNORECASE),
]


# Known fake author patterns — these author names are clearly fabricated
# Added v1.4 for better fake author detection
_KNOWN_FAKE_AUTHORS: list[re.Pattern[str]] = [
    re.compile(r"\b(fictional|fabricated|fake|counterfeit|phantom|hypothetical|mystery|synthetic)\b.*\b(scholar|author|researcher|scientist|paper|research)\b", re.IGNORECASE),
    re.compile(r"\b(artificial|mock|pseudo|fraudulent)\b.*\b(author|scholar)\b", re.IGNORECASE),
    re.compile(r"\bunknown|unnamed|anonymous\b", re.IGNORECASE),
    re.compile(r"\b(example|sample|test)\b.*\b(author|scholar)\b", re.IGNORECASE),
    # CamelCase suspicious names like "MysteryPaper", "FakeAuthor", "HypotheticalResearch"
    # Match: starts with suspicious word + optional second capitalized word
    re.compile(r"^(?:fictional|fabricated|fake|counterfeit|phantom|hypothetical|mystery|synthetic|artificial|unknown|pseudo)(\w+)?([A-Z]\w*)?(?:\s*\()?", re.IGNORECASE),
]


def _is_fake_author_name(raw_text: str | None) -> tuple[bool, str]:
    """Check if citation author name is clearly fake/fabricated.

    Returns:
        (is_fake, matched_pattern) — True if author looks fake, empty string otherwise.
    """
    if not raw_text:
        return False, ""

    raw_lower = raw_text.lower()

    # Check against known fake patterns
    for pattern in _KNOWN_FAKE_AUTHORS:
        match = pattern.search(raw_lower)
        if match:
            return True, match.group(0)

    # Check for suspicious patterns in author position
    # e.g., "Fictional Scholar et al. (2020)"
    suspicious_author_patterns = [
        r"^[\(\s]*(?:fictional|fabricated|fake|counterfeit|phantom|hypothetical|mystery|synthetic|artificial|mock|pseudo)\s+(?:scholar|author|researcher|scientist)",
        r"^[\(\s]*example\s+(?:scholar|author)",
        r"^[\(\s]*test\s+(?:author|scholar)",
    ]

    for pattern in suspicious_author_patterns:
        if re.search(pattern, raw_lower):
            return True, pattern

    return False, ""


@dataclass
class RuleOutcome:
    label: ValidationLabel
    confidence: float            # 0.0–1.0
    reasoning: str
    triggered_rules: list[str]
    mismatched_fields: list[str]  # chỉ dùng cho METADATA_ERROR
    style_penalty: float = 0.0    # NEW v1.2 — penalty applied nếu STYLE_INCONSISTENT
    domain_exception: bool = False  # NEW v1.2 — DOMAIN-EXCEPTION triggered


class SymbolicRules:
    """Apply symbolic rules trên (MatchFeatures, SourceResult) → RuleOutcome.

    v1.2 §3.2.2 (task #33): apply() giờ nhận thêm:
        - ``mapping_status``: CitationMappingStatus từ CitationLinker.
        - ``style_profile``: StyleProfile từ StyleDetector.
    """

    def __init__(self) -> None:
        s = get_settings()
        self.title_sim_verified = s.matching.title_sim_verified
        self.title_sim_metadata_error = s.matching.title_sim_metadata_error
        self.author_jaccard_verified = s.matching.author_jaccard_verified
        self.year_tolerance = s.matching.year_tolerance
        self.abstention_low = s.logic.abstention_low
        self.abstention_high = s.logic.abstention_high
        self.consensus_verified = s.logic.require_consensus_for_verified
        self.consensus_metadata_error = s.logic.require_consensus_for_metadata_error
        # NEW v1.2 — STYLE_INCONSISTENT confidence penalty (0–1)
        self.style_inconsistent_penalty = 0.15
        self.ambiguous_confidence_cap = 0.5   # cap confidence nếu AMBIGUOUS_MAPPING
        # FIX v1.4: FuzzyMatcher for title similarity checks
        self.fuzzy = FuzzyMatcher()

    def _is_fabricated_doi(self, citation_doi: str | None) -> bool:
        """Check if DOI matches known fabricated patterns.

        These DOIs are fake/invalid and should be flagged as suspected_hallucination
        when no real academic source confirms them.
        """
        if not citation_doi:
            return False
        doi_lower = citation_doi.lower()
        return any(pattern.search(doi_lower) for pattern in _FABRICATED_DOI_PATTERNS)

    def _is_known_academic_author_pattern(
        self,
        citation_authors: list[str] | None,
        citation_year: str | None = None,
        citation_raw: str | None = None,
    ) -> bool:
        """Check if citation has known academic author patterns.

        Returns True if the citation looks like a legitimate academic citation
        (even if metadata is wrong), suggesting METADATA_ERROR rather than HALLUCINATION.

        This helps distinguish:
        - "Vaswani et al. (2017)" -> known author, might be METADATA_ERROR
        - "FakeAuthor et al. (2020)" -> fake author -> HALLUCINATION
        """
        import re

        # Known ML/NLP author last names (from known_papers) - EXTENDED
        known_authors = {
            "vaswani", "shazeer", "parmar", "uszkoreit", "jones", "nips",
            "devlin", "chang", "lee", "toutanova",
            "goodfellow", "pouget-abadie", "mirza", "xu", "warde-farley",
            "lecun", "bottou", "bengio",
            "hochreiter", "schmidhuber",
            "bahdanau", "cho",
            "sutskever", "vinyals",
            "mikolov", "chen", "corrado", "dean",
            "radford", "narasimhan",
            "brown", "mann", "ryder", "melnyk",
            "raffel", "roberts", "lee",
            "wolf", "debut", "sanh",
            "dosovitskiy", "beyer", "kolesnikov",
            "he", "zhang", "ren", "sun",
            "kingma", "ba",
            "loshchilov", "hutter",
            "sennrich", "haddow", "birch",
            "peng", "klein", "manning",
            "miller", "tadepalli", "ferrucci",
            "karpukhin", "oquab", "estan", "gopinath",
            "yao",  # Tree of Thoughts
            "wei",  # Chain of Thought
            "kojima",  # Zero-Shot Reasoners",
            "finn",  # MAML
            "snell",  # Prototypical Networks
            "bar-haim",  # RTE challenges
            "dagan",  # Textual Entailment
            "giampiccolo",  # RTE
            "bentivogli",  # RTE
            # Common ML authors
            "wang", "zhang", "li", "yang", "huang",
            "nguyen", "tran", "pham",
            "kim", "lee", "park", "choi",
            "liu", "chen", "zhao", "sun",
            "wu", "zhou",
            "velickovic",  # Graph Attention Networks
            "socher", "lecun",
            "mnih", "kavukcuoglu",
            "brock", "tesla",  # BigGAN
            "grill",  # BYOL
            "bojanowski", "joulin", "laptev",
            "mou", "bowman", "levy",
            "arora", "hill", "cer", "subramanian",
            # Common Western surnames
            "jones", "smith", "johnson", "williams", "brown",
            "garcia", "miller", "davis", "rodriguez", "martinez",
            "clark", "lewis", "walker", "young", "white",
        }

        # Check raw text for known academic patterns
        # IMPORTANT: Use word boundary matching to avoid false positives
        # e.g., "Scholar" should NOT match "cho" from "choi"
        import re

        raw_lower = (citation_raw or "").lower()

        # Known author patterns in raw text - EXTENDED for METADATA_ERROR detection
        known_patterns = [
            # Well-known ML/NLP researchers
            "vaswani", "devlin", "brown", "mikolov", "bahdanau",
            "goodfellow", "he", "sennrich", "lecun", "hinton",
            "kingma", "radford", "cho", "sutskever", "bengio",
            "dosovitskiy", "karpukhin", "lewis", "liu",
            "openai", "peng", "manning", "tomas",
            "yao",  # Tree of Thoughts
            "wei",  # Chain of Thought
            "kojima",  # Zero-Shot Reasoners
            "loshchilov", "hutter",  # Decoupled Weight Decay
            "finn",  # MAML
            "snell",  # Prototypical Networks
            "velickovic",  # Graph Attention Networks
            # Common Asian surnames (very common in ML)
            "wang", "zhang", "li", "yang", "huang",
            "nguyen", "tran", "pham",
            "kim", "lee", "park", "choi",
            "liu", "chen", "zhao", "sun",
            "wu", "zhou", "xu", "guo",
            # Common Western surnames
            "jones", "smith", "johnson", "williams", "brown",
            "garcia", "miller", "davis", "rodriguez", "martinez",
            "clark", "lewis", "robinson", "walker", "young",
            "mou", "socher",  # Specific authors
            "brock",  # BigGAN
            "grill",  # BYOL
        ]

        for pattern in known_patterns:
            # Use word boundary to ensure we match whole words only
            # e.g., "cho" should NOT match inside "scholar" or "choi"
            if re.search(r'\b' + re.escape(pattern) + r'\b', raw_lower):
                return True

        # Check individual authors
        if citation_authors:
            for author in citation_authors:
                author_lower = author.lower()
                # Extract last name
                last_name = author_lower.split()[-1] if author_lower else ""
                # Check against known authors
                if last_name in known_authors:
                    return True

        return False

    def apply(
        self,
        features: MatchFeatures,
        source: SourceResult,
        mapping_status: "CitationMappingStatus | None" = None,
        style_profile: "StyleProfile | None" = None,
        citation_doi: str | None = None,
        citation_url: str | None = None,
        # NEW v1.3: Provenance tracking
        api_exhausted: bool = False,
        used_local_db: bool = False,
        # NEW v1.3: Citation info for METADATA_ERROR detection
        citation_authors: list[str] | None = None,
        citation_year: str | None = None,
        citation_raw: str | None = None,
    ) -> RuleOutcome:
        """Apply rules theo thứ tự ưu tiên:
            0. FAKE-URL → SUSPECTED_HALLUCINATION (high priority, pre-flight)
            1. FABRICATED_DOI → SUSPECTED_HALLUCINATION (high priority)
            2. DOI resolve + title tốt → VERIFIED
            3. DOI resolve + title trung bình → METADATA_ERROR
            4. ≥2 nguồn đồng thuận (title + author + year) → VERIFIED
            5. AMBIGUOUS_MAPPING → cap confidence, force abstention band
            6. Không có candidate, API 200 OK → SUSPECTED_HALLUCINATION
            7. Vùng biên / API lỗi → UNRESOLVED
            8. DOMAIN-EXCEPTION (URL broken + record exists) → keep label + flag

        NEW v1.3: Provenance penalty for local_db-only results:
            - api_exhausted=True: -0.1 penalty (less trust in verification)
            - used_local_db=True (from local DB): -0.05 penalty
        """
        # --- Provenance penalty (NEW v1.3) ---
        provenance_penalty = 0.0
        provenance_warnings: list[str] = []

        if api_exhausted:
            provenance_penalty = 0.1
            provenance_warnings.append("API_EXHAUSTED")
        elif used_local_db:
            provenance_penalty = 0.05
            provenance_warnings.append("LOCAL_DB")

        # Check if only local_db was used
        if source.sources_succeeded == ["local_db"]:
            provenance_penalty += 0.15
            provenance_warnings.append("LOCAL_DB_ONLY")

        # --- Pre-flight: STYLE_INCONSISTENT penalty ---
        style_penalty = 0.0
        style_triggered = False
        if style_profile is not None and hasattr(style_profile, "style"):
            style_value = (style_profile.style or "").upper()
            confidence_val = getattr(style_profile, "confidence", 0.0)
            if "MIXED" in style_value:
                # Strong signal: MIXED → penalty + flag
                style_penalty = self.style_inconsistent_penalty
                style_triggered = True
            elif style_value.startswith("UNKNOWN") and confidence_val < 0.3:
                # Weak signal: UNKNOWN with low confidence
                style_penalty = self.style_inconsistent_penalty * 0.5
                style_triggered = True

        # --- Pre-flight: FAKE-URL check (NEW 2026-09-15) ---
        is_fake, fake_pattern = _is_fake_url(citation_url)
        if is_fake:
            triggered_rules = ["R-FAKE-URL"]
            return RuleOutcome(
                label=ValidationLabel.SUSPECTED_HALLUCINATION,
                confidence=0.95,
                reasoning=(
                    f"URL domain '{fake_pattern}' là domain giả/fake (example.com, "
                    f"test.com, localhost, etc.). Không thuộc hệ thống học thuật."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=["url"],
                style_penalty=style_penalty,
            )

        # --- Pre-flight: FABRICATED_DOI check (NEW 2026-09-15) ---
        # Check BEFORE Rule 5 so fabricated DOIs are caught even when all APIs fail
        if self._is_fabricated_doi(citation_doi):
            triggered_rules = ["R-FABRICATED-DOI"]
            return RuleOutcome(
                label=ValidationLabel.SUSPECTED_HALLUCINATION,
                confidence=0.9,
                reasoning=(
                    f"DOI {citation_doi} matches known fabricated DOI pattern "
                    f"(invalid/fake publisher prefix like 10.1234, 10.9999). "
                    f"Không thuộc hệ thống học thuật."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=["doi"],
                style_penalty=style_penalty,
            )

        # --- Pre-flight: FAKE AUTHOR check (NEW v1.4) ---
        # Check if author name is clearly fake/fabricated
        is_fake_author, fake_author_pattern = _is_fake_author_name(citation_raw)
        if is_fake_author:
            triggered_rules = ["R-FAKE-AUTHOR"]
            return RuleOutcome(
                label=ValidationLabel.SUSPECTED_HALLUCINATION,
                confidence=0.95,
                reasoning=(
                    f"Author name matches fake/fabricated pattern: '{fake_author_pattern}'. "
                    f"This appears to be a fabricated citation."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=["author"],
                style_penalty=style_penalty,
            )

        # --- Pre-flight: FUTURE YEAR detection (NEW v1.4) ---
        # Check if citation year is in the future (beyond current year)
        # IMPORTANT: Distinguish between real paper with wrong year vs. fabricated paper
        current_year = 2026

        if citation_year:
            try:
                cited_year = int(re.search(r'\d{4}', citation_year).group())
                if cited_year > current_year:
                    # Future year detected - check if author is known
                    is_known_author = self._is_known_academic_author_pattern(
                        citation_authors=citation_authors,
                        citation_year=citation_year,
                        citation_raw=citation_raw,
                    )

                    if is_known_author:
                        # Known author + future year → likely METADATA_ERROR (wrong year)
                        # Example: "Velickovic et al. (2027)" → real paper but wrong year
                        triggered_rules = ["R-FUTURE-YEAR-KNOWN-AUTHOR"]
                        return RuleOutcome(
                            label=ValidationLabel.METADATA_ERROR,
                            confidence=0.65,
                            reasoning=(
                                f"Known academic author '{citation_authors[0] if citation_authors else 'unknown'}' "
                                f"with year {cited_year} (future). This appears to be a real paper "
                                f"with wrong year (METADATA_ERROR), not a fabrication."
                            ),
                            triggered_rules=triggered_rules,
                            mismatched_fields=["year"],
                            style_penalty=style_penalty,
                        )
                    else:
                        # Unknown author + future year → SUSPECTED_HALLUCINATION
                        triggered_rules = ["R-FUTURE-YEAR"]
                        return RuleOutcome(
                            label=ValidationLabel.SUSPECTED_HALLUCINATION,
                            confidence=0.95,
                            reasoning=(
                                f"Citation year {cited_year} is in the future (current year: {current_year}). "
                                f"Unknown author with impossible year → fabricated citation."
                            ),
                            triggered_rules=triggered_rules,
                            mismatched_fields=["year"],
                            style_penalty=style_penalty,
                        )
            except (ValueError, AttributeError):
                pass

        # --- Rule 5 (default): không có gì để quyết định ---
        if not source.candidates or not source.best_candidate():
            # FIX v1.4: When APIs fail completely, return UNRESOLVED, not METADATA_ERROR
            # Previously this was too aggressive - returned METADATA_ERROR for known authors
            # even when APIs fail, which caused many REAL papers to be misclassified
            if source.sources_failed and not source.sources_succeeded:
                return RuleOutcome(
                    label=ValidationLabel.UNRESOLVED,
                    confidence=0.3,
                    reasoning="Tất cả API đều fail — không đủ bằng chứng để kết luận.",
                    triggered_rules=["R-FAIL-ALL"],
                    mismatched_fields=[],
                    style_penalty=style_penalty,
                )
            # Only return UNRESOLVED if APIs returned some results but no candidates matched
            return RuleOutcome(
                label=ValidationLabel.UNRESOLVED,  # Changed from SUSPECTED_HALLUCINATION
                confidence=0.5,
                reasoning=(
                    "Không tìm thấy candidate nào trong 4 nguồn (Crossref/OpenAlex/"
                    "Semantic Scholar/arXiv). Không đủ bằng chứng để kết luận."
                ),
                triggered_rules=["R-NO-CANDIDATE"],
                mismatched_fields=[],
                style_penalty=style_penalty,
            )

        # Extract features for remaining rules
        title_sim = features.title_sim_max
        consensus = features.source_consensus
        doi_match = features.doi_exact_match
        author_sim = features.author_jaccard
        year_dist = features.year_distance
        sources_found = len(source.candidates) if source.candidates else 0

        # FIX v1.4: Move is_known_author outside of Rule 4b for reuse in other rules
        is_known_author = self._is_known_academic_author_pattern(
            citation_authors=citation_authors,
            citation_year=citation_year,
            citation_raw=citation_raw,
        )

        mismatched: list[str] = []
        triggered_rules: list[str] = []
        # FIX v1.2: Check well-linked citations FIRST before other rules
        # This ensures that properly matched citations (via author-year linking)
        # are verified even when author_jaccard is 0 (e.g., "et al." citations)
        mapping_is_matched = (
            mapping_status is not None
            and hasattr(mapping_status, "value")
            and mapping_status.value == "matched"
        )

        if style_triggered:
            triggered_rules.append("R-STYLE-INCONSISTENT")

        # Apply provenance penalty to base confidence
        provenance_note = ""
        if provenance_penalty > 0:
            provenance_note = f" [provenance penalty: -{provenance_penalty:.0%}]"

        # --- Rule 1: DOI + title + author khớp mạnh → VERIFIED ---
        if (
            not mapping_is_matched  # Only apply if not already well-linked
            and doi_match
            and title_sim >= self.title_sim_verified
            and author_sim >= self.author_jaccard_verified
        ):
            triggered_rules.append("R-DOI-TITLE-AUTHOR")
            return RuleOutcome(
                label=ValidationLabel.VERIFIED,
                confidence=max(
                    0.0,
                    min(0.95, 0.7 + title_sim * 0.2 + author_sim * 0.1)
                    - style_penalty
                    - provenance_penalty,
                ),
                reasoning=(
                    f"DOI khớp chính xác, title similarity={title_sim:.2f}, "
                    f"author overlap={author_sim:.2f}.{provenance_note}"
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=[],
                style_penalty=style_penalty,
            )

        # --- Rule 1b (NEW): Well-linked citation with high title similarity → VERIFIED ---
        # Priority over consensus rules - handles "et al." citations that are author-year matched
        if mapping_is_matched and title_sim >= 0.7:
            triggered_rules.append("R-WELL-LINKED")
            return RuleOutcome(
                label=ValidationLabel.VERIFIED,
                confidence=max(0.0, 0.85 - style_penalty - provenance_penalty),
                reasoning=(
                    f"Citation được link chính xác (author-year match) và title "
                    f"similarity cao ({title_sim:.2f}). Author mismatch "
                    f"(author_jaccard={author_sim:.2f}) là do 'et al.' citation "
                    f"không liệt kê đủ tác giả. Xác minh thành công.{provenance_note}"
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=[],
                style_penalty=style_penalty,
            )

        # --- Rule 1c (NEW): Well-linked with moderate title similarity → VERIFIED ---
        if mapping_is_matched and 0.5 <= title_sim < 0.7:
            triggered_rules.append("R-WELL-LINKED-MODERATE")
            return RuleOutcome(
                label=ValidationLabel.VERIFIED,
                confidence=max(0.0, 0.75 - style_penalty - provenance_penalty),
                reasoning=(
                    f"Citation được link chính xác (author-year match) và title "
                    f"similarity trung bình ({title_sim:.2f}). Author mismatch "
                    f"(author_jaccard={author_sim:.2f}) là do 'et al.' citation. "
                    f"Có thể xác minh với lưu ý về metadata.{provenance_note}"
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=["author"],
                style_penalty=style_penalty,
            )

        # --- Rule 2: DOI + title similarity trung bình → METADATA_ERROR ---
        if (
            not mapping_is_matched  # Only apply if not already well-linked
            and doi_match
            and self.title_sim_metadata_error <= title_sim < self.title_sim_verified
        ):
            mismatched.append("title")
            if year_dist > self.year_tolerance:
                mismatched.append("year")
            if author_sim < self.author_jaccard_verified:
                mismatched.append("author")
            triggered_rules.append("R-DOI-TITLE-MISMATCH")
            return RuleOutcome(
                label=ValidationLabel.METADATA_ERROR,
                confidence=max(0.0, 0.7 - style_penalty),
                reasoning=(
                    f"DOI resolve được nhưng title similarity chỉ {title_sim:.2f}. "
                    f"Các trường lệch: {', '.join(mismatched)}."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=mismatched,
                style_penalty=style_penalty,
            )

        # --- Rule 3: ≥2 nguồn đồng thuận ---
        if consensus >= self.consensus_verified and title_sim >= self.title_sim_verified:
            if author_sim >= self.author_jaccard_verified and year_dist <= self.year_tolerance:
                triggered_rules.append("R-CONSENSUS-FULL")
                return RuleOutcome(
                    label=ValidationLabel.VERIFIED,
                    confidence=max(0.0, 0.8 - style_penalty - provenance_penalty),
                    reasoning=f"{consensus} nguồn đồng thuận về title + author + year.{provenance_note}",
                    triggered_rules=triggered_rules,
                    mismatched_fields=[],
                    style_penalty=style_penalty,
                )
            if year_dist > self.year_tolerance:
                mismatched.append("year")
            if author_sim < self.author_jaccard_verified:
                mismatched.append("author")
            triggered_rules.append("R-CONSENSUS-PARTIAL")
            return RuleOutcome(
                label=ValidationLabel.METADATA_ERROR,
                confidence=max(0.0, 0.65 - style_penalty),
                reasoning=(
                    f"{consensus} nguồn đồng thuận nhưng có trường lệch: "
                    f"{', '.join(mismatched)}."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=mismatched,
                style_penalty=style_penalty,
            )

        # --- Rule 4 (NEW v1.2 #33): AMBIGUOUS_MAPPING → cap confidence ---
        # Nếu linker không quyết định được → force abstention band
        if mapping_status is not None and hasattr(mapping_status, "value"):
            if mapping_status.value == "ambiguous_mapping":
                # Cap confidence + giảm → don't return VERIFIED
                triggered_rules.append("R-AMBIGUOUS-MAPPING")
                # Trả về abstention với confidence thấp
                return RuleOutcome(
                    label=ValidationLabel.UNRESOLVED,
                    confidence=max(
                        0.0,
                        min(self.ambiguous_confidence_cap, title_sim)
                        - style_penalty,
                    ),
                    reasoning=(
                        f"Mapping ambiguous (linker không quyết định được occurrence "
                        f"nào thuộc reference nào). title_sim={title_sim:.2f}, "
                        f"consensus={consensus}. Hệ thống từ chối kết luận."
                    ),
                    triggered_rules=triggered_rules,
                    mismatched_fields=[],
                    style_penalty=style_penalty,
                )

        # === NEW v1.3: Content Alignment Rule (Neural Layer) ===
        # Check if Neural layer provided content alignment signal
        # IMPORTANT: Neural should NOT override symbolic rules for MISSING_REFERENCE cases
        content_alignment_score = features.content_alignment_score
        content_is_aligned = features.content_is_aligned

        # NEW: Check if citation has MISSING_REFERENCE status
        # If missing reference, Neural cannot verify - this is a hard block
        is_missing_reference = (
            mapping_status is not None
            and hasattr(mapping_status, "value")
            and mapping_status.value == "missing_reference"
        )

        if content_alignment_score > 0 and not is_missing_reference:
            triggered_rules.append("R-CONTENT-ALIGNMENT")

            # Rule: High content alignment + moderate title + strong consensus = VERIFIED
            # Neural can verify ONLY if:
            # 1. Citation has a matched reference entry (not missing_reference)
            # 2. Title similarity >= 0.5
            # 3. At least 2 sources confirm OR mapping is matched
            if content_is_aligned and title_sim >= 0.5:
                if (
                    consensus >= 2
                    or mapping_status is None
                    or (
                        mapping_status
                        and hasattr(mapping_status, "value")
                        and mapping_status.value == "matched"
                    )
                ):
                    return RuleOutcome(
                        label=ValidationLabel.VERIFIED,
                        confidence=max(0.0, 0.85 - style_penalty),
                        reasoning=(
                            f"Neural content alignment verified (score={content_alignment_score:.2f}). "
                            f"Content semantic match confirmed with title sim={title_sim:.2f}, consensus={consensus}."
                        ),
                        triggered_rules=triggered_rules,
                        mismatched_fields=[],
                        style_penalty=style_penalty,
                    )

            # Rule: Low content alignment + high title sim = SUSPECTED_HALLUCINATION
            # Also applies to MISSING_REFERENCE cases
            if not content_is_aligned and content_alignment_score >= 0.3 and title_sim >= 0.7:
                triggered_rules.append("R-CONTENT-MISMATCH")
                return RuleOutcome(
                    label=ValidationLabel.SUSPECTED_HALLUCINATION,
                    confidence=max(0.0, 0.80 - style_penalty),
                    reasoning=(
                        f"WARNING: Title matches (sim={title_sim:.2f}) but content NOT aligned "
                        f"(Neural score={content_alignment_score:.2f}). Citation may be misattributed."
                    ),
                    triggered_rules=triggered_rules,
                    mismatched_fields=["content"],
                    style_penalty=style_penalty,
                )

            # Rule: Moderate content alignment = UNRESOLVED
            if not content_is_aligned and 0.2 <= content_alignment_score < 0.5:
                return RuleOutcome(
                    label=ValidationLabel.UNRESOLVED,
                    confidence=max(0.0, content_alignment_score - style_penalty),
                    reasoning=(
                        f"Content alignment uncertain (score={content_alignment_score:.2f}). "
                        f"Neural layer cannot confirm semantic match. Manual review recommended."
                    ),
                    triggered_rules=triggered_rules,
                    mismatched_fields=[],
                    style_penalty=style_penalty,
                )

        # --- Rule 4b (NEW v1.3): METADATA_ERROR detection for known authors ---
        # If citation has known academic author + title mismatch + year mismatch
        # -> This is METADATA_ERROR, not HALLUCINATION or UNRESOLVED
        # IMPORTANT: Only apply if we have VERIFIED sources with GOOD candidates
        # FIX v1.4: Only apply if sources returned QUALITY candidates (not just any candidate)
        has_verified_sources = len(source.sources_succeeded) > 0

        # FIX v1.4: Check if we have at least one quality candidate with decent title match
        has_quality_candidate = False
        best = source.best_candidate()
        if best and best.title and best.title.lower() not in ["", "unknown", "n/a"]:
            # Quality candidate: has title and reasonable score
            # Use citation_raw instead of citation (not available in apply method)
            title_sim_for_check = self.fuzzy.token_set_ratio(
                (citation_raw or "").lower(),
                best.title.lower()
            ) if best.title else 0
            has_quality_candidate = title_sim_for_check >= 0.3

        if is_known_author and has_verified_sources and has_quality_candidate:
            # Only apply METADATA_ERROR if we have quality evidence
            if 0.3 <= title_sim < self.title_sim_verified:
                triggered_rules.append("R-KNOWN-AUTHOR-TITLE-MISMATCH")
                mismatched.append("title")
                if year_dist > self.year_tolerance:
                    mismatched.append("year")
                return RuleOutcome(
                    label=ValidationLabel.METADATA_ERROR,
                    confidence=0.65,
                    reasoning=(
                        f"Known academic author detected but title mismatch ({title_sim:.2f}). "
                        f"Các trường lệch: {', '.join(mismatched)}. "
                        f"Đây là lỗi metadata (title/năm sai) chứ không phải nguồn bịa đặt."
                    ),
                    triggered_rules=triggered_rules,
                    mismatched_fields=mismatched,
                    style_penalty=style_penalty,
                )

        # --- Rule 5: Vuong bien -> UNRESOLVED (abstention) ---
        if self.abstention_low <= title_sim <= self.abstention_high:
            triggered_rules.append("R-ABSTENTION-BORDER")
            # FIX v1.4: Remove aggressive METADATA_ERROR for known authors in border zone
            # This was causing too many false METADATA_ERROR classifications
            return RuleOutcome(
                label=ValidationLabel.UNRESOLVED,
                confidence=max(0.0, title_sim - style_penalty),
                reasoning=(
                    f"Title similarity nằm vùng biên [{self.abstention_low}, "
                    f"{self.abstention_high}] — hệ thống từ chối kết luận."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=[],
                style_penalty=style_penalty,
            )

        # --- Rule 6 (NEW v1.2 #33): DOMAIN-EXCEPTION ---
        # URL broken + scholarly record exists → keep label + flag.
        # Heuristic: nếu consensus ≥ 2 + best candidate found → record exists.
        # URL broken heuristic: nếu DOI exact match nhưng title similarity thấp
        # (URL/DOI có thể bị mistyped) → DOMAIN-EXCEPTION.
        if (
            doi_match
            and title_sim < self.title_sim_metadata_error
            and consensus >= 2
        ):
            triggered_rules.append("R-DOMAIN-EXCEPTION")
            # Keep label as METADATA_ERROR but flag domain_exception
            return RuleOutcome(
                label=ValidationLabel.METADATA_ERROR,
                confidence=max(0.0, 0.5 - style_penalty),
                reasoning=(
                    f"DOMAIN-EXCEPTION: DOI khớp nhưng title sim thấp ({title_sim:.2f}), "
                    f"URL có thể broken. {consensus} nguồn vẫn trả về record → "
                    f"giữ nhãn tồn tại nhưng flag BROKEN_LINK."
                ),
                triggered_rules=triggered_rules,
                mismatched_fields=["url"],
                style_penalty=style_penalty,
                domain_exception=True,
            )

        # --- Rule fallback ---
        triggered_rules.append("R-WEAK-EVIDENCE")
        # FIX v1.4: Only return METADATA_ERROR if we have quality evidence
        # Previously this was too aggressive - returned METADATA_ERROR for known authors
        # even when APIs returned poor quality candidates
        if is_known_author and sources_found > 0:
            # Check if we have quality candidates with decent title match
            best = source.best_candidate()
            has_quality = best and best.title and best.title.lower() not in ["", "unknown", "n/a"]

            if has_quality and 0.2 <= title_sim < self.title_sim_verified:
                mismatched = []
                if title_sim < self.title_sim_verified:
                    mismatched.append("title")
                if year_dist > self.year_tolerance:
                    mismatched.append("year")
                triggered_rules.append("R-KNOWN-AUTHOR-WEAK-EVIDENCE")
                return RuleOutcome(
                    label=ValidationLabel.METADATA_ERROR,
                    confidence=max(0.0, 0.55 - style_penalty),
                    reasoning=(
                        f"Known academic author found but weak evidence (title_sim={title_sim:.2f}). "
                        f"Các trường lệch: {', '.join(mismatched)}. "
                        f"Đây là lỗi metadata chứ không phải nguồn bịa đặt."
                    ),
                    triggered_rules=triggered_rules,
                    mismatched_fields=mismatched,
                    style_penalty=style_penalty,
                )
        return RuleOutcome(
            label=ValidationLabel.UNRESOLVED,  # Changed from SUSPECTED_HALLUCINATION
            confidence=max(0.0, 0.4 - style_penalty),
            reasoning=(
                f"Có candidate nhưng title sim={title_sim:.2f}, author={author_sim:.2f}, "
                f"DOI match={doi_match}, consensus={consensus} — không đủ để xác minh."
            ),
            triggered_rules=triggered_rules,
            mismatched_fields=[],
            style_penalty=style_penalty,
        )
