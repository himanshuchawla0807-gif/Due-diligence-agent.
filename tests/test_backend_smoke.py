from fastapi.testclient import TestClient

from backend.config import Settings, get_settings
from backend.main import app


def test_health_uses_mock_provider():
    settings = Settings(due_diligence_provider="mock", local_embedding_provider="local-hashing")
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["service"] == "due-diligence-agent-open"
        assert payload["provider_key_available"] is True
        assert payload["rag_embedding_provider"] == "local-hashing"
    finally:
        app.dependency_overrides.clear()
