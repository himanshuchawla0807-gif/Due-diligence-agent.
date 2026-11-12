"""Local upload storage and session state."""

from __future__ import annotations

import json
import hashlib
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from .config import Settings
from .document_extractors import extract_text, extract_segments
from .persistence import Database, validate_id


class SessionStore:
    def __init__(self, settings: Settings):
        self.root = settings.local_storage_dir
        self.upload_root = self.root / "uploads"
        self.session_store = settings.session_store
        self.root.mkdir(parents=True, exist_ok=True)
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.session_store.parent.mkdir(parents=True, exist_ok=True)
        database_path = self.session_store.with_suffix(".sqlite3")
        fresh = True
        if database_path.exists():
            with sqlite3.connect(database_path) as connection:
                fresh = not connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'"
                ).fetchone()
        legacy = self._load() if fresh and self.session_store.exists() else {}
        if not isinstance(legacy, dict):
            raise ValueError("Legacy session store is corrupt; restore it before migration")
        for session_id, payload in legacy.items():
            validate_id(session_id)
            if not isinstance(payload, dict):
                raise ValueError("Legacy session store is corrupt; restore it before migration")
        self.database = Database(database_path, legacy_sessions=legacy)
        self.settings = settings
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.session_store.exists():
            return {}
        try:
            return json.loads(self.session_store.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError("Legacy session store is corrupt; restore it before migration") from exc

    def save(self) -> None:
        # Compatibility for explicit CLI callers; API mutations use transactional updates.
        for session_id, payload in self.sessions.items():
            self.database.update(session_id, lambda state, payload=payload: state.update(payload))

    def get_or_create(self, session_id: str) -> Dict[str, Any]:
        self.sessions[session_id] = self.database.session(session_id)
        return self.sessions[session_id]

    async def save_uploads(
        self,
        session_id: str,
        files: List[UploadFile],
        relative_paths: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        validate_id(session_id)
        if not files or len(files) > self.settings.max_upload_files:
            raise ValueError("Upload file count exceeds limit")
        session_dir = (self.upload_root / session_id).resolve()
        if not session_dir.is_relative_to(self.upload_root.resolve()):
            raise ValueError("Upload path escapes storage")
        session_dir.mkdir(parents=True, exist_ok=True)

        saved_files: List[Dict[str, Any]] = []
        total_bytes = 0
        created: list[Path] = []
        try:
            for index, upload in enumerate(files):
                file_id = str(uuid.uuid4())
                original_name = upload.filename or f"{file_id}.bin"
                relative_path = self._safe_relative_path(
                    (relative_paths or [])[index] if relative_paths and index < len(relative_paths) else original_name
                )
                safe_name = Path(relative_path).name
                stored_name = f"{file_id}_{safe_name}"
                path = session_dir / stored_name
                suffix = path.suffix.lower()
                if suffix not in {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"}:
                    raise ValueError("Unsupported upload type")
                digest = hashlib.sha256()
                file_bytes = 0
                with path.open("xb") as out_file:
                    created.append(path)
                    first = True
                    while block := await upload.read(1024 * 1024):
                        if first and ((suffix == ".pdf" and not block.startswith(b"%PDF-")) or (suffix in {".docx", ".xlsx"} and not block.startswith(b"PK"))):
                            raise ValueError("Upload signature does not match document type")
                        first = False
                        file_bytes += len(block)
                        total_bytes += len(block)
                        if file_bytes > self.settings.max_upload_mb * 1024 * 1024 or total_bytes > self.settings.max_upload_total_mb * 1024 * 1024:
                            raise ValueError("Upload size exceeds limit")
                        digest.update(block)
                        out_file.write(block)
                if not file_bytes:
                    raise ValueError("Empty upload")
                info = {
                    "file_id": file_id,
                    "filename": stored_name,
                    "display_name": safe_name,
                    "relative_path": relative_path,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "upload_time": datetime.now(UTC).isoformat(),
                    "status": "stored",
                    "content_hash": digest.hexdigest(),
                }
                saved_files.append(info)

            self.database.update(session_id, lambda state: state["uploaded_files"].extend(saved_files))
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            raise
        return saved_files

    def uploaded_files(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self.get_or_create(session_id).get("uploaded_files", []))

    def document_tree(self, session_id: str) -> Dict[str, Any]:
        files = self.uploaded_files(session_id)
        documents = [
            {
                "name": file_info.get("display_name") or file_info.get("filename"),
                "type": "file",
                "path": file_info.get("relative_path") or file_info.get("display_name") or file_info.get("filename"),
                "size": file_info.get("size", 0),
            }
            for file_info in files
        ]
        return {
            "session_id": session_id,
            "documents": documents,
            "total_files": len(documents),
            "total_size": sum(item.get("size", 0) for item in documents),
        }

    def resolve_file(self, session_id: str, file_name: str) -> Optional[Path]:
        normalized = file_name.replace("\\", "/")
        root = (self.upload_root / session_id).resolve()
        exact, basename = [], []
        for info in self.uploaded_files(session_id):
            path = Path(info.get("path", "")).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                continue
            if normalized in {info.get("relative_path"), info.get("filename"), path.name}:
                exact.append(path)
            elif "/" not in normalized and normalized == info.get("display_name"):
                basename.append(path)
        matches = exact or basename
        return matches[0] if len(matches) == 1 else None

    def documents(self, session_id: str) -> List[Dict[str, str]]:
        session = self.get_or_create(session_id)
        docs: List[Dict[str, str]] = []
        for file_info in session.get("uploaded_files", []):
            path = Path(file_info.get("path", ""))
            try:
                path = path.resolve()
                if not path.is_relative_to((self.upload_root / session_id).resolve()) or not path.is_file():
                    raise ValueError("Stored document is missing or outside the session directory")
                with path.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                cache_key = f"v3:{path.suffix.lower()}:{digest}"
                with self.database.connect() as connection:
                    cached = connection.execute("SELECT payload FROM extraction WHERE hash=?", (cache_key,)).fetchone()
                if cached:
                    segments = json.loads(cached[0])
                else:
                    segments = extract_segments(path)
                    with self.database.connect() as connection:
                        connection.execute("INSERT OR REPLACE INTO extraction VALUES (?, ?)", (cache_key, json.dumps(segments)))
                error = None
            except Exception as exc:
                digest, segments, error = None, [], str(exc)
            docs.append({
                "file_name": file_info.get("relative_path") or file_info.get("display_name", path.name),
                "source_path": str(path),
                "size": file_info.get("size", 0),
                "text": "\n".join(segment["text"] for segment in segments),
                "segments": segments,
                "content_hash": digest,
                "extraction_error": error,
            })
        return docs

    def update_findings(self, session_id: str, findings: List[Dict[str, Any]], *, connection=None) -> None:
        def change(state):
            state.update(findings=findings, updated_at=datetime.now(UTC).isoformat())

        if connection is None:
            self.database.update(session_id, change)
        else:
            self.database.update_session_in_transaction(connection, session_id, change)

    def _read_file(self, path: Path) -> str:
        try:
            return extract_text(path)
        except Exception as exc:
            raise ValueError(f"Document extraction failed: {path.name}") from exc

    def _safe_relative_path(self, file_path: str) -> str:
        normalized = file_path.replace("\\", "/")
        if normalized.startswith("/") or any(part in {".", ".."} or ":" in part for part in normalized.split("/")):
            raise ValueError("Invalid document path")
        parts = [
            part
            for part in normalized.split("/")
            if part and part not in {".", ".."} and ":" not in part
        ]
        if not parts:
            return Path(file_path or "uploaded-file").name
        return "/".join(parts)
