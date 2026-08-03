"""Extraction module — PDF → Citation.

Bao gồm:
- BasePDFParser (abstract) + MuPdfParser + PdfPlumberParser
- TextPreprocessor (Unicode, ligature, line-break normalization)
- RegexPatterns (APA/MLA/Chicago/IEEE/DOI/URL)
- CitationExtractor (regex + heuristics)
- ReferenceListParser (parse "References" section cuối bài)
- SectionSegmenter (phân vùng body / bibliography / appendix) — MỚI v1.2
- GROBID adapter (TEI XML → GrobidOutput) — MỚI v1.2
"""

from integrity_checker.extraction.base import BasePDFParser, Document
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.extraction.mupdf_parser import MuPdfParser
from integrity_checker.extraction.pdfplumber_parser import PdfPlumberParser
from integrity_checker.extraction.reference_parser import ReferenceListParser
from integrity_checker.extraction.grobid_parser import (
    GrobidAuthor,
    GrobidBibEntry,
    GrobidCitation,
    GrobidOutput,
    GrobidSection,
    call_grobid_fulltext,
    parse_tei,
)
from integrity_checker.extraction.regex_patterns import CitationPattern, get_all_patterns
from integrity_checker.extraction.section_segmenter import (
    DocumentSection,
    SectionSegmenter,
    SectionType,
)
from integrity_checker.extraction.text_preprocessor import TextPreprocessor

__all__ = [
    "BasePDFParser",
    "Document",
    "MuPdfParser",
    "PdfPlumberParser",
    "TextPreprocessor",
    "CitationPattern",
    "get_all_patterns",
    "CitationExtractor",
    "ReferenceListParser",
    "DocumentSection",
    "SectionSegmenter",
    "SectionType",
    "GrobidAuthor",
    "GrobidBibEntry",
    "GrobidCitation",
    "GrobidOutput",
    "GrobidSection",
    "call_grobid_fulltext",
    "parse_tei",
]