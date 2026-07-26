"""Semantic similarity với sentence-transformers."""

from __future__ import annotations

import threading

from integrity_checker.config import get_settings
from integrity_checker.logging import get_logger

logger = get_logger(__name__)


class SemanticMatcher:
    """Cosine similarity giữa 2 đoạn text dùng sentence-transformers.

    # TODO(user): tuần 10 — benchmark các model sau:
        - all-MiniLM-L6-v2 (default, CPU-friendly, ~80MB)
        - mxbai-embed-large-v1 (tốt hơn nhưng nặng hơn)
        - multilingual-e5-base (nếu cần tiếng Việt)
    """

    _instance_lock = threading.Lock()
    _model_cache: dict[str, "object"] = {}

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings().matching
        self.model_name = model_name or settings.embedding_model
        self._model = None  # lazy load

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