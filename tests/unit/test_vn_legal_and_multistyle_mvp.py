"""Unit and regression tests for Vietnamese Legal & Multi-Style MVP improvements:
- Agency-first Vietnamese legal references (Quốc hội, Chính phủ, Bộ..., Tòa án nhân dân...)
- Multi-year Hiến pháp and law names without 'năm'
- Sequential dot/paren-numbered bibliography splitting (including standalone '1.\\n' lines and hybrid TDTU lists)
- Vietnamese traditional humanities/law entries (year at end or URL + access date)
- Reference-guided Vietnamese legal in-text citations and flattened superscript numeric citations
"""

from __future__ import annotations

from integrity_checker.extraction.base import Document, Page
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.extraction.document_parser import DocumentParser
from integrity_checker.extraction.patterns.apa import (
    is_vn_legal_reference,
    parse_vn_legal_reference,
)
from integrity_checker.extraction.reference_parser import ReferenceListParser
from integrity_checker.extraction.section_segmenter import SectionSegmenter, SectionType
from integrity_checker.linking.citation_linker import CitationLinker
from integrity_checker.linking.statuses import CitationMappingStatus


def test_agency_first_vn_legal_references() -> None:
    samples = [
        (
            "1. Quốc hội (2020), Luật Doanh nghiệp số 59/2020/QH14 ngày 17/6/2020.",
            "2020",
            "Quốc hội",
            1,
        ),
        (
            "2. Chính phủ (2025). Nghị định số 55/2025/NĐ-CP ngày 01/3/2025 quy định chức năng, nhiệm vụ của Bộ Khoa học và Công nghệ.",
            "2025",
            "Chính phủ",
            2,
        ),
        (
            "3. Bộ Chính trị (2024). Nghị quyết số 57-NQ/TW ngày 22/12/2024 về đột phá phát triển khoa học, công nghệ.",
            "2024",
            "Bộ Chính trị",
            3,
        ),
        (
            "4. Tòa án nhân dân cấp cao tại TP. Hồ Chí Minh (2022). Bản án số 39/2022/KDTM-PT ngày 18/7/2022.",
            "2022",
            "Tòa án nhân dân cấp cao tại TP. Hồ Chí Minh",
            4,
        ),
        (
            "5. Hiến pháp năm 1946, 1959, 1980, 1992, 2013.",
            "2013",
            "Quốc hội",
            5,
        ),
    ]
    for raw, exp_year, exp_venue, exp_idx in samples:
        assert is_vn_legal_reference(raw), f"Expected legal reference for: {raw}"
        cit = parse_vn_legal_reference(raw)
        assert cit is not None
        assert cit.matched_pattern == "vn_legal_document"
        assert cit.year == exp_year
        assert cit.venue == exp_venue
        assert cit.numeric_index == exp_idx


def test_split_sequential_dot_numbered_with_standalone_numbers() -> None:
    bib_text = (
        "References\n"
        "1.\n"
        "Friedel, C.; Crafts, J. M. J. Chem. Soc. 1877, 32, 725–791. doi:10.1039/JS8773200725\n"
        "2.\n"
        "Yamauchi, T.; Hattori, K.; Mizutaki, S. Bull. Chem. Soc. Jpn. 1986, 59, 3617–3620.\n"
        "3.\n"
        "Tsuchimoto, T.; Tobita, K. Synlett 1996, 557–559.\n"
    )
    parser = ReferenceListParser()
    entries = parser._split_entries(bib_text)
    assert len(entries) == 3
    assert entries[0].startswith("1. Friedel")
    assert entries[1].startswith("2. Yamauchi")
    assert entries[2].startswith("3. Tsuchimoto")


