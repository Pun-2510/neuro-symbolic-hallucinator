"""Unit tests for Task 2: In-text extraction and bidirectional linking improvements."""

from __future__ import annotations

from integrity_checker.extraction.base import Document, Page
from integrity_checker.extraction.reference_parser import ReferenceListParser
from integrity_checker.linking.citation_linker import CitationLinker
from integrity_checker.linking.statuses import CitationMappingStatus
from integrity_checker.models.citation import Citation, CitationStyle, CitationType


def _make_doc(text: str) -> Document:
    return Document(
        file_path="test.pdf",
        num_pages=1,
        pages=[Page(page_num=1, text=text, has_text_layer=True)],
    )


def test_chicago_nb_article_not_stolen_by_harvard_fallback() -> None:
    """Numbered Chicago Notes-Bibliography articles with '(Year): pages' must not be stolen by Harvard fallback."""
    parser = ReferenceListParser()
    bib_text = (
        "References\n"
        '1. Chandra, K. Ram, Et Al. "Exploring the depths of human emotion: '
        'A literary analysis." Journal of Literary Studies 4.1 (2022): 19-27.\n'
        '2. Smith, John. "Modernist Poetics." Modern Fiction 12.2 (2021): 45-60.\n'
    )
    refs = parser.parse_reference_section(_make_doc(bib_text))
    assert len(refs) == 2
    assert refs[0].year == "2022"
    assert refs[0].title and "Exploring the depths of human emotion" in refs[0].title
    assert refs[0].authors


def test_period_after_bracket_prefix_normalized() -> None:
    """Entries starting with '[1]. Author' should strip the period after the bracket cleanly."""
    parser = ReferenceListParser()
    bib_text = (
        "Works Cited\n"
        '[1]. Abraham, Sarah. "Postcolonial Narratives in Contemporary Fiction." '
        "Ariel, vol. 50, no. 2, 2019, pp. 101-120.\n"
        '[2]. Alone, Y. S. "Brahmanical Modernity and Dalit Aesthetics." '
        "Economic and Political Weekly, vol. 52, no. 15, 2017, pp. 44-51.\n"
    )
    refs = parser.parse_reference_section(_make_doc(bib_text))
    assert len(refs) == 2
    assert refs[0].numeric_index == 1
    assert refs[0].authors
    first_author = str(refs[0].authors[0])
    assert "Abraham" in first_author
    assert not first_author.startswith(".")


def test_vn_traditional_fallback_extracts_personal_and_agency_authors() -> None:
    """Numbered Vietnamese traditional references should extract personal and agency authors before the first comma."""
    parser = ReferenceListParser()
    bib_text = (
        "TÀI LIỆU THAM KHẢO\n"
        "[1] Phùng Thị Hằng, Thực trạng thi hành pháp luật về thẩm quyền giải quyết tranh chấp đất đai, 2021.\n"
        "[2] Sở Tài nguyên và Môi trường Thành phố Hồ Chí Minh, Báo cáo tổng kết công tác quản lý đất đai giai đoạn 2018-2022, 2022.\n"
    )
    refs = parser.parse_reference_section(_make_doc(bib_text))
    assert len(refs) == 2
    assert refs[0].authors
    assert "Phùng Thị Hằng" in str(refs[0].authors[0])
    assert refs[1].authors
    assert "Sở Tài nguyên và Môi trường" in str(refs[1].authors[0])


def test_corporate_acronym_and_initialism_linking() -> None:
    """CitationLinker should link (WHO, 2020) to 'World Health Organization (2020)' via initialism."""
    linker = CitationLinker()
    body = [
        Citation(
            raw_text="(WHO, 2020)",
            citation_type=CitationType.IN_TEXT,
            style=CitationStyle.APA,
            page_num=1,
        )
    ]
    bib = [
        Citation(
            raw_text="World Health Organization (2020). Coronavirus disease (COVID-19) situation report.",
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            page_num=5,
            authors=["World Health Organization"],
            year="2020",
            title="Coronavirus disease (COVID-19) situation report",
        )
    ]
    res = linker.link(body, bib)
    assert len(res.links) == 1
    assert res.links[0].status == CitationMappingStatus.MATCHED
    assert len(res.unmatched_reference_ids) == 0


def test_work_title_year_linking() -> None:
    """CitationLinker should link work-title + year citations like '(Capitalism and Slavery, 1944)' to the matching bibliography title."""
    linker = CitationLinker()
    body = [
        Citation(
            raw_text="(Capitalism and Slavery, 1944)",
            citation_type=CitationType.IN_TEXT,
            style=CitationStyle.CHICAGO,
            page_num=2,
        )
    ]
    bib = [
        Citation(
            raw_text="Williams, Eric. Capitalism and Slavery. Chapel Hill: University of North Carolina Press, 1944.",
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.CHICAGO,
            page_num=10,
            authors=["Williams, Eric"],
            year="1944",
            title="Capitalism and Slavery: A Historical Study",
        )
    ]
    res = linker.link(body, bib)
    assert len(res.links) == 1
    assert res.links[0].status == CitationMappingStatus.MATCHED
    assert len(res.unmatched_reference_ids) == 0


def test_vn_multi_author_access_year_fallback_linking() -> None:
    """CitationLinker should link multi-author Vietnamese full-name citations when the cited year is the access year."""
    linker = CitationLinker()
    body = [
        Citation(
            raw_text="(Lê Thị Thu Hà & Đào Kim Anh, 2026)",
            citation_type=CitationType.IN_TEXT,
            style=CitationStyle.APA,
            page_num=3,
        )
    ]
    bib = [
        Citation(
            raw_text="Lê Thị Thu Hà & Đào Kim Anh (01/8/2013). Bảo hộ tên miền theo pháp luật sở hữu trí tuệ.",
            citation_type=CitationType.REFERENCE_LIST,
            style=CitationStyle.APA,
            page_num=5,
            authors=["Lê Thị Thu Hà", "Đào Kim Anh"],
            year="2013",
            title="Bảo hộ tên miền theo pháp luật sở hữu trí tuệ",
        )
    ]
    res = linker.link(body, bib)
    assert len(res.links) == 1
    assert res.links[0].status == CitationMappingStatus.MATCHED
    assert len(res.unmatched_reference_ids) == 0
