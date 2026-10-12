import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.auth import Principal, get_principal
from backend.config import Settings, get_settings
from backend.jobs import JobManager
from backend.main import app
from backend.persistence import Database, validate_id
from backend.providers import MockProvider, ProviderError
from backend.rag import LocalRagIndex
from backend.api import citations_from_findings


def settings_for(tmp_path, **extra):
    return Settings(app_env="test", due_diligence_provider="mock", local_embedding_provider="local-hashing",
        local_storage_dir=tmp_path/"uploads", session_store=tmp_path/"sessions.json", rag_storage_dir=tmp_path/"rag", **extra)


@pytest.mark.parametrize("value", ["../escape", "/absolute", "C:\\escape", "a/b", "..", ""])
def test_session_ids_cannot_escape_or_alias(value):
    with pytest.raises(ValueError):
        validate_id(value)


def test_transactions_preserve_concurrent_updates(tmp_path):
    database = Database(tmp_path/"state.sqlite3")
    def append(value):
        database.update("case", lambda state: state["uploaded_files"].append(value))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(append, range(32)))
    assert sorted(Database(tmp_path/"state.sqlite3").session("case")["uploaded_files"]) == list(range(32))


def test_unknown_source_and_invented_quote_rejected(tmp_path):
    provider = MockProvider(settings_for(tmp_path))
    documents = [{"file_name": "terms.pdf", "source_path": "private/terms.pdf", "text": "Termination on change of control.", "page": 5, "chunk_id": "chunk-5"}]
    finding = {"finding": "Review termination", "category": "Legal", "severity": "High", "recommendation": "Request waiver", "source_file": "terms.pdf", "text_snippet": "Termination on change of control."}
    for mutation in ({"source_file": None}, {"source_file": "invented.pdf"}, {"text_snippet": "Nonexistent quote"}, {"severity": "Extreme"}):
        with pytest.raises(ProviderError):
            provider._normalize_finding({**finding, **mutation}, documents)
    verified = provider._normalize_finding(finding, documents)
    citations = citations_from_findings([verified], documents)
    assert citations[0]["page"] == 5
    assert citations[0]["chunk_id"] == "chunk-5"
    assert citations[0]["source_path"] == "terms.pdf"


def test_changed_content_invalidates_index_and_runtime_cache_not_persisted(tmp_path):
    rag = LocalRagIndex(settings_for(tmp_path))
    rag.index_documents("case", [{"file_name": "facts.txt", "source_path": "same", "text": "Revenue is ten million"}])
    rag.query("case", "revenue")
    rag.index_documents("case", [{"file_name": "facts.txt", "source_path": "same", "text": "Revenue is twenty million"}])
    assert rag.status("case")["documents"] == 1
    assert "twenty" in rag.query("case", "revenue")[0]["text"]
    payload = json.loads(rag.index_path_for("case").read_text())
    assert not any(key.startswith("_") for chunk in payload["chunks"] for key in chunk)


def test_semantic_encoder_failure_never_persists_wrong_vector_space(tmp_path, monkeypatch):
    rag = LocalRagIndex(settings_for(tmp_path))
    class Broken:
        def encode(self, *args, **kwargs):
            raise RuntimeError("encoder unavailable")
    monkeypatch.setattr(rag, "_embedding_metadata", lambda: {"provider": "sentence-transformers", "model": "fixture", "dimensions": 384})
    monkeypatch.setattr(rag, "_semantic_model", lambda: Broken())
    with pytest.raises(ValueError, match="Semantic embedding failed"):
        rag.index_documents("case", [{"file_name": "facts.txt", "text": "revenue risk"}])
    assert not rag.index_path_for("case").exists()


@pytest.mark.asyncio
async def test_jobs_cancel_real_work_and_recover_queued_state(tmp_path):
    database = Database(tmp_path/"state.sqlite3")
    started = asyncio.Event()
    async def runner(session, payload):
        started.set()
        await asyncio.sleep(10)
        return {"status": "completed"}
    manager = JobManager(database, runner)
    job = manager.submit("case", {"focus": "revenue"}, "same")
    assert manager.submit("case", {"focus": "revenue"}, "same") == job
    with pytest.raises(ValueError):
        manager.submit("case", {"focus": "different"}, "same")
    await started.wait()
    assert manager.cancel_session("case") == 1
    await asyncio.gather(*list(manager.tasks.values()), return_exceptions=True)
    assert manager.get(job)["status"] == "cancelled"
    recovery_job = manager.submit("recovery", {"focus": "legal"})
    await manager.close()
    async def recovered(session, payload):
        return {"status": "completed", "focus": payload["focus"]}
    replacement = JobManager(Database(tmp_path/"state.sqlite3"), recovered)
    replacement.recover()
    result = await replacement.wait(recovery_job)
    assert result["focus"] == "legal"
    assert replacement.get(recovery_job)["status"] == "completed"
    await replacement.close()


def test_verified_principal_isolates_documents_and_http_directory_disabled(tmp_path):
    settings = settings_for(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_principal] = lambda: Principal("alice")
    try:
        with TestClient(app) as client:
            response = client.post("/api/upload", data={"session_id": "case"}, files={"files": ("memo.txt", b"Revenue risk", "text/plain")})
            assert response.status_code == 200
            app.dependency_overrides[get_principal] = lambda: Principal("bob")
            assert client.get("/api/document/case/memo.txt").status_code == 404
            assert client.post("/api/rag/index-local-directory", json={"session_id": "case", "directory": str(tmp_path)}).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_local_auth_rejects_remote_clients_and_production(tmp_path):
    app.dependency_overrides[get_settings] = lambda: settings_for(tmp_path, auth_mode="local")
    try:
        with TestClient(app, client=("203.0.113.10", 1234)) as client:
            assert client.get("/api/session/case/documents").status_code == 403
        app.dependency_overrides[get_settings] = lambda: settings_for(tmp_path).model_copy(update={"app_env": "production"})
        with TestClient(app) as client:
            assert client.get("/api/session/case/documents").status_code == 403
    finally:
        app.dependency_overrides.clear()
