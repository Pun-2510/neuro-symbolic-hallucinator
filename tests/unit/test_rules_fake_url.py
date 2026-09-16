"""Tests cho fake URL detection (2026-09-15).

Priority 3.1: Detect fake URLs like https://example.com/rag-tech.pdf
Tests các pattern:
    - example.com → fake
    - example.org → fake
    - test.com → fake
    - localhost → fake
    - 127.0.0.1 → fake
    - Real URLs (arxiv.org, nature.com, etc.) → NOT fake
"""

from __future__ import annotations

import pytest

from integrity_checker.logic.rules import SymbolicRules, _is_fake_url
from integrity_checker.models.source import SourceResult
from integrity_checker.models.validation import MatchFeatures, ValidationLabel


class TestFakeURLRegex:
    """Direct regex tests for fake URL patterns."""

    def test_example_com_is_fake(self):
        is_fake, pattern = _is_fake_url("https://example.com/rag-tech.pdf")
        assert is_fake
        assert pattern == "example.com"

    def test_example_org_is_fake(self):
        is_fake, pattern = _is_fake_url("http://example.org/paper.pdf")
        assert is_fake
        assert pattern == "example.org"

    def test_example_net_is_fake(self):
        """example.net may not always parse correctly without scheme."""
        is_fake, pattern = _is_fake_url("https://example.net/doc.pdf")
        assert is_fake
        assert pattern == "example.net"

    def test_example_edu_is_fake(self):
        is_fake, pattern = _is_fake_url("https://example.edu/resource")
        assert is_fake
        assert pattern == "example.edu"

    def test_test_com_is_fake(self):
        is_fake, pattern = _is_fake_url("http://test.com/file.pdf")
        assert is_fake
        assert pattern == "test.com"

    def test_fake_com_is_fake(self):
        is_fake, pattern = _is_fake_url("https://fake.com/article")
        assert is_fake
        assert pattern == "fake.com"

    def test_localhost_is_fake(self):
        is_fake, pattern = _is_fake_url("http://localhost:8080/paper.pdf")
        assert is_fake
        # Pattern returns combined "localhost/127.0.0.1" for the IP check
        assert "localhost" in pattern.lower()

    def test_127_0_0_1_is_fake(self):
        is_fake, pattern = _is_fake_url("https://127.0.0.1/api/resource")
        assert is_fake
        # Pattern returns "localhost/127.0.0.1" for the IP check
        assert "127.0.0.1" in pattern or "localhost" in pattern.lower()

    def test_subdomain_example_com_still_fake(self):
        """Subdomain of example.com should also be fake."""
        is_fake, pattern = _is_fake_url("https://www.example.com/resource.pdf")
        assert is_fake
        assert pattern == "example.com"

    def test_path_example_com_still_fake(self):
        """URL with path containing example.com should be detected."""
        is_fake, pattern = _is_fake_url("https://example.com/path/to/file.pdf")
        assert is_fake
        assert pattern == "example.com"

    def test_real_arxiv_url_not_fake(self):
        """Real arXiv URLs should NOT be flagged as fake."""
        is_fake, _ = _is_fake_url("https://arxiv.org/abs/2103.14030")
        assert not is_fake

    def test_real_nature_url_not_fake(self):
        """Real Nature URLs should NOT be flagged as fake."""
        is_fake, _ = _is_fake_url("https://www.nature.com/articles/nature14539")
        assert not is_fake

    def test_real_acm_url_not_fake(self):
        """Real ACM URLs should NOT be flagged as fake."""
        is_fake, _ = _is_fake_url("https://dl.acm.org/doi/10.1145/3442188.3445922")
        assert not is_fake

    def test_real_ieee_url_not_fake(self):
        """Real IEEE URLs should NOT be flagged as fake."""
        is_fake, _ = _is_fake_url("https://ieeexplore.ieee.org/document/10000000")
        assert not is_fake

    def test_real_sciencedirect_url_not_fake(self):
        """Real ScienceDirect URLs should NOT be flagged as fake."""
        is_fake, _ = _is_fake_url("https://www.sciencedirect.com/science/article/pii/S0000000000000000")
        assert not is_fake

    def test_github_url_not_fake(self):
        """GitHub URLs should NOT be flagged as fake (even if not academic)."""
        is_fake, _ = _is_fake_url("https://github.com/user/repo")
        assert not is_fake

    def test_none_url_not_fake(self):
        """None URL should return not fake."""
        is_fake, _ = _is_fake_url(None)
        assert not is_fake

    def test_empty_url_not_fake(self):
        """Empty URL should return not fake."""
        is_fake, _ = _is_fake_url("")
        assert not is_fake

    def test_mixed_case_example_com_is_fake(self):
        """Case-insensitive matching for example.com."""
        is_fake, pattern = _is_fake_url("https://EXAMPLE.COM/resource")
        assert is_fake
        assert pattern == "example.com"


