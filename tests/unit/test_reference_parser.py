"""Unit tests cho extraction/reference_parser.py v1.2 — APA / IEEE / Vancouver."""

from __future__ import annotations

import pytest

from integrity_checker.extraction.base import Document, Page
from integrity_checker.extraction.reference_parser import (
    ReferenceListParser,
    _normalize_title,
)
from integrity_checker.extraction.text_preprocessor import TextPreprocessor
from integrity_checker.models.citation import CitationStyle, CitationType


def _doc_with_section(text: str) -> Document:
    pp = TextPreprocessor()
    return Document(
        file_path="x.pdf",
        num_pages=1,
        parser_used="test",
        pages=[Page(page_num=1, text=pp.normalize(f"References\n{text}"))],
    )


class TestNormalizeTitle:
    def test_lowercase(self):
        assert _normalize_title("Hello World") == "hello world"

    def test_strip_punctuation(self):
        assert _normalize_title("A study: of X!") == "a study of x"

    def test_collapse_spaces(self):
        assert _normalize_title("A   study   of   X") == "a study of x"

    def test_empty(self):
        assert _normalize_title("") == ""


class TestParseAPALike:
    def test_basic_apa(self):
        doc = _doc_with_section(
            "Smith, J. (2020). A study of X. Journal A, 10(2), 1-10. "
            "DOI: 10.1234/abc.001"
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        assert len(cits) == 1
        c = cits[0]
        assert c.style == CitationStyle.APA
        assert c.year == "2020"
        assert c.year_suffix is None
        assert c.title == "A study of X"
        assert c.title_normalized == "a study of x"
        assert c.doi == "10.1234/abc.001"
        assert [a.last_name for a in c.authors] == ["smith"]
        assert c.order_index == 1

    def test_apa_three_authors(self):
        doc = _doc_with_section(
            "LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. "
            "Nature, 521, 436-444. DOI: 10.1038/nature14539"
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        c = cits[0]
        assert [a.last_name for a in c.authors] == ["lecun", "bengio", "hinton"]
        assert c.year == "2015"

    def test_apa_year_with_suffix(self):
        doc = _doc_with_section(
            "Smith, J. (2024a). Recent advances. Journal A, 1, 1-5."
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        c = cits[0]
        assert c.year == "2024"
        assert c.year_suffix == "a"

    def test_apa_dutch_multi_word(self):
        doc = _doc_with_section(
            "van der Berg, J. (2020). A study. Journal A, 1, 1-10."
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        c = cits[0]
        assert [a.last_name for a in c.authors] == ["van der berg"]


class TestParseIEEELike:
    def test_basic_ieee(self):
        doc = _doc_with_section(
            '[1] Smith, J., "A study of X," Journal A, vol. 10, no. 2, '
            'pp. 1-10, 2020.'
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        assert len(cits) == 1
        c = cits[0]
        assert c.style == CitationStyle.IEEE
        assert c.numeric_index == 1
        assert c.year == "2020"
        assert c.title == "A study of X"
        assert [a.last_name for a in c.authors] == ["smith"]

    def test_ieee_three_authors(self):
        doc = _doc_with_section(
            '[2] LeCun, Y., Bengio, Y., & Hinton, G., "Deep learning," '
            'Nature, vol. 521, pp. 436-444, 2015.'
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        c = cits[0]
        assert c.numeric_index == 2
        assert [a.last_name for a in c.authors] == ["lecun", "bengio", "hinton"]
        assert c.title == "Deep learning"


class TestParseVancouver:
    def test_basic_vancouver(self):
        doc = _doc_with_section("Smith J. A study of X. Journal A. 2020;10(2):1-10.")
        cits = ReferenceListParser().parse_reference_section(doc)
        c = cits[0]
        assert c.style == CitationStyle.VANCOUVER
        assert c.year == "2020"
        assert [a.last_name for a in c.authors] == ["smith"]


class TestCitationTypeAndMetadata:
    @pytest.mark.parametrize("text,style", [
        ("Smith, J. (2020). Title. Journal A, 1, 1-10.", CitationStyle.APA),
        ('[1] Smith, J., "Title," Journal A, vol. 1, 2020.', CitationStyle.IEEE),
        ("Smith J. Title. Journal A. 2020;1:1-10.", CitationStyle.VANCOUVER),
    ])
    def test_all_returned_reference_list(self, text, style):
        doc = _doc_with_section(text)
        cits = ReferenceListParser().parse_reference_section(doc)
        assert cits[0].citation_type == CitationType.REFERENCE_LIST
        assert cits[0].style == style

    def test_no_section_no_citations(self):
        # Document không có "References" header → trả []
        pp = TextPreprocessor()
        doc = Document(
            file_path="x.pdf",
            num_pages=1,
            parser_used="t",
            pages=[Page(page_num=1, text="Body without refs section.")],
        )
        assert ReferenceListParser().parse_reference_section(doc) == []


class TestMultipleEntriesSplit:
    def test_ieee_separates_on_open_bracket(self):
        doc = _doc_with_section(
            '[1] Smith, J., "Title A," Journal A, vol. 1, 2020.\n'
            '[2] Doe, A., "Title B," Journal B, vol. 2, 2021.'
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        assert len(cits) == 2
        assert cits[0].numeric_index == 1
        assert cits[1].numeric_index == 2

    def test_apa_separates_lines(self):
        doc = _doc_with_section(
            "Smith, J. (2020). Title A. Journal A, 1, 1-10.\n"
            "Doe, A. (2021). Title B. Journal B, 2, 20-30."
        )
        cits = ReferenceListParser().parse_reference_section(doc)
        assert len(cits) == 2
        assert cits[0].title == "Title A"
        assert cits[1].title == "Title B"
        assert cits[0].order_index == 1
        assert cits[1].order_index == 2