def test_vn_traditional_entry_parsing() -> None:
    parser = ReferenceListParser()
    c1 = parser._parse_entry(
        "[1] Đỗ Văn Đại, Những vấn đề chung của pháp luật dân sự Việt Nam, Nxb. Hồng Đức, 2023.",
        order_index=1,
        page_num=5,
    )
    assert c1 is not None
    assert c1.matched_pattern == "vn_traditional_entry"
    assert c1.numeric_index == 1
    assert c1.year == "2023"
    assert "Những vấn đề chung" in (c1.title or "")

    c2 = parser._parse_entry(
        '[2] Trương Đắc Linh và Nguyễn Mạnh Hùng, “Giới thiệu Hiến pháp mới”, Tạp chí Khoa học Pháp lý, 2013.',
        order_index=2,
        page_num=5,
    )
    assert c2 is not None
    assert c2.matched_pattern == "vn_traditional_entry"
    assert c2.numeric_index == 2
    assert c2.year == "2013"
    assert c2.title == "Giới thiệu Hiến pháp mới"


def test_midpage_bibliography_segmentation_and_pre_header_body() -> None:
    seg = SectionSegmenter()
    doc = Document(
        file_path="test.pdf",
        num_pages=2,
        pages=[
            Page(page_num=1, text="Mở đầu báo cáo nghiên cứu pháp luật doanh nghiệp (Nguyễn, 2020).", has_text_layer=True),
            Page(
                page_num=2,
                text=(
                    "Kết luận chung về hoàn thiện Luật Doanh nghiệp năm 2020 và Nghị định số 01/2021/NĐ-CP.\n"
                    "TÀI LIỆU THAM KHẢO\n"
                    "1. Luật Doanh nghiệp (Luật số 59/2020/QH14) ngày 17/06/2020 của Quốc hội.\n"
                    "2. Nghị định số 01/2021/NĐ-CP ngày 04/01/2021 của Chính phủ về đăng ký doanh nghiệp.\n"
                    "3. Nguyễn, V. A. (2020). Pháp luật doanh nghiệp Việt Nam. NXB Tư pháp."
                ),
                has_text_layer=True,
            ),
        ],
    )
    sections = seg.segment(doc)
    bib_sec = next(s for s in sections if s.section_type == SectionType.BIBLIOGRAPHY)
    assert bib_sec.start_page == 2
    assert bib_sec.text.startswith("TÀI LIỆU THAM KHẢO")
    assert "Kết luận chung" in bib_sec.metadata.get("pre_header_body_text", "")

    dp = DocumentParser()
    parsed = dp._merge(doc, None)
    linker = CitationLinker()
    res = linker.link(parsed.body_citations, parsed.references)
    assert len(parsed.references) == 3
    assert len(res.unmatched_reference_ids) == 0
    assert all(r.mapping_status == CitationMappingStatus.MATCHED.value for r in parsed.references)


def test_attached_superscript_numeric_extraction() -> None:
    doc = Document(
        file_path="nature_sample.pdf",
        num_pages=2,
        pages=[
            Page(
                page_num=1,
                text=(
                    "Signaling pathways regulate cell motility1–2 and inhibit tumor invasion3. "
                    "Higher expression occurs in a cell-autonomous manner1,3."
                ),
                has_text_layer=True,
            ),
            Page(
                page_num=2,
                text=(
                    "References\n"
                    "1. Oishi, I. et al. Receptor tyrosine kinase signaling. Genes Cells 8, 645–654 (2003).\n"
                    "2. Nishita, M. et al. Filopodia formation in cell migration. J. Cell Biol. 175, 555–562 (2006).\n"
                    "3. Nomachi, A. et al. Tumor invasiveness pathways. Nature 450, 100–105 (2008)."
                ),
                has_text_layer=True,
            ),
        ],
    )
    dp = DocumentParser()
    parsed = dp._merge(doc, None)
    linker = CitationLinker()
    linker.link(parsed.body_citations, parsed.references)
    assert len(parsed.references) == 3
    assert all(r.mapping_status == CitationMappingStatus.MATCHED.value for r in parsed.references)


def test_non_citation_parenthetical_filters() -> None:
    ext = CitationExtractor()
    doc = Document(
        file_path="filter_sample.pdf",
        num_pages=1,
        pages=[
            Page(
                page_num=1,
                text=(
                    "(Received: 29/07/2025; Revised: 08/08/2025; Accepted: 29/08/2025) "
                    "See reaction (Scheme 1), (Compound 2), and emissions (Scope 1, 2, 3)."
                ),
                has_text_layer=True,
            ),
        ],
    )
    cits = ext.extract_from_document(doc)
    assert cits == []