class TestFakeURLRule:
    """Tests for fake URL in SymbolicRules.apply()."""

    @pytest.fixture
    def rules(self):
        return SymbolicRules()

    @pytest.fixture
    def empty_source(self):
        """Empty source result with no candidates."""
        return SourceResult(
            citation_raw="test citation",
            candidates=[],
            sources_queried=["crossref"],
            sources_succeeded=[],
            sources_failed={"crossref": "not found"},
        )

    @pytest.fixture
    def low_features(self):
        """Features with low values."""
        return MatchFeatures(
            title_sim_fuzzy=0.0,
            title_sim_semantic=0.0,
            author_jaccard=0.0,
            year_distance=999,
            doi_exact_match=False,
            source_consensus=0,
        )

    def test_example_com_url_returns_suspected(self, rules, empty_source, low_features):
        """example.com URL should be flagged as SUSPECTED_HALLUCINATION."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url="https://example.com/rag-tech.pdf",
        )
        assert outcome.label == ValidationLabel.SUSPECTED_HALLUCINATION
        assert "R-FAKE-URL" in outcome.triggered_rules
        assert outcome.confidence >= 0.9  # High confidence for clear fake

    def test_localhost_url_returns_suspected(self, rules, empty_source, low_features):
        """localhost URL should be flagged as SUSPECTED_HALLUCINATION."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url="http://localhost:3000/paper.pdf",
        )
        assert outcome.label == ValidationLabel.SUSPECTED_HALLUCINATION
        assert "R-FAKE-URL" in outcome.triggered_rules

    def test_127_0_0_1_url_returns_suspected(self, rules, empty_source, low_features):
        """127.0.0.1 URL should be flagged as SUSPECTED_HALLUCINATION."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url="https://127.0.0.1/api/doc",
        )
        assert outcome.label == ValidationLabel.SUSPECTED_HALLUCINATION
        assert "R-FAKE-URL" in outcome.triggered_rules

    def test_real_url_not_flagged(self, rules, empty_source, low_features):
        """Real arXiv URL should NOT trigger R-FAKE-URL."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url="https://arxiv.org/abs/2103.14030",
        )
        assert "R-FAKE-URL" not in outcome.triggered_rules

    def test_no_url_param_not_flagged(self, rules, empty_source, low_features):
        """When citation_url is None, should not trigger fake URL rule."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url=None,
        )
        assert "R-FAKE-URL" not in outcome.triggered_rules

    def test_fake_url_high_confidence(self, rules, empty_source, low_features):
        """Fake URL detection should have high confidence."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url="https://example.com/fake-paper.pdf",
        )
        assert outcome.confidence >= 0.9

    def test_fake_url_in_reasoning(self, rules, empty_source, low_features):
        """Reasoning should mention the fake domain."""
        outcome = rules.apply(
            low_features,
            empty_source,
            citation_url="https://example.com/paper.pdf",
        )
        assert "example.com" in outcome.reasoning.lower()


class TestFakeURLWithCandidate:
    """Test that fake URLs are caught even with fake candidates."""

    @pytest.fixture
    def rules(self):
        return SymbolicRules()

    @pytest.fixture
    def fake_candidate_source(self):
        """Source with fake-looking candidates (should be ignored for fake URL)."""
        from integrity_checker.models.source import SourceCandidate
        return SourceResult(
            citation_raw="example.com citation",
            candidates=[
                SourceCandidate(
                    source_name="crossref",
                    found=True,
                    title="Fake Paper Title",
                    authors=["Fake, A."],
                    year="2023",
                    confidence=0.3,
                ),
            ],
            sources_queried=["crossref"],
            sources_succeeded=["crossref"],
            sources_failed={},
        )

    def test_fake_url_caught_even_with_candidate(self, rules, fake_candidate_source):
        """Fake URL should be flagged even if API returns a candidate."""
        features = MatchFeatures(
            title_sim_fuzzy=0.7,
            title_sim_semantic=0.7,
            author_jaccard=0.5,
            year_distance=0,
            doi_exact_match=False,
            source_consensus=1,
        )
        outcome = rules.apply(
            features,
            fake_candidate_source,
            citation_url="https://example.com/fake.pdf",
        )
        # Should still be caught as fake URL (high priority pre-flight check)
        assert outcome.label == ValidationLabel.SUSPECTED_HALLUCINATION
        assert "R-FAKE-URL" in outcome.triggered_rules
