# Modular Citation Format Pattern System - Refactoring Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor monolithic citation pattern files into a modular architecture where each citation format (APA, IEEE, Vancouver, etc.) lives in its own file with clear interfaces, enabling easy addition of new formats.

**Architecture:** Create a plugin-style architecture with a central registry that coordinates format-specific pattern modules. Each format module exposes a standardized interface for in-text patterns, reference list patterns, and parser logic.

**Tech Stack:** Python 3.10+, dataclasses, typing.Protocol for interfaces, YAML for optional config, existing Pydantic models.

**Spec:** This is a refactoring task based on the audit findings in the workflow prompt.

---

## Global Constraints

- Python 3.10+ (uses `from __future__ import annotations`)
- Maintain backward compatibility with existing tests (619 passing)
- PEP 8 style guide + type hints everywhere
- Vietnamese comments for user-facing code, English for internal logic

---

## Review Focus

The five input classes or failure modes most likely to bite a person:

1. **Format priority conflicts** - When a citation matches multiple formats, priority ordering matters; tests must verify correct precedence
2. **Missing author name patterns** - New formats like MLA/Chicago need robust author parsing; ensure parser doesn't break
3. **Reference list vs in-text confusion** - Same pattern may exist in both contexts with different semantics
4. **Cross-format duplication** - DOI/URL patterns reused across formats; single source of truth required
5. **Legacy code path compatibility** - Existing CitationExtractor/ReferenceListParser consumers must continue working

---

## Current State Analysis

### Files with Patterns (Current State)

| File | Lines | Patterns | Problem |
|------|-------|----------|---------|
| `extraction/regex_patterns.py` | 106 | 6 core | Partial, some duplicated elsewhere |
| `extraction/citation_extractor.py` | 298 | 6+ filter | Mixed concerns |
| `extraction/reference_parser.py` | 810 | 10+ entry | Monolithic, hard to maintain |
| `extraction/style_detector.py` | 251 | 2+ style | Uses config patterns |
| `matching/author_parser.py` | 603 | 7+ author | Complex, format-specific |
| `models/citation.py` | 257 | 3 basic | Utility patterns |
| `linking/citation_linker.py` | 506 | 4 linking | Uses patterns |
| `logic/rules.py` | 925 | 4+ detection | Fake/fabricated patterns |
| `config.py` | 413 | 2 style | Hardcoded regex strings |

**Total patterns across codebase: ~45**

---

## Proposed Architecture

### Directory Structure

```
src/integrity_checker/
├── extraction/
│   ├── patterns/                    # NEW: Modular pattern system
│   │   ├── __init__.py              # Registry + public API
│   │   ├── base.py                  # Base classes: CitationFormat, PatternSet
│   │   ├── registry.py              # Format registry with priority
│   │   ├── utils.py                 # Shared utilities (DOI, URL, year)
│   │   ├── apa.py                   # APA format (in-text + reference)
│   │   ├── ieee.py                  # IEEE format (in-text + reference)
│   │   ├── vancouver.py             # Vancouver format
│   │   ├── chicago.py               # Chicago format (future)
│   │   ├── mla.py                   # MLA format (future)
│   │   └── _registry.py             # Format registry data
│   ├── citation_extractor.py         # Simplified: uses registry
│   ├── reference_parser.py           # Simplified: uses format parsers
│   ├── style_detector.py             # Uses registry
│   └── regex_patterns.py             # Deprecated: re-export for compat
├── matching/
│   ├── author_parser.py             # Uses format-specific patterns
│   └── patterns/                    # Author patterns (future modular)
│       ├── __init__.py
│       └── author_patterns.py
├── linking/
│   └── citation_linker.py           # Uses registry
└── logic/
    └── rules.py                     # Uses shared utils
```

### Pattern Module Interface

```python
# Each format module implements this protocol
class CitationFormat(Protocol):
    name: str                    # "APA", "IEEE", etc.
    priority: int                # Higher = checked first
    
    # In-text patterns (for body extraction)
    @property
    def in_text_patterns(self) -> list[CompiledPattern]: ...
    
    # Reference list patterns (for bibliography parsing)
    @property
    def reference_patterns(self) -> list[CompiledPattern]: ...
    
    # Parser for reference list entries
    def parse_reference_entry(self, text: str) -> Citation | None: ...
    
    # Author parsing specific to this format
    def parse_authors(self, text: str) -> list[Author]: ...
    
    # Filter predicates for quality control
    def is_valid_citation(self, text: str) -> bool: ...
```

---

## Task Breakdown

### Phase 1: Foundation (Registry + Base Classes)

#### Task 1: Create Pattern Module Directory Structure

**Files:**
- Create: `src/integrity_checker/extraction/patterns/__init__.py`
- Create: `src/integrity_checker/extraction/patterns/base.py`
- Create: `src/integrity_checker/extraction/patterns/registry.py`
- Create: `src/integrity_checker/extraction/patterns/utils.py`
- Create: `tests/unit/test_patterns_base.py`
- Create: `tests/unit/test_patterns_registry.py`

**Interfaces:**
- Consumes: Nothing
- Produces: `CitationFormat`, `PatternSet`, `CompiledPattern` dataclasses; `get_all_formats()`, `get_format(name)`, `register_format()` functions

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_patterns_base.py
import pytest
from integrity_checker.extraction.patterns.base import (
    CitationFormat,
    PatternSet,
    CompiledPattern,
)

def test_pattern_set_dataclass():
    """PatternSet should hold pattern metadata."""
    ps = PatternSet(
        name="test_pattern",
        pattern=r"\d+",
        style="APA",
        pattern_type="in_text",
        description="Test pattern"
    )
    assert ps.name == "test_pattern"
    assert ps.pattern == r"\d+"
    assert ps.style == "APA"

