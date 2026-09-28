"""Base dataclasses and Protocol for modular citation pattern system.

This module defines the core abstractions for citation format handling:
- PatternType: Classification of patterns by usage
- CompiledPattern: Immutable pattern with compiled regex
- CitationFormat Protocol: Interface for format-specific implementations

Each citation format (APA, MLA, IEEE, etc.) implements CitationFormat
to provide its own patterns and parsing logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from integrity_checker.models.citation import Citation


class PatternType(str, Enum):
    """Classification of patterns by their usage context.

    IN_TEXT: Patterns for in-text citations (Author, 2020), [1]
    REFERENCE_ENTRY: Patterns for reference list entries
    UTILITY: Patterns for extracting metadata (DOI, URL, year)
    """

    IN_TEXT = "in_text"
    REFERENCE_ENTRY = "reference_entry"
    UTILITY = "utility"


@dataclass(frozen=True)
class CompiledPattern:
    """Immutable compiled pattern with metadata.

    Attributes:
        name: Unique identifier for this pattern
        pattern: Original regex pattern string
        pattern_type: Classification of how this pattern is used
        compiled_regex: Pre-compiled re.Pattern object
        description: Human-readable description for documentation
    """

    name: str
    pattern: str
    pattern_type: PatternType
    compiled_regex: re.Pattern[str]
    description: str

    def __post_init__(self) -> None:
        """Validate that pattern is properly compiled."""
        if not isinstance(self.compiled_regex, re.Pattern):
            raise TypeError(
                f"compiled_regex must be a compiled regex pattern, "
                f"got {type(self.compiled_regex).__name__}"
            )

    @classmethod
    def create(
        cls,
        name: str,
        pattern: str,
        pattern_type: PatternType,
        description: str,
    ) -> CompiledPattern:
        """Factory method to create a CompiledPattern with auto-compiled regex.

        Args:
            name: Unique identifier for this pattern
            pattern: Regex pattern string
            pattern_type: Classification of pattern usage
            description: Human-readable description

        Returns:
            CompiledPattern with compiled regex
        """
        return cls(
            name=name,
            pattern=pattern,
            pattern_type=pattern_type,
            compiled_regex=re.compile(pattern),
            description=description,
        )

    def finditer(self, text: str) -> list[re.Match[str]]:
        """Find all matches of this pattern in text.

        Args:
            text: Text to search

        Returns:
            List of match objects
        """
        return list(self.compiled_regex.finditer(text))

    def search(self, text: str) -> re.Match[str] | None:
        """Search for first match of this pattern in text.

        Args:
            text: Text to search

        Returns:
            First match or None if not found
        """
        return self.compiled_regex.search(text)

    def match(self, text: str) -> re.Match[str] | None:
        """Check if pattern matches at start of text.

        Args:
            text: Text to match

        Returns:
            Match object or None if no match at start
        """
        return self.compiled_regex.match(text)


@runtime_checkable
class CitationFormat(Protocol):
    """Protocol for citation format implementations.

    Each citation format (APA, MLA, IEEE, etc.) must implement:
    - name: Format identifier
    - priority: Lower = higher priority (tried first)
    - in_text_patterns: Patterns for in-text citations
    - reference_patterns: Patterns for reference list entries
    - parse_reference_entry(text: str) -> Citation | None
    - is_valid_citation(text: str) -> bool

    Example implementation for APA:
        class APAFormat:
            name = "APA"
            priority = 10

            in_text_patterns: list[CompiledPattern] = [...]
            reference_patterns: list[CompiledPattern] = [...]

            def parse_reference_entry(self, text: str) -> Citation | None:
                ...

            def is_valid_citation(self, text: str) -> bool:
                ...
    """

    @property
    def name(self) -> str:
        """Format name (e.g., 'APA', 'IEEE', 'MLA')."""
        ...

    @property
    def priority(self) -> int:
        """Priority for format resolution. Lower = higher priority."""
        ...

    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting in-text citations."""
        ...

    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Patterns for extracting reference list entries."""
        ...

    def parse_reference_entry(self, text: str) -> Citation | None:
        """Parse a reference list entry into a Citation object.

        Args:
            text: Raw reference entry text

        Returns:
            Citation object if successfully parsed, None otherwise
        """
        ...

    def is_valid_citation(self, text: str) -> bool:
        """Check if text matches a valid citation for this format.

        Args:
            text: Text to validate

        Returns:
            True if text is a valid citation, False otherwise
        """
        ...
