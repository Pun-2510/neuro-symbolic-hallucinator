"""Unit tests for TDTU Vietnamese legal document references, linking, and checking (Mục 2.6.1 & 2.6.3)."""

import pytest

from integrity_checker.extraction.base import Document, Page
from integrity_checker.extraction.citation_extractor import CitationExtractor
from integrity_checker.extraction.patterns.apa import (
    APAFormat,
    is_vn_legal_reference,
    parse_vn_legal_reference,
)
from integrity_checker.extraction.reference_parser import ReferenceListParser, _is_fake_entry
from integrity_checker.linking.citation_linker import CitationLinker
from integrity_checker.linking.statuses import CitationMappingStatus
from integrity_checker.logic.neuro_symbolic_checker import NeuroSymbolicChecker
from integrity_checker.models.source import SourceResult
from integrity_checker.models.validation import ValidationLabel


class TestTDTULegalDocumentParsing:
    """Tests for parsing Vietnamese legal documents per TDTU §2.6.1."""

    def setup_method(self) -> None:
        self.fmt = APAFormat()
        self.ref_parser = ReferenceListParser()

    def test_constitution_entry_not_filtered_as_fake(self) -> None:
        raw = "1. Hiến pháp 2013."
        assert is_vn_legal_reference(raw) is True
        assert _is_fake_entry(raw) is False

        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert c.matched_pattern == "vn_legal_document"
        assert c.year == "2013"
        assert c.title == "Hiến pháp 2013"
        assert c.venue == "Quốc hội"
        assert {a.last_name for a in c.authors} >= {"hiến pháp", "quốc hội"}

    def test_constitution_full_name_variant(self) -> None:
        raw = "Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam năm 2013."
        c = parse_vn_legal_reference(raw)
        assert c is not None
        assert c.year == "2013"
        assert c.matched_pattern == "vn_legal_document"

    def test_law_entry_luat_doanh_nghiep(self) -> None:
        raw = "2. Luật Doanh nghiệp (Luật số 68/2014/QH13) ngày 26/12/2014."
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert c.matched_pattern == "vn_legal_document"
        assert c.year == "2014"
        assert c.title == "Luật Doanh nghiệp (Luật số 68/2014/QH13) ngày 26/12/2014"
        assert c.venue == "Quốc hội"
        author_names = {a.last_name for a in c.authors}
        assert "luật doanh nghiệp" in author_names
        assert "quốc hội" in author_names
        assert "luật số 68/2014/qh13" in author_names

    def test_code_entry_bo_luat_dan_su(self) -> None:
        raw = "Bộ luật Dân sự (Luật số 91/2015/QH13) ngày 24/11/2015."
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert c.matched_pattern == "vn_legal_document"
        assert c.year == "2015"
        assert c.title == "Bộ luật Dân sự (Luật số 91/2015/QH13) ngày 24/11/2015"
        author_names = {a.last_name for a in c.authors}
        assert "bộ luật dân sự" in author_names
        assert "quốc hội" in author_names

    def test_sublaw_nghi_dinh_entry(self) -> None:
        raw = (
            "3. Nghị định số 23/2015/NĐ-CP của Chính phủ ngày 16/02/2015 về cấp bản sao "
            "từ sổ gốc, chứng thực bản sao từ bản chính, chứng thực chữ ký và chứng thực "
            "hợp đồng, giao dịch."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert c.matched_pattern == "vn_legal_document"
        assert c.year == "2015"
        assert c.venue == "Chính phủ"
        author_names = {a.last_name for a in c.authors}
        assert "chính phủ" in author_names
        assert "nghị định số 23/2015/nđ-cp" in author_names
        assert "nghị định 23/2015/nđ-cp" in author_names

    @pytest.mark.parametrize(
        ("raw", "expected_year", "expected_venue"),
        [
            (
                "Thông tư số 200/2014/TT-BTC của Bộ Tài chính ngày 22/12/2014 hướng dẫn Chế độ kế toán Doanh nghiệp.",
                "2014",
                "Bộ Tài chính",
            ),
            (
                "Quyết định số 167/2008/QĐ-TTg của Thủ tướng Chính phủ ngày 12/12/2008 về chính sách hỗ trợ hộ nghèo về nhà ở.",
                "2008",
                "Thủ tướng Chính phủ",
            ),
            (
                "Nghị quyết số 43/2022/QH15 của Quốc hội ngày 11/01/2022 về chính sách tài khóa, tiền tệ hỗ trợ Chương trình phục hồi.",
                "2022",
                "Quốc hội",
            ),
        ],
    )
    def test_sublaw_other_types(
        self, raw: str, expected_year: str, expected_venue: str
    ) -> None:
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert c.matched_pattern == "vn_legal_document"
        assert c.year == expected_year
        assert c.venue == expected_venue


class TestTDTULegalDocumentLinkingAndChecking:
    """Tests for in-text extraction, linking, and NeuroSymbolicChecker classification of legal documents."""

    def test_intext_extraction_and_linking_to_legal_references(self) -> None:
        extractor = CitationExtractor()
        ref_parser = ReferenceListParser(extractor=extractor)
        linker = CitationLinker()

        body_text = (
            "Quyền tự do kinh doanh được hiến định trong (Hiến pháp, 2013). "
            "Theo Luật Doanh nghiệp (2014) và (Bộ luật Dân sự, 2015), doanh nghiệp "
            "phải tuân thủ quy định về chứng thực tại (Nghị định số 23/2015/NĐ-CP, 2015)."
        )
        ref_text = (
            "TÀI LIỆU THAM KHẢO\n"
            "1. Hiến pháp 2013.\n"
            "2. Luật Doanh nghiệp (Luật số 68/2014/QH13) ngày 26/12/2014.\n"
            "3. Bộ luật Dân sự (Luật số 91/2015/QH13) ngày 24/11/2015.\n"
            "4. Nghị định số 23/2015/NĐ-CP của Chính phủ ngày 16/02/2015 về cấp bản sao từ sổ gốc, "
            "chứng thực bản sao từ bản chính, chứng thực chữ ký và chứng thực hợp đồng, giao dịch.\n"
        )
        doc = Document(
            file_path="test_legal.pdf",
            num_pages=2,
            pages=[
                Page(page_num=1, text=body_text),
                Page(page_num=2, text=ref_text),
            ],
        )

        in_text_cits = extractor.extract_from_document(doc)
        bib_cits = ref_parser.parse_reference_section(doc)

        assert len(bib_cits) == 4
        assert len(in_text_cits) == 4

        report = linker.link(in_text_cits, bib_cits)
        matched_links = [
            lnk for lnk in report.links if lnk.status == CitationMappingStatus.MATCHED
        ]
        assert len(matched_links) == 4
        assert len(report.unmatched_in_text) == 0
        assert len(report.unmatched_reference_ids) == 0

    def test_neuro_symbolic_checker_classifies_legal_document_as_resource(self) -> None:
        fmt = APAFormat()
        checker = NeuroSymbolicChecker(enable_content_alignment=False)

        for raw in [
            "1. Hiến pháp 2013.",
            "2. Luật Doanh nghiệp (Luật số 68/2014/QH13) ngày 26/12/2014.",
            "3. Nghị định số 23/2015/NĐ-CP của Chính phủ ngày 16/02/2015 về cấp bản sao từ sổ gốc.",
        ]:
            cit = fmt.parse_reference_entry(raw)
            assert cit is not None
            empty_source = SourceResult(citation_raw=raw, candidates=[])
            verdict = checker.check(cit, empty_source)
            assert verdict.label == ValidationLabel.RESOURCE
            assert "R-LEGAL-DOCUMENT" in verdict.triggered_rules
