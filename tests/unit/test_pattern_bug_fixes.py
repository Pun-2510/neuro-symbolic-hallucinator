"""Tests for bug fixes in citation patterns (2026-09-29).

These tests verify that overly permissive patterns do not match
false positive citations.

Bug: TranThanhPhuoc_523H0002_523H0054.pdf returned 485 citations
instead of ~80 because:
  - mla/acs/ama patterns matched data and non-citation text
  - These formats were REMOVED from auto-registration in __init__.py

After fix: MLA, ACS, AMA removed from default registry.
Remaining formats: APA, IEEE, Numeric, Vancouver, Harvard, ACM, Nature, CSE, Chicago
"""

from __future__ import annotations

import pytest

from integrity_checker.extraction.patterns import (
    get_format,
    get_in_text_patterns,
)


class TestRemovedFormatsNotRegistered:
    """Tests verifying MLA, ACS, AMA are registered with safe patterns only."""

    def test_mla_registered_without_permissive_parenthetical(self):
        """MLA format should be registered without bare (Author) pattern."""
        mla = get_format("MLA")
        assert mla is not None
        pattern_names = [p.name for p in mla.in_text_patterns]
        assert "mla_intext_parenthetical_page" in pattern_names
        assert "mla_intext_parenthetical" not in pattern_names

    def test_acs_registered_without_parenthesized(self):
        """ACS format should be registered without bare (1) or comma-separated number patterns."""
        acs = get_format("ACS")
        assert acs is not None
        pattern_names = [p.name for p in acs.in_text_patterns]
        assert "acs_superscript" in pattern_names
        assert "acs_parenthesized" not in pattern_names
        assert "acs_comma_separated" not in pattern_names

    def test_ama_registered_without_parenthesized(self):
        """AMA format should be registered without bare (1) or comma-separated number patterns."""
        ama = get_format("AMA")
        assert ama is not None
        pattern_names = [p.name for p in ama.in_text_patterns]
        assert "ama_superscript" in pattern_names
        assert "ama_parenthesized" not in pattern_names
        assert "ama_comma_separated" not in pattern_names


class TestRemainingFormatsWork:
    """Tests verifying remaining formats still work correctly."""

    def test_ieee_still_registered(self):
        """IEEE format should still be registered."""
        ieee = get_format("IEEE")
        assert ieee is not None
        pattern_names = [p.name for p in ieee.in_text_patterns]
        assert "ieee_numeric" in pattern_names

    def test_apa_still_registered(self):
        """APA format should still be registered."""
        apa = get_format("APA")
        assert apa is not None
        pattern_names = [p.name for p in apa.in_text_patterns]
        assert "apa_intext_parenthetical" in pattern_names
        assert "apa_intext_narrative" in pattern_names

    def test_vancouver_still_registered(self):
        """Vancouver format should still be registered."""
        vanc = get_format("Vancouver")
        assert vanc is not None
        pattern_names = [p.name for p in vanc.in_text_patterns]
        assert "vancouver_numeric" in pattern_names

    def test_harvard_still_registered(self):
        """Harvard format should still be registered."""
        harv = get_format("Harvard")
        assert harv is not None
        pattern_names = [p.name for p in harv.in_text_patterns]
        assert "harvard_parenthetical_comma" in pattern_names

    def test_nature_still_registered(self):
        """Nature format should still be registered."""
        nature = get_format("Nature")
        assert nature is not None
        pattern_names = [p.name for p in nature.in_text_patterns]
        assert "nature_bracketed" in pattern_names

    def test_cse_still_registered(self):
        """CSE format should still be registered."""
        cse = get_format("CSE")
        assert cse is not None
        pattern_names = [p.name for p in cse.in_text_patterns]
        assert "cse_superscript" in pattern_names
        assert "cse_bracketed" in pattern_names
        # cse_parenthesized should be removed from in_text_patterns
        assert "cse_parenthesized" not in pattern_names

    def test_chicago_still_registered(self):
        """Chicago format should still be registered."""
        chi = get_format("Chicago")
        assert chi is not None

    def test_acm_still_registered(self):
        """ACM format should still be registered."""
        acm = get_format("ACM")
        assert acm is not None


