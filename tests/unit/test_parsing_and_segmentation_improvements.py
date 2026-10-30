"""Unit tests for Task 1 Parsing & Segmentation improvements across multi-style PDFs."""

from __future__ import annotations

from integrity_checker.extraction.base import Document, Page
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.extraction.patterns.chicago import ChicagoFormat
from integrity_checker.extraction.patterns.harvard import HarvardFormat
from integrity_checker.extraction.reference_parser import ReferenceListParser
from integrity_checker.extraction.section_segmenter import SectionSegmenter, SectionType
from integrity_checker.models.citation import CitationStyle


def _make_doc(*page_texts: str) -> Document:
    pages = [
        Page(page_num=i + 1, text=txt, has_text_layer=True)
        for i, txt in enumerate(page_texts)
    ]
    return Document(file_path="test.pdf", num_pages=len(pages), pages=pages)


def test_section_segmenter_notes_header_and_table_note_guard() -> None:
    """SectionSegmenter detects numbered 'Notes' bibliography headers while ignoring table notes."""
    body_page_with_table_note = (
        "Table 1. Regression results across cohorts\n"
        "Notes\n"
        "* p < 0.05, ** p < 0.01. Standard errors in parentheses.\n"
        "The empirical analysis proceeds in the next section.\n"
    )
    notes_bib_page = (
        "Notes\n"
        "1. John Smith, The Architecture of Modern Systems (Chicago: University of Chicago Press, 2019), 45.\n"
        "2. Jane Doe, \"Distributed Consensus Revisited,\" Journal of Systems 14, no. 2 (2020): 112-130.\n"
    )
    doc = _make_doc(body_page_with_table_note, notes_bib_page)
    sections = SectionSegmenter().segment(doc)
    bib_secs = [s for s in sections if s.section_type == SectionType.BIBLIOGRAPHY]
    assert len(bib_secs) == 1
    assert bib_secs[0].start_page == 2


def test_section_segmenter_implicit_dot_numbered_bibliography_and_pre_header_slice() -> None:
    """SectionSegmenter detects implicit '1. Author...' bibliography and preserves pre-reference body prose."""
    p1 = "Introduction to perovskite solar cells and charge transport."
    p2 = (
        "Conclusion: These findings demonstrate high stability under continuous illumination (Smith, 2020).\n"
        "1. Bach, U. et al. Solid-state dye-sensitized mesoporous TiO2 solar cells. Nature 395, 583-585 (1998).\n"
        "2. O'Regan, B. & Gratzel, M. A low-cost, high-efficiency solar cell. Nature 353, 737-740 (1991).\n"
        "3. Kojima, A. et al. Organometal halide perovskites as visible-light sensitizers. J. Am. Chem. Soc. 131, 6050-6051 (2009).\n"
        "4. Lee, M. M. et al. Efficient hybrid solar cells based on meso-superstructured organometal halide perovskites. Science 338, 643-647 (2012).\n"
        "Acknowledgments\n"
        "We thank the National Science Foundation for financial support.\n"
    )
    doc = _make_doc(p1, p2)
    sections = SectionSegmenter().segment(doc)
    bib_secs = [s for s in sections if s.section_type == SectionType.BIBLIOGRAPHY]
    app_secs = [s for s in sections if s.section_type == SectionType.APPENDIX]
    assert len(bib_secs) == 1
    assert "Smith, 2020" in (bib_secs[0].metadata or {}).get("pre_header_body_text", "")
    assert "Bach, U." in bib_secs[0].text
    assert "National Science Foundation" not in bib_secs[0].text
    assert len(app_secs) == 1


def test_section_segmenter_wrapped_article_a_not_treated_as_appendix() -> None:
    """Wrapped article 'A' or initial 'A.' inside bibliography entries never triggers false appendix truncation."""
    p1 = "Body text citing [1] and [2] and [3]."
    p2 = (
        "References\n"
        "[1] A. Author, \"Structural Health Monitoring:\n"
        "A\n"
        "Comprehensive\n"
        "Survey,\" IEEE Sensors Journal, vol. 20, pp. 1-15, 2020.\n"
        "[2] B. Barnard,\n"
        "A.\n"
        "History of Computing, New York: Press, 2021.\n"
        "[3] C. Chen, \"Deep Learning for Vision,\" IEEE Access, vol. 9, pp. 100-120, 2022.\n"
    )
    doc = _make_doc(p1, p2)
    sections = SectionSegmenter().segment(doc)
    assert not any(s.section_type == SectionType.APPENDIX for s in sections)
    bib_secs = [s for s in sections if s.section_type == SectionType.BIBLIOGRAPHY]
    assert len(bib_secs) == 1
    assert "[3] C. Chen" in bib_secs[0].text


