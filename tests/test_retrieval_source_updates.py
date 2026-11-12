from backend.config import Settings
from backend.rag import LocalRagIndex


def test_index_refreshes_changed_source_label_even_if_content_is_unchanged(tmp_path):
    rag = LocalRagIndex(Settings(rag_storage_dir=tmp_path, local_embedding_provider="local-hashing"))
    document = {"file_name": "old.txt", "source_path": "stored-file", "text": "Revenue risk"}
    rag.index_documents("case", [document])
    rag.index_documents("case", [{**document, "file_name": "reports/current.txt"}])

    assert rag.document_names("case") == ["reports/current.txt"]
    assert rag.context_documents("case", "revenue")[0]["file_name"] == "reports/current.txt"


def test_retrieval_limits_distinct_sources_independently(tmp_path):
    rag = LocalRagIndex(Settings(rag_storage_dir=tmp_path, local_embedding_provider="local-hashing"))
    rag.index_documents("case", [
        {"file_name": "report.txt", "source_path": "sales/report.txt", "text": "Revenue in sales"},
        {"file_name": "report.txt", "source_path": "legal/report.txt", "text": "Revenue in legal"},
    ])

    direct = rag.query("case", "revenue", top_k=10, per_file_limit=1)
    combined = rag.multi_query_context_documents("case", ["revenue"], per_file_limit=1)
    assert {item["source_path"] for item in direct} == {"sales/report.txt", "legal/report.txt"}
    assert {item["source_path"] for item in combined} == {"sales/report.txt", "legal/report.txt"}
