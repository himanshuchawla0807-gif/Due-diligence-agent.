# Architecture

This project has three main pieces:

```text
CLI launcher
  -> FastAPI backend
  -> React frontend
```

The backend is where the important agent work happens. The frontend is the surface for uploading files and reading the report.

## Runtime Flow

```text
python cli.py
  -> asks for provider and model
  -> writes local .env
  -> optionally pre-indexes a local data-room folder
  -> starts FastAPI on :8102
  -> starts Vite on :5174
  -> opens the browser
```

## Backend Modules

| File | Job |
| --- | --- |
| `backend/main.py` | FastAPI app setup and CORS |
| `backend/api.py` | Upload, chat, analysis, document, and RAG routes |
| `backend/config.py` | Runtime settings from `.env` |
| `backend/document_extractors.py` | Text extraction for supported file types |
| `backend/rag.py` | Local vector index and retrieval |
| `backend/pipeline.py` | Multi-pass diligence workstreams |
| `backend/providers.py` | Mock/OpenAI/Anthropic/Gemini/OpenRouter adapters |
| `backend/report.py` | Markdown IC memo renderer |
| `backend/storage.py` | Local session and upload storage |

## Analysis Pipeline

```text
Upload
  -> save files locally
  -> extract text
  -> chunk and embed text
  -> run domain retrieval passes
  -> ask provider for findings
  -> dedupe findings
  -> create citation metadata
  -> render Markdown report
```

The agent asks providers for structured JSON findings instead of final prose. That keeps the final report format stable even if different LLMs write differently.

## Why The Report Is Rendered Locally

The closed-source version produced strong Markdown reports with tables, charts, and citations. In this open version, the model produces findings and the backend renders the memo. That gives us:

- fewer broken Markdown reports,
- consistent section names,
- chart placeholders the frontend can parse,
- citation IDs that match the citation array,
- easier tests.

## Local Storage

All runtime data goes under `storage/`:

```text
storage/
  uploads/
  rag/
  sessions.json
```

That folder is ignored by Git. The repo should stay source-only.

## Provider Boundary

Providers are only used for analysis. They are not required for indexing.

```text
local files -> local RAG -> retrieved source blocks -> selected LLM provider
```

This makes the project easier to test without paid keys and avoids hard-wiring the agent to one model company.