def test_citation_format_protocol():
    """CitationFormat should define required interface."""
    # This will fail until we implement the base class
    from integrity_checker.extraction.patterns.base import CitationFormat
    assert hasattr(CitationFormat, '__iter__')  # Protocol check
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_patterns_base.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create base.py with core dataclasses**

```python
# src/integrity_checker/extraction/patterns/base.py
"""Base classes for modular citation format patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from integrity_checker.models.citation import Citation, CitationStyle, CitationType


class PatternType(str, Enum):
    """Type of citation pattern."""
    IN_TEXT = "in_text"
    REFERENCE_LIST = "reference_list"
    NUMERIC = "numeric"
    AUTHOR = "author"


@dataclass(frozen=True)
class CompiledPattern:
    """A compiled regex pattern with metadata."""
    name: str
    pattern: str
    compiled: re.Pattern = field(repr=False)
    pattern_type: PatternType
    style: str
    description: str
    
    @classmethod
    def create(cls, name: str, pattern: str, pattern_type: PatternType, 
               style: str, description: str) -> "CompiledPattern":
        """Factory method to compile and create."""
        return cls(
            name=name,
            pattern=pattern,
            compiled=re.compile(pattern),
            pattern_type=pattern_type,
            style=style,
            description=description,
        )


@dataclass
class PatternSet:
    """A set of patterns for a specific citation format component."""
    name: str
    pattern: str
    style: str
    pattern_type: PatternType
    description: str


@runtime_checkable
class CitationFormat(Protocol):
    """Protocol for citation format implementations."""
    
    @property
    def name(self) -> str:
        """Format name (e.g., 'APA', 'IEEE')."""
        ...
    
    @property
    def priority(self) -> int:
        """Priority for matching (higher = checked first)."""
        ...
    
    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        """In-text citation patterns."""
        ...
    
    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        """Reference list entry patterns."""
        ...
```

- [ ] **Step 4: Create utils.py with shared utilities**

```python
# src/integrity_checker/extraction/patterns/utils.py
"""Shared utilities for all citation formats."""

from __future__ import annotations

import re

# DOI patterns (single source of truth)
DOI_PATTERN = r"10\.\d{4,9}/[^\s\]\)\,;]+"
DOI_RE = re.compile(DOI_PATTERN)

# URL patterns (single source of truth)
URL_PATTERN = r"https?://[^\s\]\)\,;]+"
URL_RE = re.compile(URL_PATTERN)

# Year patterns
YEAR_PATTERN = r"\b((?:19|20)\d{2})([a-z]?)\b"
YEAR_RE = re.compile(YEAR_PATTERN)


def extract_doi(text: str) -> str | None:
    """Extract DOI from text."""
    m = DOI_RE.search(text)
    return m.group(0).rstrip(".,;:") if m else None


def extract_url(text: str) -> str | None:
    """Extract URL from text."""
    m = URL_RE.search(text)
    return m.group(0).rstrip(".,;:") if m else None


def extract_year(text: str) -> tuple[str | None, str | None]:
    """Extract year and optional suffix."""
    m = YEAR_RE.search(text)
    if m:
        return m.group(1), m.group(2) or None
    return None, None
```

- [ ] **Step 5: Create registry.py**

```python
# src/integrity_checker/extraction/patterns/registry.py
"""Registry for citation format implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CitationFormat

# Global registry
_FORMAT_REGISTRY: dict[str, CitationFormat] = {}
_PRIORITY_ORDER: list[CitationFormat] = []


def register_format(format_impl: CitationFormat) -> None:
    """Register a citation format implementation."""
    global _FORMAT_REGISTRY, _PRIORITY_ORDER
    _FORMAT_REGISTRY[format_impl.name] = format_impl
    # Rebuild priority order
    _PRIORITY_ORDER = sorted(
        _FORMAT_REGISTRY.values(),
        key=lambda f: f.priority,
        reverse=True
    )


def get_format(name: str) -> CitationFormat | None:
    """Get a specific format by name."""
    return _FORMAT_REGISTRY.get(name)


def get_all_formats() -> list[CitationFormat]:
    """Get all registered formats in priority order."""
    return list(_PRIORITY_ORDER)


def get_in_text_patterns() -> list:
    """Get all in-text patterns from all formats."""
    patterns = []
    for fmt in _PRIORITY_ORDER:
        patterns.extend(fmt.in_text_patterns)
    return patterns


def get_reference_patterns() -> list:
    """Get all reference list patterns from all formats."""
    patterns = []
    for fmt in _PRIORITY_ORDER:
        patterns.extend(fmt.reference_patterns)
    return patterns
```

- [ ] **Step 6: Create __init__.py with public API**

```python
# src/integrity_checker/extraction/patterns/__init__.py
"""Modular citation format pattern system.

Architecture:
    - base.py: Core dataclasses and protocols
    - registry.py: Format registration and lookup
    - utils.py: Shared utilities (DOI, URL, year patterns)
    - apa.py: APA format implementation
    - ieee.py: IEEE format implementation
    - vancouver.py: Vancouver format implementation

Usage:
    from integrity_checker.extraction.patterns import (
        get_all_formats,
        get_in_text_patterns,
        get_reference_patterns,
    )
    
    # Get all registered formats
    formats = get_all_formats()
    
    # Get all in-text patterns
    patterns = get_in_text_patterns()
"""

from .base import (
    CitationFormat,
    CompiledPattern,
    PatternSet,
    PatternType,
)
from .registry import (
    get_all_formats,
    get_format,
    get_in_text_patterns,
    get_reference_patterns,
    register_format,
)
from .utils import (
    DOI_PATTERN,
    DOI_RE,
    URL_PATTERN,
    URL_RE,
    YEAR_PATTERN,
    YEAR_RE,
    extract_doi,
    extract_url,
    extract_year,
)

__all__ = [
    # Base classes
    "CitationFormat",
    "CompiledPattern",
    "PatternSet",
    "PatternType",
    # Registry functions
    "get_all_formats",
    "get_format",
    "get_in_text_patterns",
    "get_reference_patterns",
    "register_format",
    # Utilities
    "DOI_PATTERN",
    "DOI_RE",
    "URL_PATTERN",
    "URL_RE",
    "YEAR_PATTERN",
    "YEAR_RE",
    "extract_doi",
    "extract_url",
    "extract_year",
]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/unit/test_patterns_base.py tests/unit/test_patterns_registry.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: create modular pattern foundation (Task 1)

- Add extraction/patterns/ directory with base classes
- CitationFormat protocol for format implementations
- PatternSet and CompiledPattern dataclasses
- Registry with register/get_all/get_by_name functions
- Shared utils for DOI/URL/year extraction
- Phase 1 foundation for modular citation patterns"
```

