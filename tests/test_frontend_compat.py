import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings, get_settings
from backend.main import app


def test_migrated_frontend_upload_and_document_routes():
    tmp_path = Path(".test-tmp/frontend-compat").resolve()
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)
    settings = Settings(
        due_diligence_provider="mock",
        rag_storage_dir=tmp_path / "rag",
        session_store=tmp_path / "sessions.json",
        local_storage_dir=tmp_path / "storage",
        local_embedding_provider="local-hashing",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        response = client.post(
            "/api/upload",
            files={"files": ("memo.txt", b"Revenue concentration risk in customer base.", "text/plain")},
            data={"auto_process": "false"},
        )

        assert response.status_code == 200
        payload = response.json()
        session_id = payload["session_id"]
        assert payload["rag"]["total_documents"] == 1
        assert payload["rag"]["total_chunks"] == 1

        tree_response = client.get(f"/api/session/{session_id}/documents")
        assert tree_response.status_code == 200
        tree = tree_response.json()
        assert tree["total_files"] == 1
        assert tree["documents"][0]["name"] == "memo.txt"

        status_response = client.get(f"/api/rag/status/{session_id}")
        assert status_response.status_code == 200
        assert status_response.json()["indexed"] is True

        chat_response = client.post(
            "/api/chat",
            json={"session_id": session_id, "content": "perform due diligence on the given documents"},
        )
        assert chat_response.status_code == 200
        chat = chat_response.json()
        assert "# Comprehensive Due Diligence Report" in chat["response"]
        assert "## Risk Register" in chat["response"]
        assert "## Financial Performance Overview" in chat["response"]
        assert "*Bar chart of risk findings by severity*" in chat["response"]
        assert "<c>finding-" in chat["response"]
        assert "memo.txt" in chat["response"]
        assert chat["citations"][0]["file_name"] == "memo.txt"
        assert chat["citations"][0]["id"].startswith("finding-")
        assert any(step["action"] == "investment_memo_synthesis" for step in chat["steps"])

        document_response = client.get(f"/api/document/{session_id}/memo.txt")
        assert document_response.status_code == 200
        assert "Revenue concentration" in document_response.text
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(tmp_path, ignore_errors=True)
