"""Utility patterns for citation extraction — SINGLE SOURCE OF TRUTH.

This module provides compiled regex patterns and extraction functions for:
- DOI: Digital Object Identifier
- URL: Uniform Resource Locator
- Year: Publication year (1900-2099)

All regex patterns in this module are compiled once at import time
for performance. Use these functions throughout the codebase instead
of duplicating regex patterns.
"""

from __future__ import annotations

import re
from typing import Optional

from integrity_checker.extraction.patterns.base import CompiledPattern, PatternType


# =============================================================================
# DOI Pattern
# =============================================================================
# DOI format: 10.prefix/suffix
# - Prefix: 4-9 digits (10.XXXX or 10.XXXXX)
# - Suffix: Any characters except whitespace, ], ), comma, semicolon
#
# Common DOI examples:
# - 10.1000/xyz123
# - 10.1038/nature12345
# - 10.1145/3442188.3445922

DOI_PATTERN = CompiledPattern.create(
    name="doi",
    pattern=r"10\.\d{4,9}/[^\s\]\)\,;]+",
    pattern_type=PatternType.UTILITY,
    description="DOI: Matches 10.xxxx/yyyy format (Digital Object Identifier)",
)

# Pre-compiled regex for direct use
_DOI_REGEX = re.compile(r"10\.\d{4,9}/[^\s\]\)\,;]+")


def extract_doi(text: str) -> Optional[str]:
    """Extract DOI from text.

    Args:
        text: Input text containing potential DOI

    Returns:
        DOI string if found, None otherwise

    Examples:
        >>> extract_doi("See https://doi.org/10.1000/xyz123")
        '10.1000/xyz123'
        >>> extract_doi("DOI: 10.1038/nature12345")
        '10.1038/nature12345'
        >>> extract_doi("No DOI here")
        None
    """
    if not text:
        return None
    match = _DOI_REGEX.search(text)
    if match:
        doi = match.group(0)
        # Clean trailing punctuation
        return doi.rstrip(".,;:")
    return None


# =============================================================================
# URL Pattern
# =============================================================================
# URL format: http(s)://host/path
# - Protocol: http:// or https://
# - Host: Non-whitespace characters
# - Path: Any characters except whitespace, ], ), comma, semicolon
#
# Common URL examples:
# - https://arxiv.org/abs/2103.00001
# - http://example.com/paper.pdf
# - https://github.com/user/repo

URL_PATTERN = CompiledPattern.create(
    name="url",
    pattern=r"https?://[^\s\]\)\,;]+",
    pattern_type=PatternType.UTILITY,
    description="URL: Matches http(s)://... format (Uniform Resource Locator)",
)

# Pre-compiled regex for direct use
_URL_REGEX = re.compile(r"https?://[^\s\]\)\,;]+")


def extract_url(text: str) -> Optional[str]:
    """Extract URL from text.

    Args:
        text: Input text containing potential URL

    Returns:
        URL string if found, None otherwise

    Examples:
        >>> extract_url("Visit https://example.com for more")
        'https://example.com'
        >>> extract_url("See http://arxiv.org/abs/1234.5678")
        'http://arxiv.org/abs/1234.5678'
        >>> extract_url("No URL here")
        None
    """
    if not text:
        return None
    match = _URL_REGEX.search(text)
    if match:
        url = match.group(0)
        # Clean trailing punctuation
        return url.rstrip(".,;:")
    return None


# =============================================================================
# Year Pattern
# =============================================================================
# Year format: 4-digit number starting with 19 or 20
# - 1900-1999: 19XX
# - 2000-2099: 20XX
# - Optional lowercase suffix: 2020a, 2020b for multiple papers in same year
#
# Common year examples:
# - 2020, 2019, 1985
# - 2020a (multiple papers by same author in 2020)

YEAR_PATTERN = CompiledPattern.create(
    name="year",
    pattern=r"\b(19|20)\d{2}[a-z]?\b",
    pattern_type=PatternType.UTILITY,
    description="Year: Matches 1900-2099 with optional letter suffix (e.g., 2020a)",
)

# Pre-compiled regex for direct use
_YEAR_REGEX = re.compile(r"\b(19|20)\d{2}[a-z]?\b")


def extract_year(text: str) -> Optional[str]:
    """Extract publication year from text.

    Args:
        text: Input text containing potential year

    Returns:
        Year string (e.g., "2020", "2019a") if found, None otherwise

    Examples:
        >>> extract_year("Published in 2020")
        '2020'
        >>> extract_year("Vaswani et al. (2017)")
        '2017'
        >>> extract_year("Smith (2020a) and Jones (2020b)")
        '2020'
        >>> extract_year("No year here")
        None
    """
    if not text:
        return None
    match = _YEAR_REGEX.search(text)
    return match.group(0) if match else None


# =============================================================================
# All Utility Patterns (for registry)
# =============================================================================
UTILITY_PATTERNS: list[CompiledPattern] = [
    DOI_PATTERN,
    URL_PATTERN,
    YEAR_PATTERN,
]


# =============================================================================
# Re-export for convenience
# =============================================================================
__all__ = [
    "CompiledPattern",
    "PatternType",
    "DOI_PATTERN",
    "URL_PATTERN",
    "YEAR_PATTERN",
    "UTILITY_PATTERNS",
    "extract_doi",
    "extract_url",
    "extract_year",
]
