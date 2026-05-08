"""Local upload storage and session state."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from .config import Settings
from .document_extractors import extract_text


class SessionStore:
    def __init__(self, settings: Settings):
        self.root = settings.local_storage_dir
        self.upload_root = self.root / "uploads"
        self.session_store = settings.session_store
        self.root.mkdir(parents=True, exist_ok=True)
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self.session_store.parent.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.session_store.exists():
            return {}
        try:
            return json.loads(self.session_store.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self) -> None:
        self.session_store.write_text(json.dumps(self.sessions, indent=2), encoding="utf-8")

    def get_or_create(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "created_at": datetime.now(UTC).isoformat(),
                "uploaded_files": [],
                "findings": [],
            }
            self.save()
        return self.sessions[session_id]

    async def save_uploads(
        self,
        session_id: str,
        files: List[UploadFile],
        relative_paths: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        session = self.get_or_create(session_id)
        session_dir = self.upload_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        saved_files: List[Dict[str, Any]] = []
        for index, upload in enumerate(files):
            file_id = str(uuid.uuid4())
            original_name = upload.filename or f"{file_id}.bin"
            relative_path = self._safe_relative_path(
                (relative_paths or [])[index] if relative_paths and index < len(relative_paths) else original_name
            )
            safe_name = Path(relative_path).name
            stored_name = f"{file_id}_{safe_name}"
            path = session_dir / stored_name
            with path.open("wb") as out_file:
                shutil.copyfileobj(upload.file, out_file)
            info = {
                "file_id": file_id,
                "filename": stored_name,
                "display_name": safe_name,
                "relative_path": relative_path,
                "path": str(path),
                "size": path.stat().st_size,
                "upload_time": datetime.now(UTC).isoformat(),
                "status": "stored",
            }
            session["uploaded_files"].append(info)
            saved_files.append(info)

        self.save()
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
        normalized = file_name.replace("\\", "/").split("/")[-1]
        for file_info in self.uploaded_files(session_id):
            path = Path(file_info.get("path", ""))
            candidates = {
                path.name,
                file_info.get("filename", ""),
                file_info.get("display_name", ""),
                file_info.get("relative_path", ""),
            }
            if file_name in candidates or normalized in candidates:
                return path if path.exists() else None
        return None

    def documents(self, session_id: str) -> List[Dict[str, str]]:
        session = self.get_or_create(session_id)
        docs: List[Dict[str, str]] = []
        for file_info in session.get("uploaded_files", []):
            path = Path(file_info.get("path", ""))
            docs.append({
                "file_name": file_info.get("relative_path") or file_info.get("display_name", path.name),
                "source_path": str(path),
                "size": file_info.get("size", 0),
                "text": self._read_file(path),
            })
        return docs

    def update_findings(self, session_id: str, findings: List[Dict[str, Any]]) -> None:
        session = self.get_or_create(session_id)
        session["findings"] = findings
        session["updated_at"] = datetime.now(UTC).isoformat()
        self.save()

    def _read_file(self, path: Path) -> str:
        try:
            return extract_text(path)
        except Exception:
            return ""

    def _safe_relative_path(self, file_path: str) -> str:
        normalized = file_path.replace("\\", "/")
        parts = [
            part
            for part in normalized.split("/")
            if part and part not in {".", ".."} and ":" not in part
        ]
        if not parts:
            return Path(file_path or "uploaded-file").name
        return "/".join(parts)
