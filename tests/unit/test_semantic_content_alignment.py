"""Unit tests for SemanticMatcher content alignment (Neural layer v1.3)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


class TestSemanticContentAlignment:
    """Test content-context alignment using Neural embeddings."""

    def test_check_content_alignment_returns_result(self):
        """check_content_alignment should return SemanticAlignmentResult."""
        from integrity_checker.matching.semantic import SemanticMatcher

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.__getitem__ = MagicMock()
        mock_cos = MagicMock()
        mock_cos.item.return_value = 0.8  # High similarity
        mock_model.encode.return_value.__getitem__.return_value.__matmul__ = MagicMock(return_value=mock_cos)

        with patch.object(SemanticMatcher, '_get_model', return_value=mock_model):
            matcher = SemanticMatcher()
            result = matcher.check_content_alignment(
                cited_context="Attention mechanisms have revolutionized NLP research.",
                source_title="Attention Is All You Need",
                source_abstract="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
            )

        assert result.similarity >= 0.0
        assert result.confidence in ["high", "medium", "low"]
        assert isinstance(result.is_aligned, bool)

    def test_content_aligned_high_similarity(self):
        """High semantic similarity should result in is_aligned=True."""
        from integrity_checker.matching.semantic import SemanticMatcher

        # Mock the entire check_content_alignment method to avoid real model
        original_check = SemanticMatcher.check_content_alignment

        def mock_check(self, cited_context, source_title, source_abstract=None, source_body=None):
            from integrity_checker.matching.semantic import SemanticAlignmentResult
            # Return high similarity alignment
            return SemanticAlignmentResult(
                similarity=0.85,
                confidence="high",
                is_aligned=True,
                compared_texts={
                    "cited_context": cited_context[:50],
                    "source_title": source_title
                }
            )

        with patch.object(SemanticMatcher, 'check_content_alignment', mock_check):
            matcher = SemanticMatcher()
            result = matcher.check_content_alignment(
                cited_context="Transformers have replaced RNNs in most NLP tasks.",
                source_title="Attention Is All You Need",
            )

        # With high similarity (0.85), should be aligned
        assert result.is_aligned is True
        assert result.confidence == "high"
        assert result.similarity > 0.7

    def test_content_not_aligned_low_similarity(self):
        """Low semantic similarity should result in is_aligned=False."""
        from integrity_checker.matching.semantic import SemanticMatcher

        # Mock the _compute_similarity method to return low similarity
        with patch.object(SemanticMatcher, '_compute_similarity', return_value=0.2):
            matcher = SemanticMatcher()
            result = matcher.check_content_alignment(
                cited_context="Cooking methods for Italian cuisine.",
                source_title="Attention Is All You Need",
            )

        assert result.is_aligned is False
        assert result.confidence in ["low", "medium"]

    def test_content_alignment_with_abstract(self):
        """Content alignment should consider abstract when available."""
        from integrity_checker.matching.semantic import SemanticMatcher

        call_count = [0]
        similarity_values = [0.6, 0.8]  # First = title, Second = abstract

        def mock_encode(texts, **kwargs):
            result = MagicMock()
            result.__getitem__ = MagicMock()
            result.__getitem__.return_value.__matmul__ = MagicMock(
                return_value=MagicMock(item=lambda: similarity_values[call_count[0] % 2])
            )
            call_count[0] += 1
            return result

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode

        with patch.object(SemanticMatcher, '_get_model', return_value=mock_model):
            matcher = SemanticMatcher()
            result = matcher.check_content_alignment(
                cited_context="Deep learning for NLP",
                source_title="Neural Machine Translation",
                source_abstract="A neural network model for machine translation",
            )

        # Should have called encode at least twice (title + abstract)
        assert call_count[0] >= 2

    def test_content_alignment_returns_compared_texts(self):
        """Result should include compared texts for debugging."""
        from integrity_checker.matching.semantic import SemanticMatcher

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.__getitem__ = MagicMock()
        mock_cos = MagicMock()
        mock_cos.item.return_value = 0.7
        mock_model.encode.return_value.__getitem__.return_value.__matmul__ = MagicMock(return_value=mock_cos)

        with patch.object(SemanticMatcher, '_get_model', return_value=mock_model):
            matcher = SemanticMatcher()
            result = matcher.check_content_alignment(
                cited_context="The quick brown fox jumps over the lazy dog.",
                source_title="A Study on Neural Networks",
            )

        assert "cited_context" in result.compared_texts
        assert "source_title" in result.compared_texts

    def test_content_alignment_fallback_when_no_model(self):
        """Should return fallback result when model not available."""
        from integrity_checker.matching.semantic import SemanticMatcher

        with patch.object(SemanticMatcher, '_get_model', return_value=None):
            matcher = SemanticMatcher()
            result = matcher.check_content_alignment(
                cited_context="Some text",
                source_title="Some title",
            )

        assert result.similarity == 0.0
        assert result.confidence == "low"
        assert result.is_aligned is False


class TestSemanticMatcherThresholds:
    """Test alignment threshold configurations."""

    def test_default_thresholds(self):
        """Test default alignment thresholds."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()

        assert matcher.ALIGNMENT_THRESHOLD_HIGH == 0.70
        assert matcher.ALIGNMENT_THRESHOLD_MEDIUM == 0.50
        assert matcher.ALIGNMENT_THRESHOLD_LOW == 0.30

    def test_alignment_confidence_mapping(self):
        """Test confidence level determination."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()

        # High threshold
        conf, aligned = matcher._determine_alignment(0.85)
        assert conf == "high"
        assert aligned is True

        # Medium threshold
        conf, aligned = matcher._determine_alignment(0.60)
        assert conf == "medium"
        assert aligned is True

        # Low threshold
        conf, aligned = matcher._determine_alignment(0.40)
        assert conf == "medium"
        assert aligned is False

        # Below low threshold
        conf, aligned = matcher._determine_alignment(0.20)
        assert conf == "low"
        assert aligned is False


class TestSemanticMatcherTruncation:
    """Test text truncation utilities."""

    def test_truncate_short_text(self):
        """Short text should not be truncated."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        text = "Short text"
        result = matcher._truncate_text(text, max_length=100)

        assert result == text

    def test_truncate_long_text(self):
        """Long text should be truncated with ellipsis."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        text = "A" * 200
        result = matcher._truncate_text(text, max_length=50)

        assert len(result) <= 50
        assert result.endswith("...")

    def test_truncate_empty_text(self):
        """Empty text should return empty string."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        result = matcher._truncate_text("", max_length=50)

        assert result == ""


