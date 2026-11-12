import hashlib

from backend.config import Settings
from backend.rag import LocalRagIndex


def test_directory_index_retains_page_and_sheet_coordinates(tmp_path, monkeypatch):
    source = tmp_path / "documents"
    source.mkdir()
    (source / "report.pdf").write_bytes(b"fixture")
    (source / "report.xlsx").write_bytes(b"fixture")

    def extract(path):
        if path.suffix == ".pdf":
            return [{"text": "revenue page one", "page": 1}, {"text": "revenue page two", "page": 2}]
        return [{"text": "revenue sheet", "sheet": "Forecast", "page": None}]

    monkeypatch.setattr("backend.rag.extract_segments", extract)
    rag = LocalRagIndex(Settings(rag_storage_dir=tmp_path / "index", local_embedding_provider="local-hashing"))
    rag.index_directory("case", source)

    results = rag.query("case", "revenue", top_k=10, diversify_files=False)
    assert {(item["text"], item["page"], item["sheet"]) for item in results} == {
        ("revenue page one", 1, None),
        ("revenue page two", 2, None),
        ("revenue sheet", None, "Forecast"),
    }
    assert all(item["source_hash"] == hashlib.sha256(b"fixture").hexdigest() for item in results)


def test_directory_index_distinguishes_duplicate_basenames(tmp_path):
    source = tmp_path / "documents"
    for folder in ("sales", "legal"):
        directory = source / folder
        directory.mkdir(parents=True)
        (directory / "report.txt").write_text("revenue risk", encoding="utf-8")

    rag = LocalRagIndex(Settings(rag_storage_dir=tmp_path / "index", local_embedding_provider="local-hashing"))
    rag.index_directory("case", source)
    results = rag.multi_query_context_documents("case", ["revenue"], per_file_limit=1)

    assert {item["file_name"] for item in results} == {"sales/report.txt", "legal/report.txt"}


def test_directory_indexes_real_workbook_sheet(tmp_path):
    from openpyxl import Workbook

    source = tmp_path / "documents"
    source.mkdir()
    workbook = Workbook()
    workbook.active.title = "Forecast"
    workbook.active.append(["Revenue", 200])
    workbook.save(source / "forecast.xlsx")
    workbook.close()

    rag = LocalRagIndex(Settings(rag_storage_dir=tmp_path / "index", local_embedding_provider="local-hashing"))
    rag.index_directory("case", source)
    result = rag.context_documents("case", "revenue")[0]

    assert result["file_name"] == "forecast.xlsx"
    assert result["sheet"] == "Forecast"
    assert "Revenue | 200" in result["text"]
