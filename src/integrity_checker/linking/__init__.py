"""Bidirectional citation linking — v1.2 §3.5.

Public API:
    CitationLinker      — 2 chiều in-text ↔ reference entry, 7 trạng thái.
    DuplicateDetector  — phát hiện reference entry trùng nhau.
    CitationMappingStatus — enum 7 trạng thái (v1.2 §3.2.2).
    CitationLink       — 1 quan hệ in-text ↔ reference.
    LinkingResult      — đầu ra aggregate cho 1 Document.
    CitationOccurrence — wrapper cho in-text citation.
    ReferenceEntry     — wrapper cho reference list entry.
    StyleProfile       — document-level citation style.
    DuplicateGroup     — 1 nhóm reference entries trùng nhau.

    MappingMethod      — enum cách quyết định mapping (re-export từ models).

Tích hợp với config:
    settings.linking.exclude_sections
    settings.linking.duplicate_detection.title_year_author_similarity
    settings.linking.statuses.enabled
    settings.style_detection (inherited từ cùng config)

Pipeline call:
    linker = CitationLinker()
    res = linker.link(in_text_citations, reference_entries, style_profile)
    dupes = DuplicateDetector().find_duplicates(reference_entries)
    combined = merge_with_style_context(res, dupes, style_profile)

References:
    v1.2 spec §3.2.2 (mapping statuses)
    v1.2 spec §3.5 (bidirectional linking)
    v1.2 spec §3.5 (duplicate detection)
"""

from integrity_checker.linking.citation_linker import (
    CitationLinker,
    LinkingResult,
)
from integrity_checker.linking.duplicate_detector import (
    DuplicateDetector,
    DuplicateGroup,
)
from integrity_checker.linking.statuses import (
    CitationLink,
    CitationMappingStatus,
    CitationOccurrence,
    ReferenceEntry,
    StyleProfile,
)
from integrity_checker.models.validation import CitationLink as CitationLinkModel
from integrity_checker.models.validation import MappingMethod

__all__ = [
    "CitationLinker",
    "CitationMappingStatus",
    "CitationLink",
    "CitationLinkModel",
    "LinkingResult",
    "DuplicateDetector",
    "DuplicateGroup",
    "CitationOccurrence",
    "ReferenceEntry",
    "StyleProfile",
    "MappingMethod",
]
