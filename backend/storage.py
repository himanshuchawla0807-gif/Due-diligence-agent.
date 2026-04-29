"""Local upload storage and session state."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import UploadFile

from .config import Settings


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
                "created_at": datetime.utcnow().isoformat(),
                "uploaded_files": [],
                "findings": [],
            }
            self.save()
        return self.sessions[session_id]

    async def save_uploads(self, session_id: str, files: List[UploadFile]) -> List[Dict[str, Any]]:
        session = self.get_or_create(session_id)
        session_dir = self.upload_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        saved_files: List[Dict[str, Any]] = []
        for upload in files:
            file_id = str(uuid.uuid4())
            safe_name = Path(upload.filename or f"{file_id}.bin").name
            stored_name = f"{file_id}_{safe_name}"
            path = session_dir / stored_name
            with path.open("wb") as out_file:
                shutil.copyfileobj(upload.file, out_file)
            info = {
                "file_id": file_id,
                "filename": stored_name,
                "display_name": safe_name,
                "path": str(path),
                "size": path.stat().st_size,
                "upload_time": datetime.utcnow().isoformat(),
                "status": "stored",
            }
            session["uploaded_files"].append(info)
            saved_files.append(info)

        self.save()
        return saved_files

    def documents(self, session_id: str) -> List[Dict[str, str]]:
        session = self.get_or_create(session_id)
        docs: List[Dict[str, str]] = []
        for file_info in session.get("uploaded_files", []):
            path = Path(file_info.get("path", ""))
            docs.append({
                "file_name": file_info.get("display_name", path.name),
                "text": self._read_file(path)[:24000],
            })
        return docs

    def update_findings(self, session_id: str, findings: List[Dict[str, Any]]) -> None:
        session = self.get_or_create(session_id)
        session["findings"] = findings
        session["updated_at"] = datetime.utcnow().isoformat()
        self.save()

    def _read_file(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(str(path))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
