"""Repeatable synthetic retrieval benchmark; no model/network or user data."""
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

from backend.config import Settings
from backend.pipeline import DOMAIN_PASSES
from backend.rag import LocalRagIndex


def main():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        settings = Settings(local_embedding_provider="local-hashing", rag_storage_dir=root / "rag", rag_chunk_words=80)
        rag = LocalRagIndex(settings)
        documents = [{"file_name": f"company_{i}.txt", "source_path": f"fixture/{i}", "text": (f"Company {i} revenue ARR growth EBITDA legal contract termination SOC security founders churn operations debt risk forecast " * 8)} for i in range(200)]
        rag.index_documents("benchmark", documents)
        queries = [query for domain in DOMAIN_PASSES for query in domain.queries]
        samples = []
        for _ in range(5):
            started = time.perf_counter()
            for query in queries:
                rag.query("benchmark", query, top_k=8)
            samples.append(time.perf_counter() - started)
        output = {"fixture_documents": 200, "chunks": rag.status("benchmark")["chunks"], "queries_per_sample": len(queries), "samples_seconds": samples, "median_seconds": statistics.median(samples)}
        Path(sys.argv[1]).write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(json.dumps(output))


if __name__ == "__main__":
    main()
