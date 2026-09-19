"""
Persistent Vector Database and similarity search index.
Manages embeddings, document metadata, top-k cosine similarity queries,
and disk persistence.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from src.rag.chunking import TextChunk
from src.rag.embeddings import BaseEmbeddingModel, get_embedding_model


class VectorStore:
    """Vector database index with cosine similarity search and persistence."""

    def __init__(
        self,
        embedding_model: Optional[BaseEmbeddingModel] = None,
        persist_dir: Optional[Path] = None
    ):
        self.embedder = embedding_model or get_embedding_model()
        self.persist_dir = Path(persist_dir) if persist_dir else None
        self.chunks: List[TextChunk] = []
        self.vectors: Optional[np.ndarray] = None

    def add_chunks(self, chunks: List[TextChunk]) -> int:
        """Embed and index a list of text chunks."""
        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        new_vectors = self.embedder.embed_texts(texts)

        if self.vectors is None or len(self.vectors) == 0:
            self.vectors = new_vectors
            self.chunks = list(chunks)
        else:
            self.vectors = np.vstack([self.vectors, new_vectors])
            self.chunks.extend(chunks)

        if self.persist_dir:
            self.persist()

        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 3,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for top-k most similar chunks for a query.
        Returns a list of dicts with chunk metadata, content, and similarity score.
        """
        if self.vectors is None or len(self.chunks) == 0:
            return []

        query_vec = self.embedder.embed_query(query)
        # Cosine similarity for unit-normalized vectors is dot product
        similarities = np.dot(self.vectors, query_vec)

        # Sort indices by score descending
        sorted_indices = np.argsort(similarities)[::-1]

        results: List[Dict[str, Any]] = []
        for idx in sorted_indices:
            score = float(similarities[idx])
            if score < similarity_threshold:
                continue

            chunk = self.chunks[idx]

            # Apply metadata filtering if specified
            if metadata_filter:
                match = all(chunk.metadata.get(k) == v for k, v in metadata_filter.items())
                if not match:
                    continue

            results.append({
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "content": chunk.content,
                "score": round(score, 4),
                "metadata": chunk.metadata,
            })

            if len(results) >= top_k:
                break

        return results

    def persist(self) -> None:
        """Save indexed vectors and metadata to disk."""
        if not self.persist_dir:
            return

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        vectors_path = self.persist_dir / "index_vectors.npy"
        metadata_path = self.persist_dir / "index_metadata.json"

        if self.vectors is not None:
            np.save(vectors_path, self.vectors)

        chunks_data = [c.to_dict() for c in self.chunks]
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2)

    def load(self) -> bool:
        """Load indexed vectors and metadata from disk if available."""
        if not self.persist_dir:
            return False

        vectors_path = self.persist_dir / "index_vectors.npy"
        metadata_path = self.persist_dir / "index_metadata.json"

        if not (vectors_path.exists() and metadata_path.exists()):
            return False

        self.vectors = np.load(vectors_path)
        with open(metadata_path, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)

        self.chunks = [TextChunk(**item) for item in chunks_data]
        return True

    def clear(self) -> None:
        """Clear all vectors and chunks from memory and disk."""
        self.chunks = []
        self.vectors = None
        if self.persist_dir:
            vectors_path = self.persist_dir / "index_vectors.npy"
            metadata_path = self.persist_dir / "index_metadata.json"
            if vectors_path.exists():
                vectors_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

    def get_documents_summary(self) -> List[Dict[str, Any]]:
        """Return a list of indexed document IDs with their chunk counts."""
        doc_counts = {}
        for c in self.chunks:
            source_name = c.metadata.get("source", c.doc_id)
            doc_counts[source_name] = doc_counts.get(source_name, 0) + 1

        return [{"document": doc, "chunks": count} for doc, count in doc_counts.items()]

    def count(self) -> int:
        """Return total indexed chunks count."""
        return len(self.chunks)
