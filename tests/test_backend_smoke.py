from fastapi.testclient import TestClient

from backend.main import app


def test_health_uses_mock_provider():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "due-diligence-agent-open"
    assert payload["provider_key_available"] is True
    assert payload["rag_embedding_provider"] == "local-hashing"
