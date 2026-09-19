"""
Vector embedding model interfaces and implementations.
Supports HuggingFace SentenceTransformers and lightweight deterministic
local feature vectorizers with unit-norm cosine normalization.
"""

import math
import hashlib
from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseEmbeddingModel(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Compute normalized dense vector embeddings for a list of texts."""
        pass

    def embed_query(self, query: str) -> np.ndarray:
        """Compute embedding for a single search query."""
        return self.embed_texts([query])[0]


class FastDeterministicEmbedding(BaseEmbeddingModel):
    """
    Lightweight, deterministic feature-hashing embedding model.
    Produces 384-dimensional dense vectors with cosine normalization.
    Ensures 100% offline determinism and zero network dependency.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_token(self, token: str) -> int:
        return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dimension

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)

        for row_idx, text in enumerate(texts):
            tokens = text.lower().split()
            if not tokens:
                vectors[row_idx, 0] = 1.0
                continue

            # Unigrams and character trigrams
            for token in tokens:
                idx = self._hash_token(token)
                vectors[row_idx, idx] += 1.0

                if len(token) >= 3:
                    for i in range(len(token) - 2):
                        tri = token[i:i+3]
                        idx_tri = self._hash_token(tri)
                        vectors[row_idx, idx_tri] += 0.5

            # L2 normalize
            norm = np.linalg.norm(vectors[row_idx])
            if norm > 1e-12:
                vectors[row_idx] = vectors[row_idx] / norm

        return vectors


class SentenceTransformerEmbedding(BaseEmbeddingModel):
    """HuggingFace SentenceTransformer embedding wrapper."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except Exception:
                # Fallback to deterministic model if sentence_transformers isn't loaded
                self._model = FastDeterministicEmbedding()

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        self._load_model()
        if isinstance(self._model, FastDeterministicEmbedding):
            return self._model.embed_texts(texts)
        embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(embeddings, dtype=np.float32)


def get_embedding_model(name_or_type: str = "fast") -> BaseEmbeddingModel:
    """Factory to retrieve embedding model."""
    if "sentence" in name_or_type.lower() or "minilm" in name_or_type.lower():
        try:
            return SentenceTransformerEmbedding(name_or_type)
        except Exception:
            return FastDeterministicEmbedding()
    return FastDeterministicEmbedding()
