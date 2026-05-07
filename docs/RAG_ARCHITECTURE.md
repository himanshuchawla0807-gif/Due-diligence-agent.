# Due Diligence RAG Architecture

The open-source due diligence agent uses local-first retrieval instead of the closed-source Gemini File Search service.

## Workflow

```text
upload files -> extract text -> chunk text -> local embeddings -> vector index -> diversified retrieval -> file-grounded findings
```

Uploaded files are always indexed. The CLI only asks for an optional extra data-room directory to pre-index before the localhost UI starts.

## Storage

- Uploaded files live under `storage/uploads`.
- Local vector indexes live under `storage/rag`.
- Both directories are ignored by Git.
- No provider API key is required for indexing.

## Embeddings

A vector store needs embeddings. This project currently uses deterministic local hashing embeddings, so the index can be built without OpenAI, Gemini, Anthropic, or OpenRouter credentials.

This is good enough for open-source localhost testing, keyword-heavy data rooms, and file-directed citations. For stronger semantic search, add an optional local embedding backend such as sentence-transformers while keeping the hashing backend as the default no-install fallback.

## Retrieval

Retrieval combines:

- vector similarity from local hashing embeddings
- lexical scoring for exact file terms, names, dates, and risk phrases
- file diversification for broad prompts like "perform due diligence on the given documents"

The generator receives source blocks with `file_name`, `source_path`, `chunk_index`, and excerpts. Findings must include a source file and evidence from that file.
