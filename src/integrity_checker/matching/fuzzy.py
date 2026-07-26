"""Fuzzy string matching với RapidFuzz."""

from __future__ import annotations

from rapidfuzz import fuzz


class FuzzyMatcher:
    """Wrapper RapidFuzz.

    # TODO(user): tuần 10 — bổ sung:
        - Normalize trước khi so sánh (lowercase, bỏ punctuation, diacritics)
        - Author last-name matching (chỉ so sánh họ)
    """

    def token_set_ratio(self, s1: str, s2: str) -> float:
        """Trả về 0.0–1.0 (đã chia 100)."""
        if not s1 or not s2:
            return 0.0
        return fuzz.token_set_ratio(s1, s2) / 100.0

    def partial_ratio(self, s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        return fuzz.partial_ratio(s1, s2) / 100.0

    def levenshtein_ratio(self, s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        return fuzz.ratio(s1, s2) / 100.0