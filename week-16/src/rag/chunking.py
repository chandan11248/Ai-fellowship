"""
Semantic and recursive character chunking for RAG ingestion.
Splits long documents into overlapping passages while preserving
structural context (headers, paragraph boundaries, sentences).
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.rag.ingestion import Document


class TextChunk(BaseModel):
    """Represents an atomic indexed text fragment."""
    chunk_id: str
    doc_id: str
    content: str
    chunk_index: int
    char_start: int
    char_end: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "metadata": self.metadata,
        }


class RecursiveCharacterChunker:
    """
    Splits text recursively by trying separators in order:
    ['\n\n# ', '\n\n## ', '\n\n', '\n', '. ', '? ', '! ', ' ', '']
    """

    DEFAULT_SEPARATORS = [
        "\n\n# ",
        "\n\n## ",
        "\n\n### ",
        "\n\n",
        "\n",
        ". ",
        "? ",
        "! ",
        " ",
        ""
    ]

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100, separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursive splitting implementation."""
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: List[str] = []
        for s in splits:
            if separator and s:
                # restore header prefix if split on markdown headers
                if separator.startswith("\n\n#"):
                    s = separator.strip() + " " + s
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    other_splits = self._split_text(s, new_separators)
                    good_splits.extend(other_splits)
                else:
                    good_splits.append(s)

        # Merge short splits with overlap
        merged: List[str] = []
        current = ""

        for piece in good_splits:
            if not current:
                current = piece
            elif len(current) + len(separator) + len(piece) <= self.chunk_size:
                current = f"{current}{separator}{piece}"
            else:
                merged.append(current.strip())
                # Overlap step: keep tail of current
                if self.chunk_overlap > 0 and len(current) > self.chunk_overlap:
                    overlap_text = current[-self.chunk_overlap:]
                    current = f"{overlap_text}{separator}{piece}"
                else:
                    current = piece

        if current and current.strip():
            merged.append(current.strip())

        return [c for c in merged if c]

    def chunk_document(self, document: Document) -> List[TextChunk]:
        """Split a single Document into a list of TextChunk objects."""
        raw_text = document.content
        text_slices = self._split_text(raw_text, self.separators)

        chunks: List[TextChunk] = []
        current_offset = 0

        for idx, text in enumerate(text_slices):
            # Calculate approx offsets
            start = raw_text.find(text[:30], current_offset) if len(text) >= 30 else current_offset
            if start == -1:
                start = current_offset
            end = start + len(text)
            current_offset = max(start + 1, current_offset)

            chunks.append(TextChunk(
                chunk_id=f"{document.doc_id}_c{idx:03d}",
                doc_id=document.doc_id,
                content=text,
                chunk_index=idx,
                char_start=start,
                char_end=end,
                metadata={
                    **document.metadata,
                    "chunk_size": len(text)
                }
            ))

        return chunks

    def chunk_documents(self, documents: List[Document]) -> List[TextChunk]:
        """Chunk an entire collection of documents."""
        all_chunks: List[TextChunk] = []
        for doc in documents:
            all_chunks.extend(self.chunk_document(doc))
        return all_chunks