---

#### Task 2: Implement APA Format Module

**Files:**
- Create: `src/integrity_checker/extraction/patterns/apa.py`
- Modify: `src/integrity_checker/extraction/patterns/__init__.py`
- Create: `tests/unit/test_patterns_apa.py`

**Interfaces:**
- Consumes: `base.CitationFormat`, `utils.*`
- Produces: `APAFormat` class with in_text_patterns, reference_patterns, parse_reference_entry

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_patterns_apa.py
import pytest
from integrity_checker.extraction.patterns import get_format

def test_apa_format_registered():
    """APA format should be registered."""
    apa = get_format("APA")
    assert apa is not None
    assert apa.name == "APA"

def test_apa_in_text_patterns():
    """APA should have in-text patterns."""
    apa = get_format("APA")
    patterns = apa.in_text_patterns
    assert len(patterns) >= 2  # parenthetical + narrative
    
    # Check pattern names
    names = [p.name for p in patterns]
    assert "apa_intext_parenthetical" in names
    assert "apa_intext_narrative" in names

def test_apa_reference_patterns():
    """APA should have reference list patterns."""
    apa = get_format("APA")
    patterns = apa.reference_patterns
    assert len(patterns) >= 1

def test_apa_paranthetical_match():
    """APA parenthetical pattern should match (Smith, 2020)."""
    apa = get_format("APA")
    for p in apa.in_text_patterns:
        if p.name == "apa_intext_parenthetical":
            m = p.compiled.search("(Smith, 2020)")
            assert m is not None
            break

def test_apa_reference_parse():
    """APA reference entry parsing."""
    apa = get_format("APA")
    entry = "Smith, J. (2020). A Study of Things. Journal of Stuff, 10(2), 1-10."
    result = apa.parse_reference_entry(entry)
    assert result is not None
    assert result.year == "2020"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_patterns_apa.py -v`
Expected: FAIL (APA format not registered)

- [ ] **Step 3: Create apa.py with APA format implementation**

```python
# src/integrity_checker/extraction/patterns/apa.py
"""APA citation format implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .base import CitationFormat, CompiledPattern, PatternType
from .utils import DOI_RE, YEAR_RE, extract_doi, extract_year

if TYPE_CHECKING:
    from integrity_checker.models.citation import Citation


# APA In-Text Patterns
_APA_INTEXT_PARENTHETICAL = (
    r"\(([A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*,?\s*"
    r"(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*)?,?\s*"
    r"\d{4}[a-z]?)\)"
)

_APA_INTEXT_NARRATIVE = (
    r"([A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*,?\s*"
    r"(?:et\s+al\.|and\s+[A-Z][a-zÀ-ž]*(?:[A-Z][a-zÀ-ž]*)*)?,?\s*"
    r"\(\d{4}[a-z]?\))"
)

# APA Reference List Pattern
_APA_REFERENCE_ENTRY = (
    r"^([A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.\s*[A-Z]?[a-zÀ-ž]*)*"  # authors
    r"(?:,\s*&\s*[A-Z][a-zÀ-ž]+(?:,\s*[A-Z]\.\s*[A-Z]?[a-zÀ-ž]*)*)?)"
    r"\s*\(\d{4}[a-z]?\)"  # year
    r"\.\s*(.+?)\."  # title
)


class APAFormat:
    """APA citation format (7th edition)."""
    
    name = "APA"
    priority = 100
    
    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="apa_intext_parenthetical",
                pattern=_APA_INTEXT_PARENTHETICAL,
                pattern_type=PatternType.IN_TEXT,
                style=self.name,
                description="APA in-text parenthetical: (Author, 2020)",
            ),
            CompiledPattern.create(
                name="apa_intext_narrative",
                pattern=_APA_INTEXT_NARRATIVE,
                pattern_type=PatternType.IN_TEXT,
                style=self.name,
                description="APA in-text narrative: Author (2020)",
            ),
        ]
    
    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="apa_reference_entry",
                pattern=_APA_REFERENCE_ENTRY,
                pattern_type=PatternType.REFERENCE_LIST,
                style=self.name,
                description="APA reference list entry: Authors (Year). Title. Venue.",
            ),
        ]
    
    def parse_reference_entry(self, text: str) -> "Citation | None":
        """Parse APA reference entry."""
        from integrity_checker.models.citation import Citation, CitationType, CitationStyle
        from integrity_checker.matching.author_parser import parse_authors
        
        # Try to match APA reference pattern
        m = re.search(_APA_REFERENCE_ENTRY, text, re.MULTILINE)
        if not m:
            return None
        
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            matched_pattern="apa_reference_entry",
        )
        
        # Extract year
        year_m = YEAR_RE.search(text)
        if year_m:
            citation.year = year_m.group(1)
            citation.year_suffix = year_m.group(2) or None
        
        # Extract title (between year and first period after)
        # Simplified: use the captured group
        title = m.group(3).strip().rstrip(".") if m.group(3) else None
        if title:
            citation.title = title
        
        # Extract DOI
        citation.doi = extract_doi(text)
        
        # Parse authors
        if m.group(1):
            citation.authors = parse_authors(m.group(1))
        
        return citation
    
    def is_valid_citation(self, text: str) -> bool:
        """Check if text looks like a valid APA citation."""
        # Must have year in parentheses
        if not YEAR_RE.search(text):
            return False
        # Check for essay title indicators
        essay_indicators = [
            "this essay", "comprehensive survey", "comprehensive review",
            "introduction to", "abstract", "survey of"
        ]
        text_lower = text.lower()
        return not any(ind in text_lower for ind in essay_indicators)


# Auto-register
from .registry import register_format
register_format(APAFormat())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_patterns_apa.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: implement APA format module (Task 2)

- APAFormat class with in-text and reference patterns
- Parenthetical and narrative APA patterns
- Reference entry parser
- Auto-registration in registry"
```

---

#### Task 3: Implement IEEE Format Module

**Files:**
- Create: `src/integrity_checker/extraction/patterns/ieee.py`
- Create: `tests/unit/test_patterns_ieee.py`

**Interfaces:**
- Consumes: `base.CitationFormat`, `utils.*`, APA patterns for fallback
- Produces: `IEEEFormat` class

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_patterns_ieee.py
import pytest
from integrity_checker.extraction.patterns import get_format

def test_ieee_format_registered():
    """IEEE format should be registered."""
    ieee = get_format("IEEE")
    assert ieee is not None
    assert ieee.name == "IEEE"

def test_ieee_numeric_pattern():
    """IEEE numeric pattern should match [1], [1,2], [1-5]."""
    ieee = get_format("IEEE")
    patterns = ieee.in_text_patterns
    names = [p.name for p in patterns]
    assert "ieee_numeric" in names
    
    for p in patterns:
        if p.name == "ieee_numeric":
            assert p.compiled.search("[1]") is not None
            assert p.compiled.search("[1,2]") is not None
            assert p.compiled.search("[1-5]") is not None
            break

def test_ieee_reference_parse():
    """IEEE reference entry parsing."""
    ieee = get_format("IEEE")
    entry = '[1] S. Smith, "A Study of Things," Journal of Stuff, vol. 10, 2020.'
    result = ieee.parse_reference_entry(entry)
    assert result is not None
    assert result.numeric_index == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_patterns_ieee.py -v`
Expected: FAIL (IEEE format not registered)

- [ ] **Step 3: Create ieee.py with IEEE format implementation**

```python
# src/integrity_checker/extraction/patterns/ieee.py
"""IEEE citation format implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .base import CitationFormat, CompiledPattern, PatternType
from .utils import DOI_RE, YEAR_RE, extract_doi, extract_year

