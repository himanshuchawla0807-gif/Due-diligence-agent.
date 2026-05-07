from fastapi.testclient import TestClient

from backend.main import app


def test_migrated_frontend_upload_and_document_routes():
    client = TestClient(app)
    response = client.post(
        "/api/upload",
        files={"files": ("memo.txt", b"Revenue concentration risk in customer base.", "text/plain")},
        data={"auto_process": "false"},
    )

    assert response.status_code == 200
    session_id = response.json()["session_id"]

    tree_response = client.get(f"/api/session/{session_id}/documents")
    assert tree_response.status_code == 200
    tree = tree_response.json()
    assert tree["total_files"] == 1
    assert tree["documents"][0]["name"] == "memo.txt"

    document_response = client.get(f"/api/document/{session_id}/memo.txt")
    assert document_response.status_code == 200
    assert "Revenue concentration" in document_response.text
