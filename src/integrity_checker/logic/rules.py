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

    def apply(
        self,
        features: MatchFeatures,
        source: SourceResult,
        mapping_status: "CitationMappingStatus | None" = None,
        style_profile: "StyleProfile | None" = None,
        citation_doi: str | None = None,
        citation_url: str | None = None,
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
        """
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
                    - style_penalty,
                ),
                reasoning=(
                    f"DOI khớp chính xác, title similarity={title_sim:.2f}, "
                    f"author overlap={author_sim:.2f}."
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
                confidence=max(0.0, 0.85 - style_penalty),
                reasoning=(
                    f"Citation được link chính xác (author-year match) và title "
                    f"similarity cao ({title_sim:.2f}). Author mismatch "
                    f"(author_jaccard={author_sim:.2f}) là do 'et al.' citation "
                    f"không liệt kê đủ tác giả. Xác minh thành công."
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
                confidence=max(0.0, 0.75 - style_penalty),
                reasoning=(
                    f"Citation được link chính xác (author-year match) và title "
                    f"similarity trung bình ({title_sim:.2f}). Author mismatch "
                    f"(author_jaccard={author_sim:.2f}) là do 'et al.' citation. "
                    f"Có thể xác minh với lưu ý về metadata."
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
                    confidence=max(0.0, 0.8 - style_penalty),
                    reasoning=f"{consensus} nguồn đồng thuận về title + author + year.",
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

        # --- Rule 5: Vùng biên → UNRESOLVED (abstention) ---
        if self.abstention_low <= title_sim <= self.abstention_high:
            triggered_rules.append("R-ABSTENTION-BORDER")
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