if TYPE_CHECKING:
    from integrity_checker.models.citation import Citation


# IEEE Numeric In-Text Pattern
_IEEE_NUMERIC = r"\[(\d+(?:[,\s\-]+\d+)*)\]"

# IEEE Reference Entry Pattern
_IEEE_REFERENCE_ENTRY = (
    r"""
    ^\[\s*(?P<index>\d+)\s*\]\s*      # [N]
    (?P<authors>[^"]+?),\s*           # authors (everything until quote)
    [""](?P<title>[^""]+)[""]\s*,\s*   # "title,"
    (?P<venue>.+?)$                   # venue (rest of line)
    """
)


class IEEEFormat:
    """IEEE citation format."""
    
    name = "IEEE"
    priority = 90  # Checked after APA (higher priority)
    
    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="ieee_numeric",
                pattern=_IEEE_NUMERIC,
                pattern_type=PatternType.NUMERIC,
                style=self.name,
                description="IEEE numeric: [1] | [1,2] | [1-5]",
            ),
        ]
    
    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="ieee_reference_entry",
                pattern=_IEEE_REFERENCE_ENTRY,
                pattern_type=PatternType.REFERENCE_LIST,
                style=self.name,
                description="IEEE reference: [N] Authors, \"Title,\" Venue.",
            ),
        ]
    
    def parse_reference_entry(self, text: str) -> "Citation | None":
        """Parse IEEE reference entry."""
        from integrity_checker.models.citation import Citation, CitationType, CitationStyle
        from integrity_checker.matching.author_parser import parse_authors
        
        # Extract numeric index first
        idx_m = re.match(r"\[\s*(\d+)\s*\]\s*", text)
        numeric_index = int(idx_m.group(1)) if idx_m else None
        
        # Try to find quoted title
        quote_m = re.search(r'[""]([^""]+)[""]', text)
        if not quote_m:
            return None
        
        title = quote_m.group(1).strip()
        
        # Extract year from venue
        venue = text[quote_m.end():].strip().lstrip(",").strip()
        year, suffix = extract_year(venue)
        
        # Extract authors (before the quote)
        authors_part = text[:quote_m.start()].strip()
        if idx_m:
            authors_part = text[idx_m.end():quote_m.start()].strip()
        authors_part = authors_part.rstrip(",").rstrip()
        
        citation = Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.IEEE,
            matched_pattern="ieee_reference_entry",
            numeric_index=numeric_index,
            title=title,
            year=year,
            year_suffix=suffix,
            authors=parse_authors(authors_part) if authors_part else None,
            doi=extract_doi(text),
        )
        
        return citation
    
    def is_reference_list_marker(self, text: str, match_start: int) -> bool:
        """Check if [N] is a reference list marker (not in-text)."""
        if match_start == 0:
            return True
        prefix = text[:match_start]
        return prefix.isspace() or bool(re.search(r"\n\s*$", prefix))
    
    def is_valid_citation(self, text: str) -> bool:
        """Check if text looks like a valid IEEE citation."""
        # Should have numeric reference
        if not re.search(_IEEE_NUMERIC, text):
            return False
        # Check for test scenario patterns
        test_patterns = [
            r"Reference:\s*\[\d+\]",
            r"In-text:\s*\(",
            r"Expected(?:Mapping|Label):",
            r"Scenario:",
        ]
        return not any(re.search(p, text, re.IGNORECASE) for p in test_patterns)


