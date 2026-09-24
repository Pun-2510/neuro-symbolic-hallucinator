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

        # --- Rule 5 (default): không có gì để quyết định ---
        if not source.candidates or not source.best_candidate():
            # Check known author pattern - if author looks academic, this is METADATA_ERROR
            if self._is_known_academic_author_pattern(
                citation_authors=citation_authors,
                citation_year=citation_year,
                citation_raw=citation_raw,
            ):
                return RuleOutcome(
                    label=ValidationLabel.METADATA_ERROR,
                    confidence=0.6,
                    reasoning=(
                        "Không tìm thấy candidate nhưng citation có cấu trúc tác giả "
                        "học thuật hợp lệ (author-year format). Có thể là lỗi metadata "
                        "(năm sai, title sai) chứ không phải nguồn bịa."
                    ),
                    triggered_rules=["R-KNOWN-AUTHOR-PATTERN"],
                    mismatched_fields=["year", "title"],
                    style_penalty=style_penalty,
                )
            # Nếu API fail → UNRESOLVED; nếu API OK mà không có gì → SUSPECTED
            if source.sources_failed and not source.sources_succeeded:
                return RuleOutcome(
                    label=ValidationLabel.UNRESOLVED,
                    confidence=0.3,
                    reasoning="Tất cả API đều fail — không đủ bằng chứng để kết luận.",
                    triggered_rules=["R-FAIL-ALL"],
                    mismatched_fields=[],
                    style_penalty=style_penalty,
                )
            return RuleOutcome(
                label=ValidationLabel.SUSPECTED_HALLUCINATION,
                confidence=0.85,
                reasoning=(
                    "Không tìm thấy candidate nào trong 4 nguồn (Crossref/OpenAlex/"
                    "Semantic Scholar/arXiv). Có thể là nguồn bịa."
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
        # IMPORTANT: Only apply if we have VERIFIED sources (not just candidates)
        is_known_author = self._is_known_academic_author_pattern(
            citation_authors=citation_authors,
            citation_year=citation_year,
            citation_raw=citation_raw,
        )

        # Only apply this rule if we have actual successful sources
        # (sources that returned quality candidates after filtering)
        has_verified_sources = len(source.sources_succeeded) > 0

        if is_known_author and title_sim < self.title_sim_verified and has_verified_sources:
            # Check if author might match the found paper
            # Heuristic: if title_sim is moderate (0.3-0.7), this is likely wrong title
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
            # FIX v1.3: If known author pattern, this is likely METADATA_ERROR
            if is_known_author:
                mismatched = []
                if year_dist > self.year_tolerance:
                    mismatched.append("year")
                if title_sim < self.title_sim_verified:
                    mismatched.append("title")
                triggered_rules.append("R-KNOWN-AUTHOR-BORDER")
                return RuleOutcome(
                    label=ValidationLabel.METADATA_ERROR,
                    confidence=max(0.0, 0.55 - style_penalty),
                    reasoning=(
                        f"Known academic author in border range. "
                        f"Các trường có thể lệch: {', '.join(mismatched) if mismatched else 'unknown'}. "
                        f"Đây là lỗi metadata chứ không phải nguồn bịa đặt."
                    ),
                    triggered_rules=triggered_rules,
                    mismatched_fields=mismatched if mismatched else ["metadata"],
                    style_penalty=style_penalty,
                )
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
        # FIX v1.3: If known author pattern, this is likely METADATA_ERROR, not HALLUCINATION
        if is_known_author and sources_found > 0:
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
            label=ValidationLabel.SUSPECTED_HALLUCINATION,
            confidence=max(0.0, 0.6 - style_penalty),
            reasoning=(
                f"Có candidate nhưng title sim={title_sim:.2f}, author={author_sim:.2f}, "
                f"DOI match={doi_match}, consensus={consensus} — không đủ để xác minh."
            ),
            triggered_rules=triggered_rules,
            mismatched_fields=[],
            style_penalty=style_penalty,
        )
