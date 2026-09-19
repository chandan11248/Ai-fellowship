"""
Document ingestion module for RAG pipeline.
Loads Markdown, Text, PDF, JSON, and CSV documents with metadata extraction.
"""

import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Normalized document representation for RAG indexing."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata
        }


class DocumentLoader:
    """Loads and normalizes documents from file paths or directories."""

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".pdf"}

    @classmethod
    def load_file(cls, file_path: Path) -> List[Document]:
        """Load a single file into one or more Document instances."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            return []

        documents = []
        if ext in (".md", ".txt"):
            content = path.read_text(encoding="utf-8", errors="replace")
            documents.append(Document(
                doc_id=path.stem,
                content=content,
                metadata={
                    "source": str(path.name),
                    "file_type": ext[1:],
                    "char_count": len(content)
                }
            ))
        elif ext == ".pdf":
            extracted_text = ""
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                pages = []
                for i, page in enumerate(reader.pages):
                    p_text = page.extract_text() or ""
                    if p_text.strip():
                        pages.append(f"--- Page {i+1} ---\n{p_text}")
                extracted_text = "\n\n".join(pages)
            except Exception:
                # Fallback to subprocess pdftotext if available
                import subprocess
                try:
                    res = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
                    if res.returncode == 0:
                        extracted_text = res.stdout
                except Exception:
                    pass

            if extracted_text.strip():
                documents.append(Document(
                    doc_id=path.stem,
                    content=extracted_text,
                    metadata={
                        "source": str(path.name),
                        "file_type": "pdf",
                        "char_count": len(extracted_text)
                    }
                ))
        elif ext == ".json":
            content = path.read_text(encoding="utf-8", errors="replace")
            data = json.loads(content)
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    text_content = json.dumps(item, indent=2) if isinstance(item, dict) else str(item)
                    documents.append(Document(
                        doc_id=f"{path.stem}_{idx}",
                        content=text_content,
                        metadata={"source": str(path.name), "index": idx, "file_type": "json"}
                    ))
            elif isinstance(data, dict):
                documents.append(Document(
                    doc_id=path.stem,
                    content=json.dumps(data, indent=2),
                    metadata={"source": str(path.name), "file_type": "json"}
                ))
        elif ext == ".csv":
            with open(path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                    documents.append(Document(
                        doc_id=f"{path.stem}_row_{idx}",
                        content=row_str,
                        metadata={"source": str(path.name), "row_index": idx, "file_type": "csv", **row}
                    ))

        return documents

    @classmethod
    def load_directory(cls, dir_path: Path) -> List[Document]:
        """Recursively scan and load all supported documents from directory."""
        directory = Path(dir_path)
        if not directory.exists():
            return []

        all_docs: List[Document] = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_p = Path(root) / file
                if file_p.suffix.lower() in cls.SUPPORTED_EXTENSIONS:
                    all_docs.extend(cls.load_file(file_p))
        return all_docs