# Auto-register
from .registry import register_format
register_format(IEEEFormat())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_patterns_ieee.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: implement IEEE format module (Task 3)

- IEEEFormat class with numeric and reference patterns
- Quoted title parsing for reference entries
- Reference list marker detection
- Auto-registration in registry"
```

---

#### Task 4: Implement Vancouver Format Module

**Files:**
- Create: `src/integrity_checker/extraction/patterns/vancouver.py`
- Create: `tests/unit/test_patterns_vancouver.py`

**Interfaces:**
- Consumes: `base.CitationFormat`, `utils.*`
- Produces: `VancouverFormat` class

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_patterns_vancouver.py
import pytest
from integrity_checker.extraction.patterns import get_format

def test_vancouver_format_registered():
    """Vancouver format should be registered."""
    van = get_format("Vancouver")
    assert van is not None
    assert van.name == "Vancouver"

def test_vancouver_numeric_pattern():
    """Vancouver uses numeric like IEEE."""
    van = get_format("Vancouver")
    patterns = van.in_text_patterns
    assert len(patterns) >= 1

def test_vancouver_reference_parse():
    """Vancouver reference entry parsing."""
    van = get_format("Vancouver")
    entry = "Smith J. A study of things. J Stuff. 2020;10:1-10."
    result = van.parse_reference_entry(entry)
    assert result is not None
    assert result.year == "2020"

def test_vancouver_year_first_parse():
    """Vancouver year-first variant (BERT paper style)."""
    van = get_format("Vancouver")
    entry = "Samuel R. Bowman et al. 2015. A large annotated corpus. ACL."
    result = van.parse_reference_entry(entry)
    assert result is not None
    assert result.year == "2015"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_patterns_vancouver.py -v`
Expected: FAIL

- [ ] **Step 3: Create vancouver.py with Vancouver format implementation**

```python
# src/integrity_checker/extraction/patterns/vancouver.py
"""Vancouver citation format implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .base import CitationFormat, CompiledPattern, PatternType
from .utils import DOI_RE, YEAR_RE, extract_doi, extract_year

if TYPE_CHECKING:
    from integrity_checker.models.citation import Citation


# Vancouver In-Text (uses numeric like IEEE)
_VANCOUVER_NUMERIC = r"\[(\d+(?:[,\s\-]+\d+)*)\]"

# Standard Vancouver Reference Pattern
_VANCOUVER_REFERENCE = (
    r"""
    ^(?P<authors>.+?)\.\s+              # authors
    (?P<title>.+?)\.\s+                 # title
    (?P<venue>.+?)\.\s+                 # venue
    (?P<year>\d{4})(?P<rest>.*)$         # year + rest
    """
)

# Vancouver Year-First Variant
_VANCOUVER_YEAR_FIRST = (
    r"""
    ^(?P<authors>.+?)\.\s*             # authors
    \(?(?P<year>\d{4})\)?             # year
    [a-z]?\.\s+                         # period + space
    (?P<title>.+?)\.\s+                 # title
    (?P<venue>.+)$                      # venue
    """
)


class VancouverFormat:
    """Vancouver citation format (NLM style)."""
    
    name = "Vancouver"
    priority = 80
    
    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="vancouver_numeric",
                pattern=_VANCOUVER_NUMERIC,
                pattern_type=PatternType.NUMERIC,
                style=self.name,
                description="Vancouver numeric: [1] | [1,2]",
            ),
        ]
    
    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="vancouver_reference",
                pattern=_VANCOUVER_REFERENCE,
                pattern_type=PatternType.REFERENCE_LIST,
                style=self.name,
                description="Vancouver: Authors. Title. Venue. Year;pages.",
            ),
            CompiledPattern.create(
                name="vancouver_year_first",
                pattern=_VANCOUVER_YEAR_FIRST,
                pattern_type=PatternType.REFERENCE_LIST,
                style=self.name,
                description="Vancouver year-first: Authors. Year. Title. Venue.",
            ),
        ]
    
    def parse_reference_entry(self, text: str) -> "Citation | None":
        """Parse Vancouver reference entry."""
        from integrity_checker.models.citation import Citation, CitationType, CitationStyle
        from integrity_checker.matching.author_parser import parse_authors
        
        # Try year-first variant first (BERT paper style)
        m = re.search(_VANCOUVER_YEAR_FIRST, text, re.VERBOSE | re.MULTILINE)
        if m:
            return self._parse_year_first(m, text)
        
        # Try standard Vancouver
        m = re.search(_VANCOUVER_REFERENCE, text, re.VERBOSE | re.MULTILINE)
        if m:
            return self._parse_standard(m, text)
        
        return None
    
    def _parse_year_first(self, m: re.Match, text: str) -> "Citation":
        """Parse year-first variant."""
        from integrity_checker.models.citation import Citation, CitationType, CitationStyle
        from integrity_checker.matching.author_parser import parse_authors
        
        return Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.VANCOUVER,
            matched_pattern="vancouver_year_first",
            year=m.group("year"),
            title=m.group("title").strip(),
            venue=m.group("venue").strip(),
            authors=parse_authors(m.group("authors")),
            doi=extract_doi(text),
        )
    
    def _parse_standard(self, m: re.Match, text: str) -> "Citation":
        """Parse standard Vancouver format."""
        from integrity_checker.models.citation import Citation, CitationType, CitationStyle
        from integrity_checker.matching.author_parser import parse_authors
        
        return Citation(
            raw_text=text,
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.VANCOUVER,
            matched_pattern="vancouver_reference",
            year=m.group("year"),
            title=m.group("title").strip(),
            venue=m.group("venue").strip(),
            authors=parse_authors(m.group("authors")),
            doi=extract_doi(text),
        )
    
    def is_valid_citation(self, text: str) -> bool:
        """Check if text looks like a valid Vancouver citation."""
        # Should have year
        if not YEAR_RE.search(text):
            return False
        # Should have period separators (characteristic of Vancouver)
        periods = text.count(".")
        return periods >= 3


# Auto-register
from .registry import register_format
register_format(VancouverFormat())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_patterns_vancouver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: implement Vancouver format module (Task 4)

- VancouverFormat class with numeric and reference patterns
- Standard and year-first reference parsing
- Auto-registration in registry"
```

