"""Unit tests for TDTU reference entry parsing and corporate/Vietnamese author parsing (Mục 2.6.2)."""

import pytest

from integrity_checker.extraction.patterns.apa import APAFormat
from integrity_checker.matching.author_parser import parse_authors


class TestTDTUAuthorParser:
    """Tests for parse_authors with Vietnamese initials and corporate authors."""

    def test_vietnamese_single_author_with_d_bar_initial(self) -> None:
        authors = parse_authors("Đức, Đ. M.")
        assert len(authors) == 1
        assert authors[0].last_name == "đức"
        assert authors[0].initials == ["đ", "m"]

    def test_vietnamese_two_authors_three_initials(self) -> None:
        authors = parse_authors("Trâm, N. T. B., & Phượng, N. T. K.")
        assert len(authors) == 2
        assert authors[0].last_name == "trâm"
        assert authors[0].initials == ["n", "t", "b"]
        assert authors[1].last_name == "phượng"
        assert authors[1].initials == ["n", "t", "k"]

    def test_vietnamese_authors_with_va_separator(self) -> None:
        authors = parse_authors("Hùng, L. T. và Dũng, P. M.")
        assert len(authors) == 2
        assert authors[0].last_name == "hùng"
        assert authors[1].last_name == "dũng"

    @pytest.mark.parametrize(
        ("raw_corp", "expected_last_name"),
        [
            (
                "Department of Finance and Administration",
                "department of finance and administration",
            ),
            (
                "Bộ nông nghiệp & PTNT",
                "bộ nông nghiệp & ptnt",
            ),
            (
                "Reserve Bank of Australia.",
                "reserve bank of australia",
            ),
            (
                "Tổng cục thống kê",
                "tổng cục thống kê",
            ),
            (
                "World Health Organization",
                "world health organization",
            ),
            (
                "Ngân hàng Nhà nước Việt Nam",
                "ngân hàng nhà nước việt nam",
            ),
        ],
    )
    def test_corporate_authors_not_split_or_abbreviated(
        self, raw_corp: str, expected_last_name: str
    ) -> None:
        authors = parse_authors(raw_corp)
        assert len(authors) == 1
        assert authors[0].last_name == expected_last_name
        assert authors[0].initials == []


