# Due Diligence Agent Open

Open-source-ready due diligence agent for classifying deal-room files, extracting findings, reviewing risks, and producing structured summaries.

## Purpose

- Ingest deal-room documents.
- Classify files by diligence category.
- Extract commercial, financial, legal, technical, and risk signals.
- Synthesize findings into due diligence outputs.

## Planned Stack

- FastAPI backend.
- LangGraph team/worker orchestration.
- Configurable providers per team or worker.
- Local filesystem storage by default.
- Optional frontend copied and trimmed from the existing due diligence UI.

## Planned Graph

```text
ingest -> classify -> route_to_team -> extract_findings -> risk_review -> synthesize
```

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python cli.py
```

Choose `mock` first to verify the local workflow without paid API keys. The CLI flow is:

```text
1. Select provider: mock, OpenAI, Anthropic, Gemini, or OpenRouter.
2. Enter the provider API key only when that provider is selected.
3. Select a model preset.
4. Optionally enter an extra local data-room directory to pre-index, or press Enter to use uploaded files only.
5. Start the backend and frontend session on localhost.
```

Local RAG is always on for uploaded files. When a user uploads a data room, the backend extracts text from PDF, DOCX, CSV, XLSX, Markdown, and text files, chunks the full extracted content, creates local embeddings, and stores the vector index under `./storage/rag`. Users do not need Gemini, OpenAI, Anthropic, or OpenRouter keys to index local knowledge.

The default embedding mode is `LOCAL_EMBEDDING_PROVIDER=auto`. It uses `sentence-transformers/all-MiniLM-L6-v2` when installed and falls back to local hashing if the model is unavailable. Retrieval is hybrid: semantic or hashing vector similarity plus lexical scoring, domain-specific query expansion, file-specific sweeps, and file diversification. This keeps answers directed to the uploaded files and avoids pulling every chunk from a single document.

The CLI starts:

- Backend: `http://localhost:8102`
- API health: `http://localhost:8102/api/health`
- Frontend: `http://localhost:5174`

Manual backend start:

```powershell
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8102
```

Do not run the user-facing backend with whole-repo `--reload`: uploaded data-room files are stored under `storage/uploads`, and a Python file upload can otherwise trigger a server reload mid-session. If you are actively editing backend source, use the scoped reload command:

```powershell
npm run dev:backend:reload
```

Manual frontend start:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

## Provider Configuration

Set `DUE_DILIGENCE_PROVIDER` in `.env`:

- `mock`
- `openai`
- `anthropic`
- `gemini`
- `openrouter`

Then add the matching API key:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `OPENROUTER_API_KEY`

For OpenRouter, set `OPENROUTER_MODEL` to the exact model route you want.

## API Shape

- `GET /api/health`
- `GET /api/providers`
- `POST /api/due-diligence/upload`
- `POST /api/due-diligence/analyze`
- `POST /api/upload` for the migrated frontend
- `POST /api/industry-dd` for the migrated frontend
- `POST /api/chat` for the migrated frontend
- `GET /api/session/{session_id}/documents` for the migrated frontend
- `GET /api/document/{session_id}/{file_path}` for the migrated frontend
- `POST /api/rag/index-local-directory`
- `GET /api/rag/status/{session_id}`
- `POST /api/rag/query`

Uploaded files are indexed automatically through `POST /api/upload` and `POST /api/due-diligence/upload`. The manual local-directory endpoint is only for pre-indexing an extra data-room folder before using the UI.

Comprehensive due diligence requests use report-scale retrieval and return a Markdown IC-style memo with:

- executive summary
- risk snapshot table plus chart placeholder
- domain coverage table plus chart placeholder
- evidence matrix
- source coverage table plus chart placeholder
- immediate diligence actions

For broad prompts like "perform due diligence on the given documents", the backend runs a multi-pass domain pipeline:

- Financial Team
- Legal Team
- Commercial Team
- Technical Team
- People and Governance Team
- Operations Team
- Data Integrity Team

Each pass retrieves its own local evidence, asks the selected provider for file-grounded findings, then merges and deduplicates the results before report synthesis.

Index a local directory:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8102/api/rag/index-local-directory `
  -ContentType "application/json" `
  -Body '{"session_id":"default","directory":"D:\\path\\to\\data-room","recursive":true}'
```

Query the local RAG index:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8102/api/rag/query `
  -ContentType "application/json" `
  -Body '{"session_id":"default","query":"customer concentration and legal risks","top_k":5}'
```

## Source Migration Notes

- Backend/frontend reference: `Due Diligence Agent/`.
- Graph/team reference: `Due Diligence Agent/agents/`.
- Local RAG design: `docs/RAG_ARCHITECTURE.md`.

Do not copy credentials, `.env`, local data rooms, generated reports, `venv`, `.venv`, or `node_modules`.
