"""
End-to-End RAG (Retrieval-Augmented Generation) Pipeline.
Integrates Document Ingestion, Recursive Chunking, Vector Embeddings,
Top-K Semantic Search, and Context Injection.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import settings
from src.rag.ingestion import DocumentLoader, Document
from src.rag.chunking import RecursiveCharacterChunker, TextChunk
from src.rag.embeddings import get_embedding_model
from src.rag.vector_store import VectorStore


class RAGPipeline:
    """Orchestrates end-to-end knowledge ingestion and retrieval."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunker = RecursiveCharacterChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.store = vector_store or VectorStore(
            embedding_model=get_embedding_model(settings.EMBEDDING_MODEL_NAME),
            persist_dir=settings.VECTOR_STORE_PATH
        )
        self.store.load()

    def ingest_directory(self, dir_path: Path) -> int:
        """Load and index all supported files in a directory."""
        docs = DocumentLoader.load_directory(dir_path)
        if not docs:
            return 0

        chunks = self.chunker.chunk_documents(docs)
        count = self.store.add_chunks(chunks)
        return count

    def ingest_text(self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Index a single raw string document."""
        doc = Document(doc_id=doc_id, content=content, metadata=metadata or {})
        chunks = self.chunker.chunk_document(doc)
        return self.store.add_chunks(chunks)

    def retrieve(
        self,
        query: str,
        top_k: int = settings.TOP_K_RETRIEVAL,
        similarity_threshold: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve the top-k most relevant passages for a query."""
        if self.store.count() == 0:
            return []

        # If it's a general overview question, return the top chunks from the latest document
        q_lower = query.lower().strip()
        is_overview_query = any(phrase in q_lower for phrase in [
            "what is in the pdf", "what is in the document", "summarize the document",
            "summarize this pdf", "what is this document about", "overview of the pdf",
            "tell me about the document", "what does this document say", "what is this pdf"
        ])

        results = self.store.search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            metadata_filter=metadata_filter
        )

        # Fallback for overview queries if standard vector search returns low scores
        if is_overview_query or not results:
            # Return first top_k chunks from the most recently added chunks
            fallback_chunks = self.store.chunks[:top_k] if len(self.store.chunks) <= top_k else self.store.chunks[-top_k:]
            results = [{
                "chunk_id": c.chunk_id,
                "doc_id": c.doc_id,
                "content": c.content,
                "score": 1.0,
                "metadata": c.metadata
            } for c in fallback_chunks]

        return results

    def clear(self) -> None:
        """Clear all indexed data from vector store and disk."""
        self.store.clear()

    def get_documents_summary(self) -> List[Dict[str, Any]]:
        """Return list of distinct documents and chunk counts."""
        return self.store.get_documents_summary()

    def get_stats(self) -> Dict[str, Any]:
        """Return pipeline index statistics."""
        return {
            "total_chunks_indexed": self.store.count(),
            "documents": self.get_documents_summary(),
            "vector_dimension": self.store.vectors.shape[1] if self.store.vectors is not None else 0,
            "persist_dir": str(self.store.persist_dir) if self.store.persist_dir else None
        }