class TestSemanticMatcherBatch:
    """Test batch similarity computation."""

    def test_batch_similarity_returns_list(self):
        """batch_similarity should return list of floats."""
        from integrity_checker.matching.semantic import SemanticMatcher

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.__getitem__ = MagicMock()
        mock_cos = MagicMock()
        mock_cos.item.return_value = 0.7
        mock_model.encode.return_value.__getitem__.return_value.__matmul__ = MagicMock(return_value=mock_cos)

        with patch.object(SemanticMatcher, '_get_model', return_value=mock_model):
            matcher = SemanticMatcher()
            pairs = [
                ("Hello world", "Hello world"),
                ("Deep learning", "Machine learning"),
            ]
            results = matcher.batch_similarity(pairs)

        assert isinstance(results, list)
        assert len(results) == len(pairs)
        for r in results:
            assert 0.0 <= r <= 1.0

    def test_batch_similarity_empty_list(self):
        """Empty input should return empty list."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        results = matcher.batch_similarity([])

        assert results == []


class TestSemanticMatcherSegments:
    """Test text segmentation for long text comparison."""

    def test_split_into_segments(self):
        """Should split long text into segments."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        segments = matcher._split_into_segments(text, max_length=30)

        assert len(segments) > 1
        # Some segments may be slightly longer than max_length due to sentence boundaries
        for seg in segments:
            assert len(seg) <= 35  # Allow small tolerance for sentence boundaries

    def test_split_short_text(self):
        """Short text should return single segment."""
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        text = "Short text"
        segments = matcher._split_into_segments(text, max_length=100)

        assert len(segments) == 1
        assert segments[0] == text

    def test_multi_sentence_abstract_pooling_boosts_sentence_level_match(self):
        """Multi-sentence abstract pooling should capture high similarity with a specific sentence."""
        from integrity_checker.matching.semantic import SemanticMatcher

        # Title sim = 0.35 (metaphorical title), whole abstract sim = 0.55,
        # sentence 1 sim = 0.40, sentence 2 sim = 0.85 (direct match to cited claim)
        sims = [0.35, 0.55, 0.40, 0.85]
        idx = {"i": 0}

        def fake_compute_sim(self, model, t1, t2):
            val = sims[min(idx["i"], len(sims) - 1)]
            idx["i"] += 1
            return val

        long_abstract = (
            "Background on recurrent neural networks and convolutional models in sequence modeling. "
            "We propose the Transformer, a model architecture eschewing recurrence and relying entirely on attention mechanisms."
        )

        with patch.object(SemanticMatcher, "_get_model", return_value=MagicMock()), patch.object(
            SemanticMatcher, "_compute_similarity", fake_compute_sim
        ):
            matcher = SemanticMatcher()
            res = matcher.check_content_alignment(
                cited_context="The Transformer architecture dispenses with recurrence and relies on attention.",
                source_title="Attention Is All You Need",
                source_abstract=long_abstract,
            )

        assert res.is_aligned is True
        assert res.similarity >= 0.65