def test_section_segmenter_and_citation_extractor_ignore_table_column_headers() -> None:
    """Mid-document table column headers 'References' and 'Literature' are ignored by SectionSegmenter and CitationExtractor."""
    p1 = (
        "Table 1. Comparison of sensor modalities\n"
        "Sensor Type\n"
        "Strengths\n"
        "Limitations\n"
        "References\n"
        "Optical fiber | High sensitivity | Fragile | (Smith, 2020; Doe, 2021)\n"
        "Piezoelectric | Wide bandwidth | Temperature drift | (Johnson, 2019)\n"
    )
    p2 = "Further analysis in the body text confirms these findings (Williams, 2022)."
    p3 = (
        "References\n"
        "Doe, J. (2021). Optical fiber sensing. Journal of Sensors, 12(1), 10-20.\n"
        "Johnson, M. (2019). Piezoelectric transducers. Measurement Science, 8(3), 45-60.\n"
        "Smith, A. (2020). Structural monitoring. Engineering Review, 15(2), 100-115.\n"
        "Williams, R. (2022). Multimodal sensor fusion. IEEE Sensors, 22(4), 300-312.\n"
    )
    doc = _make_doc(p1, p2, p3)
    sections = SectionSegmenter().segment(doc)
    bib_secs = [s for s in sections if s.section_type == SectionType.BIBLIOGRAPHY]
    assert len(bib_secs) == 1
    assert bib_secs[0].start_page == 3

    body_doc = _make_doc(p1, p2)
    cits = CitationExtractor(preserve_occurrences=True).extract_from_document(
        body_doc, stop_at_bibliography=False
    )
    assert any("Williams" in c.raw_text for c in cits)


def test_section_segmenter_synthetic_footnote_bibliography() -> None:
    """Multi-page footnote-only Chicago papers synthesize a BIBLIOGRAPHY section from sequential footnotes."""
    pages = []
    for i in range(1, 6):
        fn1 = 2 * i - 1
        fn2 = 2 * i
        pages.append(
            f"Body prose on page {i} discussing historical developments.{fn1}\n"
            f"More body prose on page {i}.{fn2}\n"
            f"{fn1} Author{fn1} Surname{fn1}, Book Title {fn1} (London: Press, {1990 + fn1}), 12.\n"
            f"{fn2} Author{fn2} Surname{fn2}, 'Article Title {fn2}', History Journal 10, no. 1 ({1990 + fn2}): 34-56.\n"
        )
    doc = _make_doc(*pages)
    sections = SectionSegmenter().segment(doc)
    bib_secs = [s for s in sections if s.section_type == SectionType.BIBLIOGRAPHY]
    assert len(bib_secs) == 1
    assert bib_secs[0].metadata.get("synthetic_footnote_bibliography") is True
    refs = ReferenceListParser().parse_reference_section(
        _make_doc(bib_secs[0].text)
    )
    assert len(refs) == 10


def test_reference_parser_doi_prefix_semicolon_authors_ellipsis_and_asterisk() -> None:
    """ReferenceListParser splits on doi:10.xxxx/ and preserves semicolon authors, APA '. . .' ellipsis, and '*Author'."""
    bib_text = (
        "References\n"
        "*Adil, A., & Kamal, A. (2016). Impact of psychological capital on authentic leadership. "
        "Journal of Behavioral Sciences, 26(1), 52-70. doi:10.1037/cbs0000012 "
        "Bond, G. R., Drake, R. E., Becker, D. R., Noel, V. A., Swanson, S. J., . . . Frounfelker, R. L. (2015). "
        "Supported employment for people with severe mental illness. Psychiatric Services, 66(9), 948-955. "
        "doi:10.1176/appi.ps.201400510 "
        "Abdi, K.; Mardani, A.; Senin, A. A.; Tupenaite, L.; Naimaviciene, J.; Kanapeckiene, L.; Kutut, V. (2018). "
        "The effect of knowledge management on organizational innovation. Sustainability, 10(10), 3681.\n"
    )
    refs = ReferenceListParser().parse_reference_section(_make_doc(bib_text))
    assert len(refs) == 3
    assert any("Adil" in str(a) for a in refs[0].authors)
    assert any("Bond" in str(a) for a in refs[1].authors)
    assert any("Abdi" in str(a) for a in refs[2].authors)


def test_harvard_and_chicago_colon_page_intext_and_au_harvard_reference() -> None:
    """Colon-separated page numbers '(Author, 2020: 45)' and Australian unparenthesized Harvard references parse cleanly."""
    body_text = "Prior work established this framework (Bourdieu, 1984: 45; Foucault 1977: 112-115)."
    cits = CitationExtractor(preserve_occurrences=True).extract_from_document(_make_doc(body_text))
    assert len(cits) >= 1
    assert any("1984" in (c.year or c.raw_text) for c in cits)

    au_ref = HarvardFormat().parse_reference_entry(
        "Acker, A 2015, 'How cells paved the way for mobile phones', Information & Culture, vol. 50, no. 3, pp. 345-367."
    )
    assert au_ref is not None
    assert au_ref.style == CitationStyle.HARVARD
    assert au_ref.year == "2015"
    assert "How cells paved the way" in (au_ref.title or "")

    ch_ref = ChicagoFormat().parse_reference_entry(
        "1. Philip Barnes, 'Working Paper 36 and Religious Education', Journal of Education 6, no. 1 (2002): 61-77."
    )
    assert ch_ref is not None
    assert ch_ref.numeric_index == 1
    assert ch_ref.year == "2002"
    assert any("Barnes" in str(a) for a in ch_ref.authors)
