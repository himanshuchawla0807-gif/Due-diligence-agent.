"""Local RAG indexing with API-free embeddings.

The open-source agent should be able to index a user's local data room
without requiring Gemini, OpenAI, Anthropic, or any other embedding API.
This module stores a small deterministic vector index on disk using a
hashing bag-of-words embedding.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import Settings

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-\.]{1,}")

SUPPORTED_EXTENSIONS = {
    ".csv",
    ".docx",
    ".md",
    ".pdf",
    ".txt",
    ".xlsx",
}


class LocalRagIndex:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.rag_storage_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def index_path_for(self, session_id: str) -> Path:
        safe_session = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id)
        return self.root / safe_session / "index.json"

    def status(self, session_id: str) -> Dict[str, Any]:
        index_path = self.index_path_for(session_id)
        if not index_path.exists():
            return {
                "session_id": session_id,
                "indexed": False,
                "documents": 0,
                "chunks": 0,
            }
        data = self._load_index(index_path)
        return {
            "session_id": session_id,
            "indexed": True,
            "source_directory": data.get("source_directory"),
            "documents": len(data.get("documents", [])),
            "chunks": len(data.get("chunks", [])),
            "updated_at": data.get("updated_at"),
        }

    def index_directory(self, session_id: str, directory: str | Path, recursive: bool = True) -> Dict[str, Any]:
        source_dir = Path(directory).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise FileNotFoundError(f"Local data directory does not exist: {source_dir}")

        files = self._iter_files(source_dir, recursive=recursive)
        documents: List[Dict[str, Any]] = []
        chunks: List[Dict[str, Any]] = []
        skipped: List[Dict[str, str]] = []

        for path in files:
            try:
                if path.stat().st_size > self.settings.max_upload_mb * 1024 * 1024:
                    skipped.append({"path": str(path), "reason": "file too large"})
                    continue
                text = self._read_file(path)
                if not text.strip():
                    skipped.append({"path": str(path), "reason": "no extractable text"})
                    continue

                document_id = str(uuid.uuid4())
                documents.append(
                    {
                        "document_id": document_id,
                        "file_name": path.name,
                        "source_path": str(path),
                        "extension": path.suffix.lower(),
                        "size": path.stat().st_size,
                    }
                )
                for chunk_index, chunk_text in enumerate(self._chunk_text(text)):
                    chunks.append(
                        {
                            "chunk_id": f"{document_id}:{chunk_index}",
                            "document_id": document_id,
                            "file_name": path.name,
                            "source_path": str(path),
                            "chunk_index": chunk_index,
                            "text": chunk_text,
                            "vector": self._embed(chunk_text),
                        }
                    )
            except Exception as exc:
                skipped.append({"path": str(path), "reason": str(exc)})

        index_path = self.index_path_for(session_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "source_directory": str(source_dir),
            "recursive": recursive,
            "embedding": {
                "provider": "local-hashing",
                "dimensions": self.settings.local_embedding_dimensions,
            },
            "documents": documents,
            "chunks": chunks,
            "skipped": skipped,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "session_id": session_id,
            "source_directory": str(source_dir),
            "documents_indexed": len(documents),
            "chunks_indexed": len(chunks),
            "skipped": skipped,
            "index_path": str(index_path),
            "embedding_provider": "local-hashing",
        }

    def query(self, session_id: str, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        top_k = top_k or self.settings.rag_top_k
        index_path = self.index_path_for(session_id)
        if not index_path.exists() or not query.strip():
            return []
        data = self._load_index(index_path)
        query_vector = self._embed(query)
        ranked = []
        for chunk in data.get("chunks", []):
            score = self._cosine(query_vector, chunk.get("vector", []))
            if score > 0:
                ranked.append(
                    {
                        "score": round(score, 6),
                        "file_name": chunk.get("file_name"),
                        "source_path": chunk.get("source_path"),
                        "chunk_id": chunk.get("chunk_id"),
                        "chunk_index": chunk.get("chunk_index"),
                        "text": chunk.get("text", ""),
                    }
                )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

    def context_documents(self, session_id: str, query: str, top_k: int | None = None) -> List[Dict[str, str]]:
        return [
            {
                "file_name": item["file_name"],
                "source_path": item["source_path"],
                "text": item["text"],
            }
            for item in self.query(session_id, query, top_k=top_k)
        ]

    def _load_index(self, index_path: Path) -> Dict[str, Any]:
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _iter_files(self, source_dir: Path, recursive: bool) -> Iterable[Path]:
        iterator = source_dir.rglob("*") if recursive else source_dir.glob("*")
        for path in iterator:
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path

    def _read_file(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if suffix == ".docx":
            from docx import Document

            document = Document(str(path))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        if suffix == ".csv":
            import pandas as pd

            return pd.read_csv(path).to_csv(index=False)
        if suffix == ".xlsx":
            import pandas as pd

            frames = pd.read_excel(path, sheet_name=None)
            return "\n\n".join(f"Sheet: {name}\n{frame.to_csv(index=False)}" for name, frame in frames.items())
        return path.read_text(encoding="utf-8", errors="ignore")

    def _chunk_text(self, text: str) -> Iterable[str]:
        words = text.split()
        size = self.settings.rag_chunk_words
        overlap = min(self.settings.rag_chunk_overlap_words, max(size - 1, 0))
        if len(words) <= size:
            yield text.strip()
            return
        step = max(size - overlap, 1)
        for start in range(0, len(words), step):
            chunk = " ".join(words[start : start + size]).strip()
            if chunk:
                yield chunk
            if start + size >= len(words):
                break

    def _embed(self, text: str) -> List[float]:
        dimensions = self.settings.local_embedding_dimensions
        vector = [0.0] * dimensions
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [round(value / norm, 8) for value in vector]
        return vector

    def _cosine(self, left: List[float], right: List[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return sum(a * b for a, b in zip(left, right))