class TestTDTUAPAReferenceEntries:
    """Tests for all Mục 2.6.2 reference entry formats in tai_lieu_tham_khao_TDTU.md."""

    def setup_method(self) -> None:
        self.fmt = APAFormat()

    def test_book_english(self) -> None:
        raw = (
            "Kotler, P., & Lee, N. (2009). Up and out of poverty: The social marketing solution. "
            "New Jersey: Pearson Education, Inc."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["kotler", "lee"]
        assert c.year == "2009"
        assert c.title == "Up and out of poverty: The social marketing solution"
        assert c.venue == "New Jersey: Pearson Education, Inc"

    def test_book_corporate_author_english(self) -> None:
        raw = (
            "Department of Finance and Administration (2006). Delivering Australian Government "
            "services: Managing multiple channels. Canberra: Author."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert len(c.authors) == 1
        assert c.authors[0].last_name == "department of finance and administration"
        assert c.year == "2006"
        assert c.title == "Delivering Australian Government services: Managing multiple channels"
        assert c.venue == "Canberra: Author"

    def test_book_corporate_author_vietnamese(self) -> None:
        raw = (
            "Bộ nông nghiệp & PTNT (1996). Báo cáo tổng kết 5 năm (1992 – 1996) phát triển lúa lai. "
            "Hà Nội: NXB Nông nghiệp."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert len(c.authors) == 1
        assert c.authors[0].last_name == "bộ nông nghiệp & ptnt"
        assert c.year == "1996"
        assert c.title == "Báo cáo tổng kết 5 năm (1992 – 1996) phát triển lúa lai"
        assert c.venue == "Hà Nội: NXB Nông nghiệp"

    def test_book_chapter_with_editors_and_pages(self) -> None:
        raw = (
            "Aron, L., Botella, M., & Lubart, T. (2019). Culinary arts: Talent and their development. "
            "In R. F. Subotnik, P. Olszewski-Kubilius, & F. C. Worrell (Eds.), "
            "The psychology of high performance: Developing human potential into domain-specific talent "
            "(pp. 345–359). American Psychological Association."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["aron", "botella", "lubart"]
        assert c.year == "2019"
        assert c.title == "Culinary arts: Talent and their development"
        assert c.pages == "345–359"

    def test_conference_proceedings_paper(self) -> None:
        raw = (
            "Bergmann, S. (1993). Ecological theology. In J. H.aire (Ed.), "
            "Proceedings of the Revitalising dynamism Growth Seminar (pp. 29-43). "
            "Melbourne: Joint Board of Education."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["bergmann"]
        assert c.year == "1993"
        assert c.title == "Ecological theology"
        assert c.pages == "29-43"

    def test_journal_article_english(self) -> None:
        raw = (
            "Bartlett, R. P. (2009). Going private but staying public: Reexamining the effect of "
            "Sarbanes-Oxley on firms’ going-private decisions. "
            "The University of Chicago Law Review, 76(1), 7-44."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["bartlett"]
        assert c.year == "2009"
        assert c.venue == "The University of Chicago Law Review"
        assert c.volume == "76"
        assert c.issue == "1"
        assert c.pages == "7-44"

    def test_journal_article_vietnamese(self) -> None:
        raw = (
            "Đức, Đ. M. (2016). Một số đánh giá bước đầu về đầu tư của doanh nghiệp Việt Nam "
            "ra nước ngoài giai đoạn 2005 – 2015. Nghiên cứu Kinh tế, 456(5), 39-47."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["đức"]
        assert c.authors[0].initials == ["đ", "m"]
        assert c.year == "2016"
        assert c.venue == "Nghiên cứu Kinh tế"
        assert c.volume == "456"
        assert c.issue == "5"
        assert c.pages == "39-47"

    def test_journal_article_vietnamese_alphanumeric_issue(self) -> None:
        raw = (
            "Trâm, N. T. B., & Phượng, N. T. K. (2017). Phản ứng của giá cổ phiếu với thông tin "
            "trả cổ tức bằng tiền mặt tại Sở Giao dịch Chứng khoán Thành phố Hồ Chí Minh. "
            "Tạp chí Khoa học Đại học Mở Thành phố Hồ Chí Minh, 126(5D), 79–94."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["trâm", "phượng"]
        assert c.year == "2017"
        assert c.venue == "Tạp chí Khoa học Đại học Mở Thành phố Hồ Chí Minh"
        assert c.volume == "126"
        assert c.issue == "5D"
        assert c.pages == "79–94"

    def test_thesis_english(self) -> None:
        raw = (
            "May, B. (2007). A survey of radial velocities in the zodiacal dust cloud "
            "(Doctoral dissertation). University of Bristol, Bristol, UK."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["may"]
        assert c.year == "2007"
        assert c.title == "A survey of radial velocities in the zodiacal dust cloud (Doctoral dissertation)"
        assert c.venue == "University of Bristol, Bristol, UK"

    def test_thesis_vietnamese_with_comma_and_tp_hcm(self) -> None:
        raw = (
            "Trí, N. C. (2011). Nâng cao năng lực cạnh tranh của các doanh nghiệp du lịch "
            "thành phố Hồ Chí Minh đến năm 2020 (Luận án Tiến sĩ kinh tế), "
            "Trường Đại học Kinh tế Tp. HCM, Việt Nam."
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["trí"]
        assert c.year == "2011"
        assert c.title == (
            "Nâng cao năng lực cạnh tranh của các doanh nghiệp du lịch "
            "thành phố Hồ Chí Minh đến năm 2020 (Luận án Tiến sĩ kinh tế)"
        )
        assert c.venue == "Trường Đại học Kinh tế Tp. HCM, Việt Nam"

    def test_internet_reference_english_repairs_broken_url(self) -> None:
        raw = (
            "Reserve Bank of Australia. (2007). Statements on monetary policy. "
            "Retrieved March 21, 2011, from "
            "http://www.rba.gov.au/ PublicationsAndResearch/StatementsOnMonetaryPolicy/index.html"
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert len(c.authors) == 1
        assert c.authors[0].last_name == "reserve bank of australia"
        assert c.year == "2007"
        assert c.title == "Statements on monetary policy"
        assert c.volume is None
        assert c.url == (
            "http://www.rba.gov.au/PublicationsAndResearch/StatementsOnMonetaryPolicy/index.html"
        )

    def test_internet_reference_vietnamese(self) -> None:
        raw = (
            "Tô, T. (2015). Bàn về chính sách tiền tệ năm 2015. "
            "Truy cập 21/7/2016, từ "
            "http://kinhtevadubao.vn/chi-tiet/101-3591-ban-ve-chinh-sach-tien-te-nam-2015.html"
        )
        c = self.fmt.parse_reference_entry(raw)
        assert c is not None
        assert [a.last_name for a in c.authors] == ["tô"]
        assert c.year == "2015"
        assert c.title == "Bàn về chính sách tiền tệ năm 2015"
        assert c.volume is None
        assert c.url == (
            "http://kinhtevadubao.vn/chi-tiet/101-3591-ban-ve-chinh-sach-tien-te-nam-2015.html"
        )
