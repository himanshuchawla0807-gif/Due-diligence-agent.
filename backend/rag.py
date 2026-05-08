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
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .config import Settings
from .document_extractors import extract_text

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-\.]{1,}")
_SEMANTIC_MODEL_CACHE: Dict[str, Any] = {}

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
            "embedding": data.get("embedding", {}),
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
        embedding = self._embedding_metadata()

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
                        }
                    )
            except Exception as exc:
                skipped.append({"path": str(path), "reason": str(exc)})

        vectors = self._embed_many([chunk["text"] for chunk in chunks], embedding)
        for chunk, vector in zip(chunks, vectors):
            chunk["vector"] = vector

        index_path = self.index_path_for(session_id)
        index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "source_directory": str(source_dir),
            "recursive": recursive,
            "embedding": embedding,
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
            "embedding_provider": embedding["provider"],
            "embedding_model": embedding.get("model"),
        }

    def index_documents(
        self,
        session_id: str,
        documents: List[Dict[str, Any]],
        source_directory: str = "uploaded files",
        append: bool = True,
    ) -> Dict[str, Any]:
        index_path = self.index_path_for(session_id)
        embedding = self._embedding_metadata()
        current = self._load_index(index_path) if append and index_path.exists() else {}
        if current and not self._compatible_embedding(current.get("embedding", {}), embedding):
            current = {}
        indexed_documents: List[Dict[str, Any]] = list(current.get("documents", []))
        chunks: List[Dict[str, Any]] = list(current.get("chunks", []))
        skipped: List[Dict[str, str]] = list(current.get("skipped", []))
        seen_sources = {
            document.get("source_path") or document.get("file_name")
            for document in indexed_documents
        }

        documents_indexed = 0
        chunks_indexed = 0
        for document in documents:
            file_name = document.get("file_name") or document.get("display_name") or "uploaded-document"
            source_path = document.get("source_path") or document.get("path") or file_name
            source_key = source_path or file_name
            if append and source_key in seen_sources:
                continue

            text = (document.get("text") or "").strip()
            if not text:
                skipped.append({"path": str(source_path), "reason": "no extractable text"})
                continue

            document_id = str(uuid.uuid4())
            indexed_documents.append(
                {
                    "document_id": document_id,
                    "file_name": file_name,
                    "source_path": str(source_path),
                    "extension": Path(str(file_name)).suffix.lower(),
                    "size": document.get("size", len(text.encode("utf-8"))),
                }
            )
            seen_sources.add(source_key)
            documents_indexed += 1

            new_chunks = []
            for chunk_index, chunk_text in enumerate(self._chunk_text(text)):
                new_chunks.append(
                    {
                        "chunk_id": f"{document_id}:{chunk_index}",
                        "document_id": document_id,
                        "file_name": file_name,
                        "source_path": str(source_path),
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                    }
                )
            vectors = self._embed_many([chunk["text"] for chunk in new_chunks], embedding)
            for chunk, vector in zip(new_chunks, vectors):
                chunk["vector"] = vector
                chunks.append(
                    chunk
                )
                chunks_indexed += 1

        index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "source_directory": source_directory,
            "recursive": False,
            "embedding": embedding,
            "documents": indexed_documents,
            "chunks": chunks,
            "skipped": skipped,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "session_id": session_id,
            "source_directory": source_directory,
            "documents_indexed": documents_indexed,
            "chunks_indexed": chunks_indexed,
            "skipped": skipped,
            "index_path": str(index_path),
            "embedding_provider": embedding["provider"],
            "embedding_model": embedding.get("model"),
            "total_documents": len(indexed_documents),
            "total_chunks": len(chunks),
        }

    def query(
        self,
        session_id: str,
        query: str,
        top_k: int | None = None,
        diversify_files: bool = True,
        per_file_limit: int = 3,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or self.settings.rag_top_k
        index_path = self.index_path_for(session_id)
        if not index_path.exists():
            return []
        data = self._load_index(index_path)
        chunks = data.get("chunks", [])
        if not chunks:
            return []

        query_text = query.strip() or "comprehensive due diligence risk review across all uploaded documents"
        embedding = data.get("embedding", {"provider": "local-hashing", "dimensions": self.settings.local_embedding_dimensions})
        query_vector = self._embed(query_text, embedding)
        query_terms = self._tokens(query_text)
        broad_query = self._is_broad_query(query_text)
        document_frequency = self._document_frequency(chunks)
        total_chunks = max(len(chunks), 1)
        ranked = []

        for chunk in chunks:
            text = chunk.get("text", "")
            vector_score = self._cosine(query_vector, chunk.get("vector", []))
            lexical_score = self._lexical_score(query_terms, text, document_frequency, total_chunks)
            coverage_bonus = 0.04 if broad_query else 0.0
            score = (0.55 * vector_score) + (0.45 * lexical_score) + coverage_bonus
            if score > 0 or broad_query:
                ranked.append(
                    {
                        "score": round(score, 6),
                        "vector_score": round(vector_score, 6),
                        "lexical_score": round(lexical_score, 6),
                        "file_name": chunk.get("file_name"),
                        "source_path": chunk.get("source_path"),
                        "chunk_id": chunk.get("chunk_id"),
                        "chunk_index": chunk.get("chunk_index"),
                        "text": text,
                    }
                )
        ranked.sort(key=lambda item: item["score"], reverse=True)

        if not diversify_files:
            return ranked[:top_k]

        selected = []
        selected_by_file: Dict[str, int] = defaultdict(int)
        file_limit = 2 if broad_query else per_file_limit
        for item in ranked:
            file_name = item.get("file_name") or "unknown"
            if selected_by_file[file_name] >= file_limit:
                continue
            selected.append(item)
            selected_by_file[file_name] += 1
            if len(selected) >= top_k:
                break
        return selected

    def context_documents(self, session_id: str, query: str, top_k: int | None = None) -> List[Dict[str, Any]]:
        return [
            {
                "file_name": item["file_name"],
                "source_path": item["source_path"],
                "text": item["text"],
                "score": item["score"],
                "chunk_index": item.get("chunk_index"),
            }
            for item in self.query(session_id, query, top_k=top_k, diversify_files=True)
        ]

    def document_names(self, session_id: str, limit: int | None = None) -> List[str]:
        index_path = self.index_path_for(session_id)
        if not index_path.exists():
            return []
        data = self._load_index(index_path)
        names = [document.get("file_name") for document in data.get("documents", []) if document.get("file_name")]
        return names[:limit] if limit else names

    def multi_query_context_documents(
        self,
        session_id: str,
        queries: List[str],
        top_k_per_query: int = 12,
        max_results: int | None = None,
        per_file_limit: int = 5,
    ) -> List[Dict[str, Any]]:
        max_results = max_results or self.settings.rag_report_top_k
        merged: Dict[str, Dict[str, Any]] = {}
        for query in queries:
            for item in self.query(
                session_id,
                query,
                top_k=top_k_per_query,
                diversify_files=False,
            ):
                key = item.get("chunk_id") or f"{item.get('source_path')}:{item.get('chunk_index')}"
                existing = merged.get(key)
                if not existing or item.get("score", 0) > existing.get("score", 0):
                    merged[key] = item

        ranked = sorted(merged.values(), key=lambda item: item.get("score", 0), reverse=True)
        selected = []
        selected_by_file: Dict[str, int] = defaultdict(int)
        for item in ranked:
            file_name = item.get("file_name") or "unknown"
            if selected_by_file[file_name] >= per_file_limit:
                continue
            selected.append(
                {
                    "file_name": item["file_name"],
                    "source_path": item["source_path"],
                    "text": item["text"],
                    "score": item["score"],
                    "chunk_index": item.get("chunk_index"),
                }
            )
            selected_by_file[file_name] += 1
            if len(selected) >= max_results:
                break
        return selected

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
        return extract_text(path)

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

    def _embedding_metadata(self) -> Dict[str, Any]:
        provider = self.settings.local_embedding_provider.lower().strip()
        if provider in {"auto", "sentence-transformers", "semantic"} and self._semantic_model_available():
            return {
                "provider": "sentence-transformers",
                "model": self.settings.local_embedding_model,
                "dimensions": self.settings.local_embedding_dimensions,
            }
        return {
            "provider": "local-hashing",
            "model": None,
            "dimensions": self.settings.local_embedding_dimensions,
        }

    def _compatible_embedding(self, existing: Dict[str, Any], current: Dict[str, Any]) -> bool:
        return (
            existing.get("provider") == current.get("provider")
            and existing.get("model") == current.get("model")
            and int(existing.get("dimensions", 0) or 0) == int(current.get("dimensions", 0) or 0)
        )

    def _semantic_model_available(self) -> bool:
        try:
            self._semantic_model()
            return True
        except Exception:
            return False

    def _semantic_model(self) -> Any:
        model_name = self.settings.local_embedding_model
        if model_name not in _SEMANTIC_MODEL_CACHE:
            from sentence_transformers import SentenceTransformer

            _SEMANTIC_MODEL_CACHE[model_name] = SentenceTransformer(model_name)
        return _SEMANTIC_MODEL_CACHE[model_name]

    def _embed_many(self, texts: List[str], embedding: Dict[str, Any] | None = None) -> List[List[float]]:
        if not texts:
            return []
        embedding = embedding or self._embedding_metadata()
        if embedding.get("provider") == "sentence-transformers":
            try:
                model = self._semantic_model()
                vectors = model.encode(
                    texts,
                    batch_size=self.settings.local_embedding_batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                return [[round(float(value), 8) for value in vector] for vector in vectors]
            except Exception:
                fallback = {"provider": "local-hashing", "dimensions": self.settings.local_embedding_dimensions}
                return [self._embed(text, fallback) for text in texts]
        return [self._embed(text, embedding) for text in texts]

    def _embed(self, text: str, embedding: Dict[str, Any] | None = None) -> List[float]:
        embedding = embedding or self._embedding_metadata()
        if embedding.get("provider") == "sentence-transformers":
            return self._embed_many([text], embedding)[0]
        dimensions = self.settings.local_embedding_dimensions
        vector = [0.0] * dimensions
        for token in self._tokens(text):
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

    def _tokens(self, text: str) -> List[str]:
        return TOKEN_RE.findall(text.lower())

    def _document_frequency(self, chunks: List[Dict[str, Any]]) -> Counter:
        frequency: Counter = Counter()
        for chunk in chunks:
            frequency.update(set(self._tokens(chunk.get("text", ""))))
        return frequency

    def _lexical_score(
        self,
        query_terms: List[str],
        text: str,
        document_frequency: Counter,
        total_chunks: int,
    ) -> float:
        if not query_terms or not text:
            return 0.0
        term_counts = Counter(self._tokens(text))
        if not term_counts:
            return 0.0

        query_counts = Counter(query_terms)
        score = 0.0
        for term, query_count in query_counts.items():
            count = term_counts.get(term, 0)
            if not count:
                continue
            inverse_document_frequency = math.log((total_chunks + 1) / (document_frequency.get(term, 0) + 1)) + 1.0
            score += min(query_count, 3) * math.log1p(count) * inverse_document_frequency
        return score / math.sqrt(sum(term_counts.values()))

    def _is_broad_query(self, query: str) -> bool:
        normalized = query.lower()
        broad_terms = (
            "due diligence",
            "given documents",
            "all documents",
            "data room",
            "comprehensive",
            "full review",
            "vc review",
            "analyze documents",
            "risk review",
        )
        return any(term in normalized for term in broad_terms)