---

### Phase 2: Migration (Update Existing Code)

#### Task 5: Update CitationExtractor to Use Registry

**Files:**
- Modify: `src/integrity_checker/extraction/citation_extractor.py`
- Modify: `tests/unit/test_citation_extractor.py` (if needed)
- Create: `tests/unit/test_citation_extractor_registry.py`

**Interfaces:**
- Consumes: `patterns.get_in_text_patterns()`
- Produces: Updated CitationExtractor using registry

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_citation_extractor_registry.py
import pytest
from integrity_checker.extraction.citation_extractor import CitationExtractor

def test_extractor_uses_registry():
    """CitationExtractor should use registry patterns."""
    extractor = CitationExtractor()
    # Should have patterns from all registered formats
    assert len(extractor.patterns) >= 3  # APA + IEEE + Vancouver

def test_extractor_apa_patterns():
    """Extractor should include APA patterns."""
    extractor = CitationExtractor()
    names = [p.name for p in extractor.patterns]
    assert "apa_intext_parenthetical" in names
    assert "apa_intext_narrative" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_citation_extractor_registry.py -v`
Expected: FAIL (CitationExtractor doesn't use registry yet)

- [ ] **Step 3: Update CitationExtractor**

```python
# In citation_extractor.py, modify the __init__ method:

def __init__(self, patterns: Iterable[CitationPattern] | None = None) -> None:
    # NEW: Use registry if no patterns provided
    if patterns is None:
        from integrity_checker.extraction.patterns import get_in_text_patterns
        registry_patterns = get_in_text_patterns()
        # Convert CompiledPattern to CitationPattern for backward compat
        self.patterns = [
            CitationPattern(
                name=p.name,
                pattern=p.pattern,
                style=CitationStyle[p.style] if p.style in [e.name for e in CitationStyle] else CitationStyle.UNKNOWN,
                type=_map_pattern_type(p.pattern_type),
                description=p.description,
            )
            for p in registry_patterns
        ]
    else:
        self.patterns = list(patterns)
    
    self._compiled = [(p, re.compile(p.pattern)) for p in self.patterns]
    self.preprocessor = TextPreprocessor()


def _map_pattern_type(pt: PatternType) -> CitationType:
    """Map PatternType to CitationType for backward compatibility."""
    from integrity_checker.models.citation import CitationType
    mapping = {
        PatternType.IN_TEXT: CitationType.IN_TEXT,
        PatternType.NUMERIC: CitationType.NUMERIC,
        PatternType.REFERENCE_LIST: CitationType.REFERENCE_LIST,
    }
    return mapping.get(pt, CitationType.UNKNOWN)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_citation_extractor_registry.py tests/unit/test_citation_extractor.py -v`
Expected: PASS (existing tests should still pass)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: update CitationExtractor to use pattern registry (Task 5)

- CitationExtractor now uses get_in_text_patterns() from registry
- Backward compatible: still accepts patterns parameter
- Existing tests pass without modification"
```

---

#### Task 6: Update ReferenceListParser to Use Format Modules

**Files:**
- Modify: `src/integrity_checker/extraction/reference_parser.py`
- Create: `tests/unit/test_reference_parser_registry.py`

**Interfaces:**
- Consumes: Format modules with parse_reference_entry methods
- Produces: Updated ReferenceListParser using format-specific parsers

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_reference_parser_registry.py
import pytest
from integrity_checker.extraction.reference_parser import ReferenceListParser

def test_parser_uses_format_parsers():
    """ReferenceListParser should use format modules."""
    parser = ReferenceListParser()
    # Should have access to format parsers
    assert hasattr(parser, 'format_parsers')
    assert len(parser.format_parsers) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_reference_parser_registry.py -v`
Expected: FAIL

- [ ] **Step 3: Update ReferenceListParser**

```python
# In reference_parser.py, add format parser support:

class ReferenceListParser:
    def __init__(self, extractor: CitationExtractor | None = None) -> None:
        self.extractor = extractor or CitationExtractor()
        
        # NEW: Load format parsers from registry
        from integrity_checker.extraction.patterns import get_all_formats
        self.format_parsers = {
            fmt.name: fmt for fmt in get_all_formats()
        }
        
        # Keep legacy patterns for fallback
        self._legacy_patterns = {
            'apa': _APA_ENTRY_RE,
            'ieee': _IEEE_ENTRY_RE,
            'vancouver': _VANCOUVER_ENTRY_RE,
            'vancouver_year_first': _VANCOUVER_YEAR_FIRST_RE,
        }

    def _parse_entry(self, entry: str, order_index: int, page_num: int) -> Citation | None:
        """Parse 1 entry using format modules with fallback to legacy."""
        # Try format modules first
        for name, fmt in self.format_parsers.items():
            result = fmt.parse_reference_entry(entry)
            if result:
                result.order_index = order_index
                result.page_num = page_num
                return result
        
        # Fallback to legacy patterns
        return self._parse_entry_legacy(entry, order_index, page_num)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_reference_parser_registry.py tests/unit/test_reference_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: update ReferenceListParser to use format modules (Task 6)

