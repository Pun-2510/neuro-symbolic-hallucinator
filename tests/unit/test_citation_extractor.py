"""Unit tests cho CitationExtractor."""

from __future__ import annotations

from integrity_checker.extraction import CitationExtractor
from integrity_checker.extraction.base import Document, Page
from integrity_checker.models.citation import CitationType


def _make_doc(text: str) -> Document:
    return Document(
        file_path="<test>",
        num_pages=1,
        pages=[Page(page_num=1, text=text, has_text_layer=True)],
        parser_used="test",
    )


def test_extract_apa_intext_parenthetical() -> None:
    text = "Some claim (Smith, 2020). And another (Jones et al., 2019)."
    doc = _make_doc(text)
    citations = CitationExtractor().extract_from_document(doc)
    assert len(citations) >= 2
    raw_texts = [c.raw_text for c in citations]
    assert any("Smith" in t and "2020" in t for t in raw_texts)
    assert any("Jones" in t and "2019" in t for t in raw_texts)


def test_extract_doi() -> None:
    text = "Reference: 10.1038/nature14539 (LeCun et al., 2015)."
    doc = _make_doc(text)
    citations = CitationExtractor().extract_from_document(doc)
    doi_citations = [c for c in citations if c.citation_type == CitationType.DOI]
    assert len(doi_citations) >= 1
    assert doi_citations[0].doi == "10.1038/nature14539"


def test_extract_numeric() -> None:
    text = "This is well established [1, 2] and [3-5]."
    doc = _make_doc(text)
    citations = CitationExtractor().extract_from_document(doc)
    numeric = [c for c in citations if c.citation_type == CitationType.NUMERIC]
    assert len(numeric) >= 2


def test_dedupe() -> None:
    """Cùng 1 citation xuất hiện nhiều lần → chỉ giữ 1."""
    text = "(Smith, 2020). (Smith, 2020). Again (Smith, 2020)."
    doc = _make_doc(text)
    citations = CitationExtractor().extract_from_document(doc)
    seen = set()
    for c in citations:
        key = (c.style.value, c.raw_text.lower().strip())
        assert key not in seen
        seen.add(key)


def test_no_false_positive_on_plain_text() -> None:
    text = "This is just plain text with no citations at all."
    doc = _make_doc(text)
    citations = CitationExtractor().extract_from_document(doc)
    # Should be empty (no DOI, no APA, no numeric brackets)
    assert len(citations) == 0 or all(c.citation_type.value == "unknown" for c in citations)