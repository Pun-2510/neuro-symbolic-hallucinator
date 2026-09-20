"""Semantic similarity với sentence-transformers.

Module này cung cấp Neural layer cho Neuro-Symbolic system:
- Title similarity: So sánh tiêu đề citation với paper nguồn
- Content alignment: So sánh đoạn văn được trích dẫn với abstract/paper
- Multi-text comparison: So sánh citation context với multiple sources

References:
    - Sentence-BERT: Reimers & Gurevych (2019)
    - Semantic Schemas:用于自然语言理解的句子嵌入
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SemanticAlignmentResult:
    """Kết quả semantic alignment check.

    Attributes:
        similarity: Cosine similarity score (0.0-1.0)
        confidence: Confidence level ('high', 'medium', 'low')
        is_aligned: True nếu content có semantic alignment
        compared_texts: Dict chứa các text đã so sánh (để debug)
    """
    similarity: float
    confidence: str
    is_aligned: bool
    compared_texts: dict[str, str]


class SemanticMatcher:
    """Cosine similarity giữa 2 đoạn text dùng sentence-transformers.

    Uses singleton pattern (2026-09-15) -- model instance is cached globally
    so it only loads once per process, avoiding ~5s reload overhead on each
    SemanticMatcher() instantiation.

    v1.3: Bổ sung content-context alignment để kiểm tra semantic
    alignment giữa đoạn văn được trích dẫn và paper nguồn.

    # TODO(user): tuần 10 -- benchmark các model sau:
        - all-MiniLM-L6-v2 (default, CPU-friendly, ~80MB)
        - mxbai-embed-large-v1 (tốt hơn nhưng nặng hơn)
        - multilingual-e5-base (nếu cần tiếng Việt)
    """

    _instance_lock = threading.Lock()
    _model_cache: dict[str, "object"] = {}
    _singleton: "SemanticMatcher | None" = None

    # Thresholds cho content alignment
    ALIGNMENT_THRESHOLD_HIGH = 0.70  # High confidence alignment
    ALIGNMENT_THRESHOLD_MEDIUM = 0.50  # Medium confidence alignment
    ALIGNMENT_THRESHOLD_LOW = 0.30  # Low confidence, likely mismatch

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings().matching
        self.model_name = model_name or settings.embedding_model
        self._model = None  # lazy load

    @classmethod
    def get_instance(cls, model_name: str | None = None) -> "SemanticMatcher":
        """Get singleton instance -- model loads only once per process.

        Args:
            model_name: Override default model. If singleton already exists
                       with different model, returns existing singleton (first
                       model wins to avoid redundant loads).

        Returns:
            Shared SemanticMatcher instance with cached model.
        """
        if cls._singleton is None:
            with cls._instance_lock:
                if cls._singleton is None:
                    cls._singleton = cls(model_name)
                    logger.info(f"SemanticMatcher singleton created with model: {cls._singleton.model_name}")
        return cls._singleton

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton -- for testing only."""
        with cls._instance_lock:
            cls._singleton = None

    def _get_model(self):
        if self._model is None:
            with self._instance_lock:
                if self.model_name not in self._model_cache:
                    try:
                        from sentence_transformers import SentenceTransformer  # type: ignore

                        logger.info(f"Loading sentence-transformers: {self.model_name}")
                        self._model_cache[self.model_name] = SentenceTransformer(self.model_name)
                    except ImportError as e:
                        logger.error(f"sentence-transformers chưa cài: {e}")
                        return None
                self._model = self._model_cache[self.model_name]
        return self._model

    def similarity(self, text1: str, text2: str) -> float:
        """Trả cosine similarity 0.0–1.0. Fallback 0.0 nếu model chưa load được."""
        model = self._get_model()
        if model is None or not text1 or not text2:
            return 0.0
        try:
            embs = model.encode([text1, text2], convert_to_tensor=True, normalize_embeddings=True)
            cos = (embs[0] @ embs[1]).item()
            # clamp về 0–1
            return max(0.0, min(1.0, (cos + 1.0) / 2.0))
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Semantic similarity error: {e}")
            return 0.0

    # === NEURAL LAYER: Content-Context Alignment (v1.3) ===

    def check_content_alignment(
        self,
        cited_context: str,
        source_title: str,
        source_abstract: Optional[str] = None,
        source_body: Optional[str] = None,
    ) -> SemanticAlignmentResult:
        """Kiểm tra semantic alignment giữa đoạn văn được trích dẫn và paper nguồn.

        Đây là Neural layer chính của hệ thống -- so sánh ý nghĩa ngữ nghĩa
        chứ không chỉ so khớp từ.

        Args:
            cited_context: Đoạn văn/nội dung được trích dẫn trong essay
            source_title: Tiêu đề paper nguồn từ API
            source_abstract: Abstract của paper (nếu có)
            source_body: Body text của paper (nếu có, dùng cho deep check)

        Returns:
            SemanticAlignmentResult với similarity score và confidence level

        Example:
            >>> matcher = SemanticMatcher.get_instance()
            >>> result = matcher.check_content_alignment(
            ...     cited_context="Attention mechanisms have revolutionized NLP",
            ...     source_title="Attention Is All You Need",
            ...     source_abstract="The dominant sequence transduction models..."
            ... )
            >>> result.is_aligned  # True
            >>> result.similarity  # 0.82
        """
        model = self._get_model()
        if model is None:
            return SemanticAlignmentResult(
                similarity=0.0,
                confidence="low",
                is_aligned=False,
                compared_texts={"cited_context": cited_context, "source": source_title},
            )

        try:
            # Truncate texts để tránh memory issues
            cited_context = self._truncate_text(cited_context, max_length=512)
            source_title = self._truncate_text(source_title, max_length=256)

            # Strategy 1: So sánh với title (nhanh nhất)
            title_sim = self._compute_similarity(model, cited_context, source_title)

            # Strategy 2: So sánh với abstract (nếu có)
            abstract_sim = 0.0
            if source_abstract:
                source_abstract = self._truncate_text(source_abstract, max_length=512)
                abstract_sim = self._compute_similarity(model, cited_context, source_abstract)

            # Strategy 3: So sánh với body (nếu có, dùng sampling)
            body_sim = 0.0
            if source_body:
                body_sim = self._compute_similarity_with_long_text(
                    model, cited_context, source_body, max_sample_length=512
                )

            # Combine scores -- lấy max nhưng có weight
            scores = [title_sim]
            weights = [0.3]  # Title weight

            if abstract_sim > 0:
                scores.append(abstract_sim)
                weights.append(0.5)  # Abstract weight cao hơn

            if body_sim > 0:
                scores.append(body_sim)
                weights.append(0.2)  # Body weight thấp hơn

            # Normalize weights
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]
            weighted_similarity = sum(s * w for s, w in zip(scores, normalized_weights))

            # Final similarity - use weighted average
            final_sim = weighted_similarity if scores else 0.0

            # Determine confidence và alignment
            confidence, is_aligned = self._determine_alignment(final_sim)

            return SemanticAlignmentResult(
                similarity=round(final_sim, 4),
                confidence=confidence,
                is_aligned=is_aligned,
                compared_texts={
                    "cited_context": cited_context[:100] + "..." if len(cited_context) > 100 else cited_context,
                    "source_title": source_title,
                    "has_abstract": bool(source_abstract),
                    "has_body": bool(source_body),
                },
            )

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Content alignment check failed: {e}")
            return SemanticAlignmentResult(
                similarity=0.0,
                confidence="low",
                is_aligned=False,
                compared_texts={"cited_context": cited_context, "source": source_title},
            )

    def _compute_similarity(
        self,
        model: "object",
        text1: str,
        text2: str,
    ) -> float:
        """Compute cosine similarity giữa 2 texts."""
        try:
            embs = model.encode(
                [text1, text2],
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            cos = (embs[0] @ embs[1]).item()
            return max(0.0, min(1.0, (cos + 1.0) / 2.0))
        except Exception:  # noqa: BLE001
            return 0.0

    def _compute_similarity_with_long_text(
        self,
        model: "object",
        short_text: str,
        long_text: str,
        max_sample_length: int = 512,
    ) -> float:
        """So sánh short text với long text bằng cách sample segments.

        Chia long text thành các segments và so sánh từng cái,
        lấy max similarity.
        """
        try:
            # Split long text thành sentences/paragraphs
            segments = self._split_into_segments(long_text, max_sample_length)

            if not segments:
                return 0.0

            # Encode short text once
            short_emb = model.encode(
                short_text,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            # Encode all segments và compute similarities
            similarities = []
            for segment in segments[:5]:  # Max 5 segments
                seg_emb = model.encode(
                    segment,
                    convert_to_tensor=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                sim = (short_emb @ seg_emb).item()
                similarities.append(sim)

            return max(similarities) if similarities else 0.0

        except Exception:  # noqa: BLE001
            return 0.0

    def _split_into_segments(self, text: str, max_length: int) -> list[str]:
        """Split text thành các segments có độ dài ~max_length."""
        if len(text) <= max_length:
            return [text]

        # Split by sentences
        import re
        sentences = re.split(r"[.!?]+", text)
        segments = []
        current_segment = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_segment) + len(sentence) + 1 <= max_length:
                current_segment += ". " + sentence if current_segment else sentence
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = sentence

        if current_segment:
            segments.append(current_segment)

        return segments

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max length."""
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def _determine_alignment(self, similarity: float) -> tuple[str, bool]:
        """Determine confidence level và alignment status từ similarity score."""
        if similarity >= self.ALIGNMENT_THRESHOLD_HIGH:
            return "high", True
        elif similarity >= self.ALIGNMENT_THRESHOLD_MEDIUM:
            return "medium", True
        elif similarity >= self.ALIGNMENT_THRESHOLD_LOW:
            return "medium", False
        else:
            return "low", False

    # === Utility methods ===

    def batch_similarity(self, text_pairs: list[tuple[str, str]]) -> list[float]:
        """Compute similarity cho nhiều text pairs cùng lúc (optimized).

        Args:
            text_pairs: List of (text1, text2) tuples

        Returns:
            List of similarity scores
        """
        model = self._get_model()
        if model is None:
            return [0.0] * len(text_pairs)

        try:
            texts = []
            for t1, t2 in text_pairs:
                texts.extend([self._truncate_text(t1), self._truncate_text(t2)])

            embs = model.encode(
                texts,
                convert_to_tensor=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32,
            )

            similarities = []
            for i in range(0, len(embs), 2):
                if i + 1 < len(embs):
                    cos = (embs[i] @ embs[i + 1]).item()
                    similarities.append(max(0.0, min(1.0, (cos + 1.0) / 2.0)))
                else:
                    similarities.append(0.0)

            return similarities

        except Exception as e:  # noqa: BLE001
            logger.warning(f"Batch similarity failed: {e}")
            return [0.0] * len(text_pairs)