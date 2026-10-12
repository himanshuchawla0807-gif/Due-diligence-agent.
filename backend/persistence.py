"""Local transactional state and atomic index writes. Not a Cloud Run datastore."""
import json
import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

def validate_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value):
        raise ValueError("Invalid session identifier")
    return value

def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS extraction(hash TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, result TEXT, error TEXT, cancelled INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def session(self, session_id: str) -> dict:
        validate_id(session_id)
        with self.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO sessions VALUES (?, ?)", (session_id, json.dumps({"session_id": session_id, "uploaded_files": [], "findings": []})))
            return json.loads(connection.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()[0])

    def update(self, session_id: str, change) -> dict:
        validate_id(session_id)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT OR IGNORE INTO sessions VALUES (?, ?)", (session_id, json.dumps({"session_id": session_id, "uploaded_files": [], "findings": []})))
            payload = json.loads(connection.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()[0])
            change(payload)
            connection.execute("UPDATE sessions SET payload=? WHERE id=?", (json.dumps(payload), session_id))
            return payload
