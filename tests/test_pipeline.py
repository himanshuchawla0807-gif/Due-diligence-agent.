import shutil
from pathlib import Path

import pytest

from backend.config import Settings
from backend.pipeline import run_domain_pipeline
from backend.providers import MockProvider
from backend.rag import LocalRagIndex


@pytest.mark.asyncio
async def test_domain_pipeline_runs_multiple_due_diligence_passes():
    tmp_path = Path(".test-tmp/domain-pipeline").resolve()
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)

    try:
        source = tmp_path / "data_room"
        source.mkdir(parents=True)
        (source / "financials.md").write_text(
            "ARR revenue growth is strong but customer concentration risk is high. EBITDA margin declined.",
            encoding="utf-8",
        )
        (source / "contracts.md").write_text(
            "Client contract includes change of control termination rights and assignment restrictions.",
            encoding="utf-8",
        )
        (source / "security.md").write_text(
            "SOC 2 is missing and security incident response process is incomplete.",
            encoding="utf-8",
        )

        settings = Settings(
            due_diligence_provider="mock",
            rag_storage_dir=tmp_path / "rag",
            session_store=tmp_path / "sessions.json",
            local_storage_dir=tmp_path / "storage",
            local_embedding_provider="local-hashing",
            due_diligence_domain_top_k=6,
        )
        rag = LocalRagIndex(settings)
        rag.index_directory("pipeline-session", source)

        result = await run_domain_pipeline(
            "pipeline-session",
            "perform due diligence on the given documents",
            MockProvider(settings),
            rag,
            settings,
        )

        assert result["findings"]
        assert len(result["steps"]) >= 3
        assert any("Financial Team" in finding.get("domain_pass", "") for finding in result["findings"])
        assert any(document["file_name"] == "financials.md" for document in result["documents"])
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)
