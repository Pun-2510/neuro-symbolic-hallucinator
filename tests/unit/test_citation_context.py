"""Unit tests cho việc trích xuất context (text bao quanh citation).

v1.16 — Document Inspector hiển thị "[No surrounding text extracted]" khi
citation không có context. Bộ test này khoá lại hành vi của:
  - _extract_citation_context: match bỏ qua xuống dòng / whitespace
  - _find_context_page: tôn trọng page_num, fallback sang title
  - _extract_occurrence_contexts: gom occurrence theo reference_id
  - _extract_reference_context: reference mượn context của occurrence
"""

from __future__ import annotations

from integrity_checker.extraction.base import Page
from integrity_checker.models.citation import Citation, CitationStyle, CitationType
from integrity_checker.pipeline.integrity_pipeline import IntegrityPipeline


def _pages(*texts: str) -> list[Page]:
    return [
        Page(page_num=i + 1, text=t, has_text_layer=True)
        for i, t in enumerate(texts)
    ]


def _citation(raw: str, **kw) -> Citation:
    return Citation(
        raw_text=raw,
        citation_type=kw.get("citation_type", CitationType.NUMERIC),
        style=CitationStyle.IEEE,
        page_num=kw.get("page_num"),
        title=kw.get("title"),
        authors=kw.get("authors"),
        year=kw.get("year"),
    )


def _link(reference_id: str):
    """Link tối giản — chỉ cần ``reference_id``."""

    class _L:
        def __init__(self, rid: str) -> None:
            self.reference_id = rid
            self.occurrence_id = "occ-0001"
            self.status = None
            self.confidence = 1.0
            self.evidence: dict = {}

    return _L(reference_id)


# --- _extract_citation_context ---


def test_context_matches_across_line_wrap() -> None:
    """PDF xuống dòng giữa citation — match phải bỏ qua newline."""
    page = "The model was proposed by Vaswani\net al. (2017) in the paper."
    ctx = IntegrityPipeline._extract_citation_context(
        "Vaswani et al. (2017)", page, window_chars=40
    )
    assert ctx is not None
    assert "proposed by" in ctx
    assert "in the paper" in ctx


def test_context_matches_across_double_space() -> None:
    page = "Prior work  showed  this effect clearly."
    ctx = IntegrityPipeline._extract_citation_context("Prior work", page, window_chars=30)
    assert ctx is not None
    assert "showed" in ctx


def test_context_is_none_when_citation_absent() -> None:
    assert IntegrityPipeline._extract_citation_context("[9]", "no match here") is None


def test_context_falls_back_to_title_needle() -> None:
    """Raw text không khớp verbatim — title làm chuẩn dự phòng."""
    page = "[10] B. Settles, Active Learning. Synthesis Lectures vol. 6, 2012."
    ctx = IntegrityPipeline._extract_citation_context(
        "Settles, B, Learning, Active (2012)",
        page,
        window_chars=60,
        fallback_needle="Active Learning",
    )
    assert ctx is not None
    assert "Synthesis Lectures" in ctx


def test_context_is_whitespace_normalized() -> None:
    page = "line one\nline two\nline three"
    ctx = IntegrityPipeline._extract_citation_context("line two", page, window_chars=40)
    assert ctx is not None
    assert "\n" not in ctx


# --- _find_context_page ---


def test_find_context_page_prefers_recorded_page_number() -> None:
    """Mọi ``[1]`` đều phải lấy đúng trang của nó, không phải trang đầu."""
    pages = _pages(
        "First page mentions [1] early on.",
        "Second page mentions [1] again here.",
    )
    cit = _citation("[1]", page_num=2)
    page = IntegrityPipeline._find_context_page(cit, pages)
    assert page is not None
    assert page.page_num == 2


def test_find_context_page_scans_when_page_number_missing() -> None:
    pages = _pages("nothing here", "the entry appears on this page")
    cit = _citation("the entry appears", page_num=0)
    page = IntegrityPipeline._find_context_page(cit, pages)
    assert page is not None
    assert page.page_num == 2


def test_find_context_page_falls_back_to_title() -> None:
    """Entry không xuất hiện verbatim — title vẫn dẫn tới đúng trang."""
    pages = _pages("intro", "[10] B. Settles, Active Learning. 2012.")
    cit = _citation("Settles, B, Learning, Active (2012)", page_num=0, title="Active Learning")
    page = IntegrityPipeline._find_context_page(cit, pages)
    assert page is not None
    assert page.page_num == 2


def test_find_context_page_returns_none_when_absent() -> None:
    pages = _pages("completely unrelated text")
    cit = _citation("[42]", page_num=0, title="Nothing Alike")
    assert IntegrityPipeline._find_context_page(cit, pages) is None


# --- _extract_occurrence_contexts ---


def test_occurrence_contexts_collected_per_page() -> None:
    pages = _pages(
        "Alpha study claims [1] that things work well.",
        "Beta study repeats [2] with other findings.",
    )
    c1 = _citation("[1]", page_num=1)
    c1.reference_id = "occ-0001"
    c2 = _citation("[2]", page_num=2)
    c2.reference_id = "occ-0002"
    links = {
        "occ-0001": [_link("ref-0001")],
        "occ-0002": [_link("ref-0002")],
    }
    by_ref = IntegrityPipeline._extract_occurrence_contexts([c1, c2], pages, links)
    assert c1.context and "Alpha study" in c1.context
    assert c2.context and "Beta study" in c2.context
    assert set(by_ref) == {"ref-0001", "ref-0002"}


def test_occurrence_contexts_cover_multi_citation_occurrence() -> None:
    """``[9, 10]`` trỏ tới hai reference — cả hai đều nhận context."""
    pages = _pages("A claim supported by [9, 10] in the literature.")
    c = _citation("[9, 10]", page_num=1)
    c.reference_id = "occ-0001"
    links = {"occ-0001": [_link("ref-0009"), _link("ref-0010")]}
    by_ref = IntegrityPipeline._extract_occurrence_contexts([c], pages, links)
    assert "ref-0009" in by_ref
    assert "ref-0010" in by_ref


# --- _extract_reference_context ---


def test_reference_context_borrows_from_occurrence() -> None:
    """Reference entry mượn câu trong body nơi nguồn được trích dẫn."""
    pages = _pages("The method of Smith et al. was applied [1] to new data.")
    occ = _citation("[1]", page_num=1)
    occ.reference_id = "occ-0001"
    links = {"occ-0001": [_link("ref-0001")]}
    by_ref = IntegrityPipeline._extract_occurrence_contexts([occ], pages, links)

    ref = _citation("Smith, J (2020) A paper title", citation_type=CitationType.REFERENCE_LIST)
    ref.reference_id = "ref-0001"
    ctx = IntegrityPipeline._extract_reference_context(ref, pages, by_ref)
    assert ctx is not None
    assert "method of Smith" in ctx


def test_reference_context_none_when_never_cited() -> None:
    """Entry không được trích dẫn ở đâu — không có context để mượn."""
    pages = _pages("Some unrelated body text.")
    ref = _citation("Nobody, N (1999) Uncited work", citation_type=CitationType.REFERENCE_LIST)
    ref.reference_id = "ref-0099"
    assert IntegrityPipeline._extract_reference_context(ref, pages, {}) is None
