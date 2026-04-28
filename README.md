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
Copy-Item .env.example .env
```

If frontend code is added:

```powershell
npm install
npm run dev
```

## Source Migration Notes

- Backend/frontend reference: `Due Diligence Agent/`.
- Graph/team reference: `Due Diligence Agent/agents/`.

Do not copy credentials, `.env`, local data rooms, generated reports, `venv`, `.venv`, or `node_modules`.
