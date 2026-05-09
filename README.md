# Due Diligence Agent Open

A local-first due diligence agent for reading a small data room, finding risks, and turning the evidence into a cited Markdown memo.

It is built for the boring but important part of diligence: upload the files, ask the agent to review them, and get back something you can actually inspect. The answer is not meant to be magic. It should show where each claim came from, which files were used, and what follow-up questions still need to be asked.

This repo is the open-source version of the Oriplex Due Diligence Agent. It removes private credentials, managed cloud storage, and personal deployment settings. You bring your own API key if you want a real model. You can also run the full localhost flow in `mock` mode first.

## What It Does

- Upload a folder or batch of deal-room files through the local UI.
- Extract text from PDF, DOCX, XLSX, CSV, Markdown, and text files.
- Build a local RAG index under `./storage/rag`.
- Retrieve evidence across financial, legal, commercial, technical, people, operations, and data-integrity workstreams.
- Ask the selected provider for file-grounded findings.
- Render an IC-style Markdown report with tables, chart placeholders, evidence, actions, and clickable citations.

The broad prompt this project is tuned for is simple:

```text
perform due diligence on the given documents
```

## The Short Version

```powershell
git clone https://github.com/himanshuchawla0807-gif/Due-diligence-agent..git Due-Diligence-Agent-Open
cd "Due-Diligence-Agent-Open"

python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

npm --prefix frontend ci
python cli.py
```

When the CLI opens, choose `mock` first. That proves the upload, local RAG, backend, and frontend all work without spending money on model calls.

Local URLs:

- Frontend: `http://localhost:5174`
- Backend: `http://localhost:8102`
- Health check: `http://localhost:8102/api/health`

## How The Agent Thinks

The system is intentionally straightforward.

```text
upload files
  -> extract text
  -> chunk the documents
  -> embed locally
  -> retrieve evidence by domain
  -> generate findings
  -> synthesize a cited Markdown memo
```

For broad diligence prompts, it does not use one giant search. It runs several passes:

| Pass | What it looks for |
| --- | --- |
| Financial | revenue, ARR, EBITDA, burn, runway, projections, weird accounting |
| Legal | contracts, assignment rights, change of control, IP, compliance |
| Commercial | market, customers, pricing, churn, retention, competition |
| Technical | architecture, security, scalability, roadmap, technical debt |
| People and Governance | founders, org chart, resumes, compensation, board records |
| Operations | delivery, vendors, support, processes, business continuity |
| Data Integrity | contradictions, placeholders, fake-looking data, repeated templates |

The result is then formatted into a report instead of a loose chat answer.

## RAG, In Plain English

Yes, this project uses a vector store. That means documents are converted into embeddings so the agent can search by meaning, not just exact words.

By default:

- `LOCAL_EMBEDDING_PROVIDER=auto`
- If `sentence-transformers` is installed, it uses `sentence-transformers/all-MiniLM-L6-v2`.
- If that model is not available, it falls back to deterministic local hashing.

No OpenAI, Anthropic, Gemini, or OpenRouter key is needed to index your files. API keys are only needed when you choose a real LLM provider for analysis.

More detail: [docs/RAG_ARCHITECTURE.md](docs/RAG_ARCHITECTURE.md)

## Provider Setup

Copy the example env file only if you want to start services manually:

```powershell
Copy-Item .env.example .env
```

Then set:

```env
DUE_DILIGENCE_PROVIDER=mock
```

Supported providers:

| Provider | Env var |
| --- | --- |
| `mock` | no key needed |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` |

The CLI writes `.env` for you when you choose a provider. `.env` is ignored by Git.

## Manual Commands

Backend only:

```powershell
.\.venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8102
```

Frontend only:

```powershell
npm --prefix frontend run dev
```

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
cmd.exe /c npm.cmd --prefix frontend run build
```

Do not run the user-facing backend with whole-repo `--reload`. Uploaded files are stored under `storage/uploads`, and a Python file in an uploaded data room can trigger a reload. If you need reload while editing backend code, use the scoped command:

```powershell
npm run dev:backend:reload
```

## API Map

- `GET /api/health`
- `GET /api/providers`
- `POST /api/upload`
- `POST /api/industry-dd`
- `POST /api/chat`
- `GET /api/session/{session_id}/documents`
- `GET /api/document/{session_id}/{file_path}`
- `POST /api/rag/index-local-directory`
- `GET /api/rag/status/{session_id}`
- `POST /api/rag/query`

Example local directory indexing:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8102/api/rag/index-local-directory `
  -ContentType "application/json" `
  -Body '{"session_id":"default","directory":"D:\\path\\to\\data-room","recursive":true}'
```

Example RAG query:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8102/api/rag/query `
  -ContentType "application/json" `
  -Body '{"session_id":"default","query":"customer concentration and legal risks","top_k":5}'
```

## What Is Stored Locally

Ignored by Git:

- `.env`
- `.venv`
- `frontend/node_modules`
- `frontend/dist`
- `storage/uploads`
- `storage/rag`
- logs, caches, and temporary files

The repo should contain source code, docs, tests, manifests, and safe config templates only.

## Current Limits

This is still an early open-source cut.

- The local RAG is good enough for small and medium data rooms, but it is not a hosted enterprise search system.
- The mock provider is for testing flow, not for real diligence quality.
- Real model quality depends heavily on the provider and model you choose.
- OCR for scanned PDFs is not the focus yet.
- The frontend bundle is large because PDF viewing and chart rendering are currently shipped together.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - how the pieces fit together
- [docs/RAG_ARCHITECTURE.md](docs/RAG_ARCHITECTURE.md) - local retrieval and embeddings
- [docs/AGENT_PLAN.md](docs/AGENT_PLAN.md) - migration plan notes
- [docs/OPEN_SOURCE_CHECKLIST.md](docs/OPEN_SOURCE_CHECKLIST.md) - release hygiene checklist
- [frontend/USAGE.md](frontend/USAGE.md) - using the local UI

## Contributing

Small fixes are welcome. Please keep changes boring and easy to review: one bug, one feature, or one doc improvement at a time.

Start here: [CONTRIBUTING.md](CONTRIBUTING.md)

## Security

Please do not open public issues with secrets or credential leaks. See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
