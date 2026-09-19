"""
Script to seed the RAG vector database with knowledge base documents.
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.config import settings
from src.rag.pipeline import RAGPipeline


def seed_database():
    print(f"[RAG Ingestion] Scanning knowledge base directory: {settings.DOCS_DIR}")
    pipeline = RAGPipeline()

    chunks_count = pipeline.ingest_directory(settings.DOCS_DIR)
    print(f"[RAG Ingestion] Indexed {chunks_count} chunks into vector store.")
    print(f"[RAG Ingestion] Vector store location: {settings.VECTOR_STORE_PATH}")

    # Test query
    sample_query = "What is the return policy for opened items?"
    print(f"\n[RAG Test Query] '{sample_query}'")
    results = pipeline.retrieve(sample_query, top_k=2)
    for idx, r in enumerate(results):
        print(f"  Result {idx+1} ({r['chunk_id']}, score: {r['score']:.4f}):\n    {r['content'][:120]}...\n")


if __name__ == "__main__":
    seed_database()