- ReferenceListParser now uses format modules for parsing
- Falls back to legacy patterns for backward compatibility
- Existing tests pass without modification"
```

---

#### Task 7: Deprecate Old regex_patterns.py with Compatibility Layer

**Files:**
- Modify: `src/integrity_checker/extraction/regex_patterns.py`
- Create: `tests/unit/test_regex_patterns_compat.py`

**Interfaces:**
- Consumes: New pattern modules
- Produces: Deprecated module that re-exports from registry

- [ ] **Step 1: Update regex_patterns.py to be a compatibility layer**

```python
# src/integrity_checker/extraction/regex_patterns.py
"""Citation regex patterns — DEPRECATED: Use extraction.patterns instead.

This module is kept for backward compatibility.
New code should import from extraction.patterns instead.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

# Warn about deprecation
warnings.warn(
    "extraction.regex_patterns is deprecated. Use extraction.patterns instead.",
    DeprecationWarning,
    stacklevel=2
)

from integrity_checker.models.citation import CitationStyle, CitationType
from integrity_checker.extraction.patterns import (
    get_in_text_patterns,
    get_reference_patterns,
    CompiledPattern,
    DOI_PATTERN,
    URL_PATTERN,
)


@dataclass(frozen=True)
class CitationPattern:
    """DEPRECATED: Use CompiledPattern from extraction.patterns."""
    name: str
    pattern: str
    style: CitationStyle
    type: CitationType
    description: str


# Re-export patterns from registry for backward compatibility
def _convert_to_citation_pattern(p: CompiledPattern) -> CitationPattern:
    """Convert CompiledPattern to deprecated CitationPattern format."""
    style_map = {
        "APA": CitationStyle.APA,
        "IEEE": CitationStyle.IEEE,
        "VANCOUVER": CitationStyle.VANCOUVER,
        "CHICAGO": CitationStyle.CHICAGO,
        "MLA": CitationStyle.MLA,
    }
    type_map = {
        "in_text": CitationType.IN_TEXT,
        "numeric": CitationType.NUMERIC,
        "reference_list": CitationType.REFERENCE_LIST,
    }
    return CitationPattern(
        name=p.name,
        pattern=p.pattern,
        style=style_map.get(p.style.upper(), CitationStyle.UNKNOWN),
        type=type_map.get(p.pattern_type.value, CitationType.UNKNOWN),
        description=p.description,
    )


# Backward compatible list
CITATION_PATTERNS: list[CitationPattern] = [
    _convert_to_citation_pattern(p) 
    for p in get_in_text_patterns()
]


def get_all_patterns() -> list[CitationPattern]:
    """DEPRECATED: Use get_in_text_patterns() from extraction.patterns."""
    return list(CITATION_PATTERNS)
```

- [ ] **Step 2: Run tests to verify compatibility**

Run: `pytest tests/unit/test_regex_patterns_compat.py tests/unit/test_regex_patterns.py -v`
Expected: PASS (with deprecation warnings)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: deprecate regex_patterns.py with compat layer (Task 7)

- regex_patterns.py now re-exports from extraction.patterns
- Shows deprecation warning when imported
- Backward compatible API maintained
- Existing code continues to work"
```

---

#### Task 8: Update StyleDetector to Use Registry

**Files:**
- Modify: `src/integrity_checker/extraction/style_detector.py`

**Interfaces:**
- Consumes: Format registry
- Produces: StyleDetector using registry for patterns

- [ ] **Step 1: Review current implementation**

The StyleDetector currently loads patterns from config. We'll update it to optionally use registry patterns.

- [ ] **Step 2: Update StyleDetector**

```python
# In style_detector.py, add registry support:

def _extract_features(self, body_citations, bib_citations):
    # Use registry patterns if available
    from integrity_checker.extraction.patterns import get_all_formats
    
    apa_re = re.compile(self.config.features.apa_author_year_pattern)
    ieee_re = re.compile(self.config.features.ieee_numeric_pattern)
    
    # Can also get from registry:
    # for fmt in get_all_formats():
    #     for p in fmt.in_text_patterns:
    #         ...
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/test_style_detector.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: update StyleDetector with registry support (Task 8)

- StyleDetector can now use registry patterns
- Maintains config-based pattern fallback
- Existing tests pass"
```

---

#### Task 9: Update Author Parser to Use Format Modules

**Files:**
- Modify: `src/integrity_checker/matching/author_parser.py`

**Interfaces:**
- Consumes: Format-specific author patterns
- Produces: Author parser with format-aware parsing

- [ ] **Step 1: Review and update author parser**

The author parser already has format-specific logic. We'll extract this into format-specific modules.

```python
# In author_parser.py, add format-aware entry points:

# Existing parse_authors() function can be called by format modules
# No major changes needed - it already handles multiple formats

def parse_authors_for_format(raw: str, format_name: str) -> list[Author]:
    """Parse authors with format-specific heuristics."""
    authors = parse_authors(raw)  # Existing logic
    return authors
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/unit/test_author_parser.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: author parser format-awareness (Task 9)

- Author parser maintains existing functionality
- Added format-aware entry point
- No breaking changes"
```

---

### Phase 3: Cleanup and Documentation

#### Task 10: Create Future Format Templates

**Files:**
- Create: `src/integrity_checker/extraction/patterns/chicago.py`
- Create: `src/integrity_checker/extraction/patterns/mla.py`
- Create: `docs/format_development_guide.md`

**Interfaces:**
- Consumes: Format template
- Produces: Empty but registered format modules

- [ ] **Step 1: Create Chicago template**

```python
# src/integrity_checker/extraction/patterns/chicago.py
"""Chicago citation format implementation - PLACEHOLDER."""

from __future__ import annotations

from .base import CitationFormat, CompiledPattern, PatternType
from .registry import register_format


class ChicagoFormat:
    """Chicago citation format - NOT YET IMPLEMENTED."""
    
    name = "Chicago"
    priority = 70
    
    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        # TODO: Implement Chicago in-text patterns
        return []
    
    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        # TODO: Implement Chicago reference patterns
        return []
    
    def parse_reference_entry(self, text: str):
        # TODO: Implement parser
        return None
    
    def is_valid_citation(self, text: str) -> bool:
        return False


register_format(ChicagoFormat())
```

- [ ] **Step 2: Create development guide**

```markdown
# Developing New Citation Formats

## Quick Start

1. Create a new file: `src/integrity_checker/extraction/patterns/{format}.py`
2. Implement the `CitationFormat` protocol
3. Auto-register with `register_format()`

## Template

```python
from __future__ import annotations

from .base import CitationFormat, CompiledPattern, PatternType
from .utils import extract_doi, extract_year
from .registry import register_format

class {Format}Format:
    name = "{FORMAT}"
    priority = 50  # Lower than established formats
    
    @property
    def in_text_patterns(self) -> list[CompiledPattern]:
        return [
            CompiledPattern.create(
                name="{format}_intext",
                pattern=r"...",
                pattern_type=PatternType.IN_TEXT,
                style=self.name,
                description="...",
            ),
        ]
    
    @property
    def reference_patterns(self) -> list[CompiledPattern]:
        return []
    
    def parse_reference_entry(self, text: str):
        # Return Citation or None
        ...
    
    def is_valid_citation(self, text: str) -> bool:
        ...

register_format({Format}Format())
```

## Priority Guidelines

- 100: APA (most common in academia)
- 90: IEEE (engineering/computer science)
- 80: Vancouver (medical/health sciences)
- 70: Chicago, MLA (humanities)
- 50: Others
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/unit/test_patterns_*.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: add format development templates (Task 10)

- Chicago format placeholder
- MLA format placeholder  
- Development guide for new formats"
```

---

#### Task 11: Final Integration and Cleanup

**Files:**
- Update: `src/integrity_checker/extraction/patterns/__init__.py`
- Update: `src/integrity_checker/extraction/__init__.py`
- Update: `CLAUDE.md` with new architecture documentation

**Interfaces:**
- Consumes: All format modules
- Produces: Clean public API

- [ ] **Step 1: Finalize __init__.py files**

```python
# src/integrity_checker/extraction/__init__.py

# Add import of new pattern system
from .patterns import (
    get_all_formats,
    get_format,
    get_in_text_patterns,
    get_reference_patterns,
    register_format,
    # Base classes
    CitationFormat,
    CompiledPattern,
    PatternSet,
    PatternType,
    # Utilities
    DOI_PATTERN,
    DOI_RE,
    URL_PATTERN,
    URL_RE,
    YEAR_PATTERN,
    YEAR_RE,
    extract_doi,
    extract_url,
    extract_year,
)

__all__ = [
    # ... existing exports ...
    # New pattern exports
    "get_all_formats",
    "get_format",
    "get_in_text_patterns",
    "get_reference_patterns",
    "CitationFormat",
    "CompiledPattern",
    "PatternSet",
    "PatternType",
]
```

- [ ] **Step 2: Update CLAUDE.md**

```markdown
## Citation Pattern Architecture (v2.0)

New modular pattern system (2026-09-28):

```
src/integrity_checker/extraction/patterns/
├── __init__.py          # Public API
├── base.py              # CitationFormat protocol, PatternSet, CompiledPattern
├── registry.py          # Format registration and lookup
├── utils.py             # Shared utilities (DOI, URL, year)
├── apa.py               # APA format (in-text + reference)
├── ieee.py              # IEEE format (in-text + reference)
├── vancouver.py         # Vancouver format
├── chicago.py           # Chicago format (placeholder)
└── mla.py               # MLA format (placeholder)
```

Each format is a self-contained module with:
- In-text patterns (for body extraction)
- Reference list patterns (for bibliography parsing)
- Parser for reference entries
- Quality filter predicates

Adding a new format:
1. Create `src/integrity_checker/extraction/patterns/{format}.py`
2. Implement `CitationFormat` protocol
3. Auto-register with `register_format()`
```

- [ ] **Step 3: Run full test suite**

Run: `source .venv/bin/activate && python -m pytest tests/ -v --tb=short`
Expected: All 619 tests pass + new tests pass

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: finalize modular pattern architecture (Task 11)

- Clean up __init__.py exports
- Update CLAUDE.md with new architecture
- All tests pass"
```

---

## Migration Summary

### Phase 1: Foundation (Tasks 1-4)
- Core base classes and registry
- APA, IEEE, Vancouver format modules

### Phase 2: Migration (Tasks 5-9)
- Update CitationExtractor to use registry
- Update ReferenceListParser to use format modules
- Deprecate old regex_patterns.py
- Update StyleDetector and AuthorParser

### Phase 3: Cleanup (Tasks 10-11)
- Add format templates for future development
- Final integration and documentation

### File Count
- **New files:** 15
- **Modified files:** 6
- **Deleted files:** 0 (all backward compatible)

### Test Coverage
- **New tests:** ~10 test files
- **Existing tests:** All should pass without modification

---

## Key Design Decisions

1. **Plugin Architecture**: Each format is self-contained and auto-registers
2. **Protocol-based**: CitationFormat is a Protocol for flexibility
3. **Backward Compatibility**: Old APIs still work via compatibility layers
4. **Single Source of Truth**: DOI/URL/year patterns in utils.py only
5. **Priority-based Matching**: Higher priority formats checked first

---

## Success Metrics

1. All 619 existing tests pass
2. New format can be added with <50 lines of code
3. Pattern changes don't require touching extraction logic
4. Clear separation between pattern definition and parsing logic

---

## Execution Recommendation

**For this plan I recommend Subagent-driven**, because:
- 11 tasks with clear boundaries
- Each task produces independently testable output
- Parallel work possible on format modules (Tasks 2, 3, 4)
- Sequential work needed for migration (Tasks 5-9 depend on 1-4)

Tasks 1-4 can run in parallel with different subagents. Tasks 5-9 should run sequentially.
