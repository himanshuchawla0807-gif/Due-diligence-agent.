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
4. Enter a local data-room directory to embed for RAG, or press Enter to skip.
5. Start the backend session on localhost.
```

Local RAG embedding is API-free. It uses deterministic local hashing vectors stored under `./storage/rag`, so users do not need a Gemini API key to index their directory.

The CLI starts:

- Backend: `http://localhost:8102`
- API health: `http://localhost:8102/api/health`
- Frontend: `http://localhost:5174`

Manual backend start:

```powershell
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8102 --reload
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

Do not copy credentials, `.env`, local data rooms, generated reports, `venv`, `.venv`, or `node_modules`.
