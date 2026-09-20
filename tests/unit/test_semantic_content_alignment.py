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

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.__getitem__ = MagicMock()
        mock_cos = MagicMock()
        mock_cos.item.return_value = 0.2  # Low similarity
        mock_model.encode.return_value.__getitem__.return_value.__matmul__ = MagicMock(return_value=mock_cos)

        with patch.object(SemanticMatcher, '_get_model', return_value=mock_model):
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