class TestCSERemovedParensFromInText:
    """Tests verifying CSE parenthesized pattern was removed from in_text."""

    def test_cse_no_parenthesized_in_intext(self):
        """CSE in_text_patterns should NOT include parenthesized."""
        cse = get_format("CSE")
        pattern_names = [p.name for p in cse.in_text_patterns]
        assert "cse_parenthesized" not in pattern_names, (
            "cse_parenthesized should be removed from in_text_patterns"
        )

    def test_cse_still_has_superscript_and_bracketed(self):
        """CSE should still have legitimate in-text patterns."""
        cse = get_format("CSE")
        pattern_names = [p.name for p in cse.in_text_patterns]
        assert "cse_superscript" in pattern_names
        assert "cse_bracketed" in pattern_names
        assert "cse_nameyear_parenthetical" in pattern_names
        assert "cse_nameyear_parenthetical_nocomma" in pattern_names

    def test_cse_nameyear_still_works(self):
        """CSE Name-Year patterns should still function."""
        cse = get_format("CSE")
        patterns = cse.in_text_patterns
        nameyear = next(p for p in patterns if p.name == "cse_nameyear_parenthetical")

        # Should match legitimate CSE Name-Year citations
        assert nameyear.search("(Smith, 2020)") is not None
        assert nameyear.search("(Smith et al., 2019)") is not None
        assert nameyear.search("(Vaswani, 2017)") is not None


class TestPatternCountReduction:
    """Verify false-positive patterns remain excluded while all 11 formats are registered."""

    def test_in_text_pattern_count(self):
        """Total in_text_patterns should be 30 across all 11 registered formats."""
        patterns = get_in_text_patterns()
        assert len(patterns) == 30, f"Expected 30 patterns, got {len(patterns)}"

    def test_no_permissive_patterns_in_registry(self):
        """No overly permissive parenthesized/comma-number patterns should appear in registry."""
        patterns = get_in_text_patterns()
        pattern_names = [p.name for p in patterns]

        forbidden_patterns = [
            "mla_intext_parenthetical",
            "acs_comma_separated",
            "acs_parenthesized",
            "ama_comma_separated",
            "ama_parenthesized",
            "cse_parenthesized",  # removed from in_text
        ]
        for name in forbidden_patterns:
            assert name not in pattern_names, f"{name} should not be in in_text_patterns"

    def test_registered_format_count(self):
        """Should have all 11 citation formats registered."""
        from integrity_checker.extraction.patterns import get_all_formats

        formats = get_all_formats()
        format_names = [f.name for f in formats]
        assert len(formats) == 11, f"Expected 11 formats, got {len(formats)}: {format_names}"
        expected = {
            "APA", "IEEE", "Vancouver", "Chicago", "Harvard",
            "ACM", "Nature", "CSE", "MLA", "ACS", "AMA",
        }
        assert set(format_names) == expected


class TestIEEEBracketsStillWork:
    """Verify IEEE/Nature bracketed citations still work correctly."""

    def test_ieee_numeric_single(self):
        """IEEE numeric [N] should still work."""
        patterns = get_in_text_patterns()
        ieee = next(p for p in patterns if p.name == "ieee_numeric")
        assert ieee.search("[1]") is not None
        assert ieee.search("[24]") is not None
        assert ieee.search("[1,2]") is not None
        assert ieee.search("[1, 2, 3]") is not None
        assert ieee.search("[1-5]") is not None

    def test_nature_bracketed_single(self):
        """Nature bracketed [N] should still work."""
        patterns = get_in_text_patterns()
        nat = next(p for p in patterns if p.name == "nature_bracketed")
        assert nat.search("[1]") is not None
        assert nat.search("[24]") is not None
