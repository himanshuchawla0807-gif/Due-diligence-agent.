import shutil
from pathlib import Path

from backend.config import Settings
from backend.rag import LocalRagIndex


def test_local_rag_indexes_directory_without_api_key():
    tmp_path = Path(".test-tmp/local-rag").resolve()
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)
    source = tmp_path / "data_room"
    source.mkdir(parents=True)
    (source / "commercial.md").write_text(
        "Revenue concentration risk: top customer contributes 62 percent of ARR.",
        encoding="utf-8",
    )

    settings = Settings(
        due_diligence_provider="mock",
        rag_storage_dir=tmp_path / "rag",
        session_store=tmp_path / "sessions.json",
        local_storage_dir=tmp_path / "storage",
    )
    rag = LocalRagIndex(settings)

    result = rag.index_directory("test-session", source)
    matches = rag.query("test-session", "customer revenue concentration", top_k=3)

    assert result["documents_indexed"] == 1
    assert result["embedding_provider"] == "local-hashing"
    assert matches
    assert matches[0]["file_name"] == "commercial.md"
    shutil.rmtree(tmp_path, ignore_errors=True)
