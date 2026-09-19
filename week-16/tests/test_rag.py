"""
Tests for RAG Ingestion, Chunking, Embeddings, and Vector Store.
"""

import pytest
import numpy as np
from pathlib import Path
from src.rag.ingestion import Document, DocumentLoader
from src.rag.chunking import RecursiveCharacterChunker
from src.rag.embeddings import FastDeterministicEmbedding, get_embedding_model
from src.rag.vector_store import VectorStore
from src.rag.pipeline import RAGPipeline


def test_chunking_recursive():
    chunker = RecursiveCharacterChunker(chunk_size=150, chunk_overlap=30)
    text = (
        "# Heading 1\n\n"
        "This is paragraph one explaining the refund and exchange policy in detail.\n\n"
        "## Heading 2\n\n"
        "This is paragraph two detailing domestic standard shipping requirements and carriers."
    )
    doc = Document(doc_id="test_doc", content=text)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    assert all(len(c.content) <= 200 for c in chunks)
    assert chunks[0].doc_id == "test_doc"


def test_embeddings_unit_norm():
    embedder = FastDeterministicEmbedding(dimension=128)
    vecs = embedder.embed_texts(["Hello world", "Customer support refund query"])
    assert vecs.shape == (2, 128)
    for v in vecs:
        norm = np.linalg.norm(v)
        assert abs(norm - 1.0) < 1e-4


def test_vector_store_search_and_persist(tmp_path):
    embedder = FastDeterministicEmbedding(dimension=64)
    store = VectorStore(embedding_model=embedder, persist_dir=tmp_path)

    chunker = RecursiveCharacterChunker(chunk_size=200, chunk_overlap=20)
    doc1 = Document(doc_id="refund_doc", content="Customers may return unopened items within 30 days for 100% full refund.")
    doc2 = Document(doc_id="shipping_doc", content="Standard delivery takes 3-5 business days via FedEx and UPS.")

    chunks = chunker.chunk_documents([doc1, doc2])
    store.add_chunks(chunks)

    assert store.count() == len(chunks)

    # Search for refund
    results = store.search("refund policy within 30 days", top_k=1)
    assert len(results) == 1
    assert "refund" in results[0]["content"].lower()

    # Test load from disk
    store_loaded = VectorStore(embedding_model=embedder, persist_dir=tmp_path)
    loaded = store_loaded.load()
    assert loaded is True
    assert store_loaded.count() == store.count()


def test_rag_pipeline_end_to_end(tmp_path):
    pipeline = RAGPipeline(vector_store=VectorStore(persist_dir=tmp_path))
    pipeline.ingest_text("policy_1", "All electronics carry a 1-year manufacturer warranty.")

    results = pipeline.retrieve("warranty period for electronics", top_k=1)
    assert len(results) == 1
    assert "warranty" in results[0]["content"]
