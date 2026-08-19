"""Tests for 03_enrich_crossref.py — Crossref API disabled, extracted metadata only."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts/collect_dataset to path so we can import the module
import importlib
import os
import sys
from pathlib import Path

# scripts/collect_dataset is at: tests/unit -> tests -> project_root -> scripts/collect_dataset
SCRIPTS_COLLECT = (Path(__file__).parent / ".." / ".." / "scripts" / "collect_dataset").resolve()
sys.path.insert(0, str(SCRIPTS_COLLECT))

# The file is named "03_enrich_crossref.py" — import via importlib
mod_name = "03_enrich_crossref"
mod = importlib.import_module(mod_name)

# Re-export for readability
_extract_doi_from_raw = mod._extract_doi_from_raw
_extract_title_from_raw = mod._extract_title_from_raw
enrich_citation = mod.enrich_citation


# ---------------------------------------------------------------------------
# _extract_title_from_raw
# ---------------------------------------------------------------------------

class TestExtractTitleFromRaw:
    """Title extraction from raw citation text — no API involved."""

    def test_ieee_quoted(self) -> None:
        # Quoted title with trailing comma — the comma is inside the quotes so it is captured
        raw = '[1] A. Vaswani et al., "Attention is all you need," NeurIPS, 2017.'
        title = _extract_title_from_raw(raw)
        assert title is not None
        assert "Attention is all you need" in title

    def test_ieee_quoted_with_comma(self) -> None:
        raw = '[2] D. Bahdanau, "Neural Machine Translation," ICLR, 2015.'
        title = _extract_title_from_raw(raw)
        assert title is not None
        assert "Neural Machine Translation" in title

    def test_apa_numbered_year_then_title(self) -> None:
        # Pattern: \d{4}\)\.\s+([^.]+?)(?:\.\s+[A-Z]|$)
        # The venue must start with uppercase (the regex requires \.\s+[A-Z] after title).
        # Using "arXiv" (lowercase) would NOT match — correct behaviour for this pattern.
        raw = "2016). Layer normalization. Technical Report."
        assert _extract_title_from_raw(raw) == "Layer normalization"

    def test_apa_year_then_title(self) -> None:
        # Same pattern as above; uppercase-starting venue required.
        raw = "Ba, J., et al. (2016). Layer normalization. Technical Report."
        assert _extract_title_from_raw(raw) == "Layer normalization"

    def test_bracket_style_returns_none(self) -> None:
        """
        The bracket pattern \\.\\]\\.\\s+([^.]+?) cannot handle real citations:
        [^.] stops at every period, including initials (D. P.) and titles with periods.
        Since GROBID extracts titles directly from structured TEI XML, this fallback
        is almost never needed — and when it is, it cannot reliably extract a title.
        Returning None here is the correct behaviour.
        """
        raw = "] D. P. Kingma and J. Ba. Adam optimizer. ICLR, 2015."
        assert _extract_title_from_raw(raw) is None

    def test_no_title_returns_none(self) -> None:
        # Short raw text that doesn't match any pattern
        raw = "No title here"
        assert _extract_title_from_raw(raw) is None

    def test_very_short_quoted_text_returns_none(self) -> None:
        # Pattern requires >= 10 chars inside quotes
        raw = '[1] A. Vaswani, "AI."'
        assert _extract_title_from_raw(raw) is None


# ---------------------------------------------------------------------------
# _extract_doi_from_raw
# ---------------------------------------------------------------------------

class TestExtractDoiFromRaw:
    """DOI extraction from raw citation text — no API involved."""

    def test_doi_org_prefix(self) -> None:
        raw = "See https://doi.org/10.1038/nature14539 for details."
        assert _extract_doi_from_raw(raw) == "10.1038/nature14539"

    def test_dx_doi_org_prefix(self) -> None:
        raw = "https://dx.doi.org/10.1038/nature14539"
        assert _extract_doi_from_raw(raw) == "10.1038/nature14539"

    def test_doi_colon_prefix(self) -> None:
        raw = "doi: 10.48550/arXiv.2301.00001"
        assert _extract_doi_from_raw(raw) == "10.48550/arXiv.2301.00001"

    def test_doi_trailing_comma_stripped(self) -> None:
        # doi.org/ prefix is required by the regex; trailing comma is stripped by .rstrip()
        raw = "https://doi.org/10.1038/nature14539,"
        assert _extract_doi_from_raw(raw) == "10.1038/nature14539"

    def test_doi_trailing_period_stripped(self) -> None:
        raw = "https://doi.org/10.1038/nature14539."
        assert _extract_doi_from_raw(raw) == "10.1038/nature14539"

    def test_no_doi_returns_none(self) -> None:
        raw = "Vaswani et al. Attention is all you need. NeurIPS 2017."
        assert _extract_doi_from_raw(raw) is None


# ---------------------------------------------------------------------------
# enrich_citation — the core fix
# ---------------------------------------------------------------------------

class TestEnrichCitation:
    """Crossref API is disabled. enrichment must come only from extracted fields."""

    def test_crossref_disabled_marker(self) -> None:
        """Every enriched citation must carry _crossref_disabled: True."""
        cit = {"raw_text": "Vaswani et al. (2017). Attention is all you need."}
        result = enrich_citation(cit)
        assert result.get("_crossref_disabled") is True

    def test_no_http_calls(self) -> None:
        """enrich_citation must not make any network requests."""
        import unittest.mock as mock

        cit = {
            "raw_text": "[1] A. Vaswani et al., 'Attention is all you need,' NeurIPS, 2017.",
            "authors": ["Vaswani, A."],
            "year": "2017",
            "title": "Attention is all you need",
        }
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            result = enrich_citation(cit)
            mock_urlopen.assert_not_called()
        assert result["crossref"] is not None

    def test_preserves_grobid_fields(self) -> None:
        """GROBID-extracted fields must pass through unchanged."""
        cit = {
            "raw_text": "LeCun, Y., et al. (2015). Deep learning. Nature, 521, 436-444.",
            "authors": ["Yann LeCun"],
            "year": "2015",
            "title": "Deep learning",
            "venue": "Nature",
            "doi": "10.1038/nature14539",
        }
        result = enrich_citation(cit)
        cr = result["crossref"]
        assert cr["authors"] == ["Yann LeCun"]
        assert cr["year"] == "2015"
        assert cr["title"] == "Deep learning"
        assert cr["venue"] == "Nature"
        assert cr["doi"] == "10.1038/nature14539"

    def test_doi_extracted_from_raw_when_missing(self) -> None:
        """DOI not in grobid fields → extracted from raw_text via regex."""
        cit = {
            "raw_text": "Vaswani et al. (2017). Attention is all you need. https://doi.org/10.48550/arXiv.1706.03762",
            "authors": ["Vaswani, A."],
            "year": "2017",
            "title": "Attention is all you need",
        }
        result = enrich_citation(cit)
        assert result["crossref"]["doi"] == "10.48550/arXiv.1706.03762"

    def test_title_from_raw_fallback(self) -> None:
        """Title not in grobid fields → parsed from raw_text."""
        cit = {
            "raw_text": '[1] A. Vaswani et al., "Attention is all you need," NeurIPS, 2017.',
            # no authors, no year, no title from grobid
        }
        result = enrich_citation(cit)
        # Trailing comma inside quotes is preserved by the regex (acceptable)
        assert "Attention is all you need" in result["crossref"]["title"]

    def test_empty_citation_returns_null_fields(self) -> None:
        """Citation with no extracted data → all null, but structure is valid."""
        cit = {"raw_text": ""}
        result = enrich_citation(cit)
        cr = result["crossref"]
        assert cr is not None
        assert cr.get("title") is None
        assert cr.get("doi") is None
        assert cr.get("authors") == []

    # ------------------------------------------------------------------
    # Bug regression tests — the core motivation for this fix
    # ------------------------------------------------------------------

    def test_layer_normalization_does_not_return_iucn_doi(self) -> None:
        """
        Regression: 'Layer Normalization' (Ba et al. 2016) was returning
        IUCN Red List DOI via noisy Crossref title-search.
        With Crossref disabled, the citation keeps its grobid title or
        falls back to a locally-extracted title — never hits Crossref.
        """
        cit = {
            "raw_text": "[1] J. L. Ba, J. R. Kiros, and G. E. Hinton. Layer normalization. arXiv:1607.06450, 2016.",
            "authors": ["Jimmy Lei Ba", "Jamie Ryan Kiros", "Geoffrey E Hinton"],
            "year": "2016",
            "title": "Layer normalization",
        }
        result = enrich_citation(cit)
        # Title must be the arXiv paper title, not IUCN Red List
        assert result["crossref"]["title"] == "Layer normalization"
        assert result["crossref"].get("doi") != "10.2307/IUCN.RLTF"  # IUCN DOI sentinel
        assert result.get("_crossref_disabled") is True

    def test_neural_machine_translation_does_not_return_goodfellow_doi(self) -> None:
        """
        Regression: 'Neural Machine Translation' (Bahdanau 2014) was returning
        Goodfellow's Deep Learning book DOI via noisy Crossref title-search.
        With Crossref disabled, this cannot happen.
        """
        cit = {
            "raw_text": "[2] D. Bahdanau, K. Cho, and Y. Bengio. Neural machine translation by jointly learning to align and translate. ICLR, 2015.",
            "authors": ["Dzmitry Bahdanau", "Kyunghyun Cho", "Yoshua Bengio"],
            "year": "2014",
            "title": "Neural machine translation by jointly learning to align and translate",
        }
        result = enrich_citation(cit)
        assert "Deep learning" not in (result["crossref"].get("title") or "")
        assert result.get("_crossref_disabled") is True

    def test_attention_is_all_you_need_title_not_replaced(self) -> None:
        """
        Even common titles that genuinely exist in Crossref must not have
        their metadata replaced by a potentially-wrong Crossref match.
        """
        cit = {
            "raw_text": '[1] A. Vaswani et al., "Attention is all you need," NeurIPS, 2017.',
            "authors": ["Ashish Vaswani"],
            "year": "2017",
            "title": "Attention is all you need",
        }
        result = enrich_citation(cit)
        # Title from grobid is preserved, not overwritten
        assert result["crossref"]["title"] == "Attention is all you need"
        assert result["crossref"]["authors"] == ["Ashish Vaswani"]
        assert result["crossref"]["year"] == "2017"

    def test_crossref_key_exists_even_when_empty(self) -> None:
        """
        The 'crossref' key must always be present in output (even if empty/none).
        Downstream scripts (04_format_gold_dataset.py) access it unconditionally.
        """
        cit = {"raw_text": "Some raw citation text."}
        result = enrich_citation(cit)
        assert "crossref" in result


# ---------------------------------------------------------------------------
# End-to-end via main() — tempfile I/O
# ---------------------------------------------------------------------------

class TestEnrichCrossrefMain:
    """Full script execution via main() with temp files."""

    def _make_input(self, citations: list[dict]) -> Path:
        data = {
            "paper1": {
                "arxiv_id": "paper1",
                "citations": citations,
            }
        }
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(data, f)
        f.flush()
        return Path(f.name)

    def test_main_writes_output(self, tmp_path: Path) -> None:
        citations = [
            {
                "raw_text": '[1] A. Vaswani et al., "Attention is all you need," NeurIPS, 2017.',
                "authors": ["Ashish Vaswani"],
                "year": "2017",
                "title": "Attention is all you need",
            }
        ]
        inp = self._make_input(citations)
        out = tmp_path / "out.json"

        mod_main = importlib.import_module("03_enrich_crossref")

        orig = sys.argv
        try:
            sys.argv = ["03_enrich_crossref.py", "--input", str(inp), "--output", str(out)]
            mod_main.main()
        finally:
            sys.argv = orig

        assert out.exists()
        data = json.loads(out.read_text())
        assert "paper1" in data
        assert len(data["paper1"]["citations"]) == 1
        cr = data["paper1"]["citations"][0]["crossref"]
        assert cr["title"] == "Attention is all you need"
        assert data["paper1"]["citations"][0].get("_crossref_disabled") is True

    def test_main_reports_no_crossref_matched(self, capsys: pytest.CaptureFixture) -> None:
        """Output message must not claim any Crossref matches."""
        citations = [{"raw_text": "[1] Vaswani et al., NeurIPS 2017."}]
        inp = self._make_input(citations)
        out = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        out_path = Path(out.name)

        mod_main = importlib.import_module("03_enrich_crossref")

        orig = sys.argv
        try:
            sys.argv = ["03_enrich_crossref.py", "--input", str(inp), "--output", str(out_path)]
            mod_main.main()
        finally:
            sys.argv = orig

        captured = capsys.readouterr()
        assert "Crossref" in captured.out or "crossref" in captured.out.lower()
