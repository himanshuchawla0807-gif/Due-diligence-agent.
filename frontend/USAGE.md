# Using The Local UI

## 1. Start The App

The easiest path is the root CLI:

```powershell
cd "D:\Oriplex-Backend\open-agents\Due Diligence Agent Open"
.\.venv\Scripts\activate
python cli.py
```

Choose `mock` if you just want to test the upload and report flow.

Manual start:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8102
npm --prefix frontend run dev
```

Open:

```text
http://localhost:5174
```

## 2. Upload A Data Room

You can upload individual files or a folder. The frontend preserves folder paths where the browser provides them, so the sidebar can show a simple document tree.

Supported text extraction formats:

- PDF
- DOCX
- XLSX
- CSV
- Markdown
- TXT

The backend stores uploads under `storage/uploads` and indexes extracted text under `storage/rag`. Both folders are ignored by Git.

## 3. Ask For Review

Try:

```text
perform due diligence on the given documents
```

The backend will:

1. index uploaded files locally,
2. retrieve evidence by diligence domain,
3. generate file-grounded findings,
4. return a Markdown report with citations.

## 4. Read The Report

The report is meant to be inspectable:

- citation badges open source snippets,
- referenced documents appear below the answer,
- tables are rendered as tables,
- chart placeholders become charts when the table has numeric values.

If the report feels too thin, the usual reason is retrieval coverage or model output quality. Try a stronger model, upload more complete source files, or ask a narrower follow-up like:

```text
focus only on customer contracts and change of control risk
```

## 5. Troubleshooting

Backend offline:

```powershell
Invoke-RestMethod http://localhost:8102/api/health
```

Frontend not loading:

```powershell
npm --prefix frontend run dev
```

No citations:

- make sure the backend response includes a `citations` array,
- make sure report text uses `<c>citation-id</c>` anchors,
- run a new upload/session after backend changes.

Server stops after upload:

- do not run whole-repo reload,
- use `npm run dev:backend:reload` only while editing source.