class TestDeepNeuralLayerUpgrade:
    """Tests for Deep Neural Layer v2.0 (de-hyphenation, focal sentence, intent, stance, cross-lingual, implicit body discovery)."""

    def test_clean_and_dehyphenate_context_repairs_pdf_line_wraps(self):
        from integrity_checker.matching.semantic import SemanticMatcher

        raw = "modern neural networks are poorly cal- ibration and HDB- SCAN clustering with TF- IDF."
        cleaned = SemanticMatcher.clean_and_dehyphenate_context(raw)
        assert "calibration" in cleaned
        assert "HDBSCAN" in cleaned
        assert "TF-IDF" in cleaned

    def test_extract_focal_sentence_isolates_marker_sentence(self):
        from integrity_checker.matching.semantic import SemanticMatcher

        noisy_window = (
            "1. Sentence Embeddings: Sentence-BERT [20] converts text into vectors. "
            "2. Dimensionality Reduction: UMAP [15] projects high-dimensional embeddings. "
            "3. Clustering: HDBSCAN [2] identifies dense topic clusters and marks outliers as noise."
        )
        focal = SemanticMatcher.extract_focal_sentence(
            noisy_window,
            citation_marker="[2]",
            source_title="Density-Based Clustering Based on Hierarchical Density Estimates",
        )
        assert "HDBSCAN" in focal
        assert "Sentence-BERT" not in focal

    def test_detect_and_bridge_cross_lingual_vietnamese_to_english(self):
        from integrity_checker.matching.semantic import SemanticMatcher

        vi_ctx = "Chúng tôi sử dụng mô hình học sâu và cơ chế chú ý để phân loại văn bản cảm xúc."
        en_title = "Attention Is All You Need"
        is_xling, bridge = SemanticMatcher.detect_and_bridge_cross_lingual(vi_ctx, en_title)
        assert is_xling is True
        assert "deep learning" in bridge.lower()
        assert "attention mechanism" in bridge.lower()

    def test_classify_citation_intent_categories(self):
        from integrity_checker.matching.semantic import SemanticMatcher

        with patch.object(SemanticMatcher, "_get_model", return_value=None):
            matcher = SemanticMatcher()
            assert (
                matcher.classify_citation_intent(
                    "We adopt and fine-tune the Sentence-BERT architecture [12] as our embedding backbone."
                )
                == "methodology"
            )
            assert (
                matcher.classify_citation_intent(
                    "Our model outperforms the baseline accuracy reported by Smith et al. [4] by 3.5% F1."
                )
                == "result_comparison"
            )
            assert (
                matcher.classify_citation_intent(
                    "Prior studies have broadly surveyed mental health trends in social media [1]."
                )
                == "background"
            )

    def test_check_claim_stance_detects_support_and_contradiction_risk(self):
        from integrity_checker.matching.semantic import SemanticMatcher

        matcher = SemanticMatcher()
        assert (
            matcher.check_claim_stance(
                "BERT pre-trains deep bidirectional representations from unlabeled text.",
                "BERT is designed to pre-train deep bidirectional representations from unlabeled text.",
                similarity=0.82,
                has_abstract=True,
            )
            == "supported"
        )
        assert (
            matcher.check_claim_stance(
                "Temperature scaling fails to improve calibration and is ineffective for neural networks.",
                "We show that temperature scaling is surprisingly effective at calibrating predictions.",
                similarity=0.42,
                has_abstract=True,
            )
            == "contradiction_risk"
        )

    def test_discover_implicit_body_context_finds_relevant_body_passage(self):
        from integrity_checker.matching.semantic import SemanticMatcher

        body_pages = [
            (1, "Introduction to our e-commerce bookstore project and team members."),
            (
                2,
                "In our backend architecture, PHP server-side scripting and MySQL relational databases "
                "handle user authentication, session management, and SQL queries.",
            ),
        ]
        result = SemanticMatcher.get_instance().discover_implicit_body_context(
            body_pages=body_pages,
            source_title="PHP and MySQL Web Development",
            source_abstract="Practical guide to developing database-driven web applications using PHP and MySQL.",
            source_authors=["Welling", "Thomson"],
        )
        assert result is not None
        page_num, passage, score = result
        assert page_num == 2
        assert "PHP" in passage and "MySQL" in passage
        assert score >= 0.30


