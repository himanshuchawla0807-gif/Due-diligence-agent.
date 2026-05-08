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

A vector store needs embeddings. This project uses `LOCAL_EMBEDDING_PROVIDER=auto` by default:

- If `sentence-transformers` is installed, it uses `sentence-transformers/all-MiniLM-L6-v2`.
- If the model is unavailable, it falls back to deterministic local hashing embeddings.

This keeps the open-source path local-first while allowing stronger semantic search when the small local model is present.

## Retrieval

Retrieval combines:

- vector similarity from local semantic embeddings or local hashing embeddings
- lexical scoring for exact file terms, names, dates, and risk phrases
- domain-specific query expansion for financial, legal, commercial, technical, HR, operations, and data-integrity coverage
- file-specific sweeps for up to the configured data-room file limit
- file diversification for broad prompts like "perform due diligence on the given documents"

The generator receives source blocks with `file_name`, `source_path`, `chunk_index`, and excerpts. Findings must include a source file and evidence from that file.

## Report Contract

The response formatter emits Markdown tables followed immediately by chart placeholders such as `*Bar chart of risk findings by severity*`. The frontend parses the nearest preceding table and renders the chart when the second table column is numeric.
