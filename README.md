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

Choose `mock` first to verify the local workflow without paid API keys.

The CLI starts:

- Backend: `http://localhost:8102`
- API health: `http://localhost:8102/api/health`

Manual backend start:

```powershell
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8102 --reload
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

## Source Migration Notes

- Backend/frontend reference: `Due Diligence Agent/`.
- Graph/team reference: `Due Diligence Agent/agents/`.

Do not copy credentials, `.env`, local data rooms, generated reports, `venv`, `.venv`, or `node_modules`.
