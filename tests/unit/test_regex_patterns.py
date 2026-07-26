"""Unit tests cho regex patterns."""

from __future__ import annotations

import re

from integrity_checker.extraction import get_all_patterns


def test_all_patterns_compile() -> None:
    """Mọi pattern phải compile được."""
    for p in get_all_patterns():
        compiled = re.compile(p.pattern)
        assert compiled is not None


def test_apa_intext_matches_3_forms() -> None:
    apa_intext = [p for p in get_all_patterns() if p.name == "apa_intext_parenthetical"][0]
    regex = re.compile(apa_intext.pattern)
    text = "(Smith, 2020) (Jones et al., 2019) (Brown and Clark, 2018)"
    matches = regex.findall(text)
    assert len(matches) >= 3


def test_doi_pattern_matches_real_doi() -> None:
    doi_p = [p for p in get_all_patterns() if p.name == "doi"][0]
    regex = re.compile(doi_p.pattern)
    assert regex.search("10.1038/nature14539")
    assert regex.search("10.48550/arXiv.1706.03762")
    assert regex.search("https://doi.org/10.18653/v1/N19-1423")  # URL with DOI
    assert not regex.search("just a random text")


def test_numeric_matches_brackets() -> None:
    p = [p for p in get_all_patterns() if p.name == "numeric_brackets"][0]
    regex = re.compile(p.pattern)
    assert regex.search("[1]") is not None
    assert regex.search("[1,2]") is not None
    assert regex.search("[1-5]") is not None