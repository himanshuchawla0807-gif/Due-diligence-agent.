# Due Diligence Agent Frontend

This is the local React UI for the open-source Due Diligence Agent.

It is mostly a working surface, not a marketing page. You upload files, see the document tree, ask for a diligence review, and read the cited Markdown report.

## Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- React Markdown with GFM tables
- Recharts for charts generated from report tables
- PDF/document viewer components for citation inspection

## Setup

From the repo root:

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

The frontend runs at:

```text
http://localhost:5174
```

The backend should be running at:

```text
http://localhost:8102
```

The API URL lives in `frontend/.env.example`:

```env
VITE_API_URL=http://localhost:8102
VITE_SESSION_SERVICE_URL=http://localhost:8102/api
```

## What The UI Expects From The Backend

The report response should be Markdown. It can include:

- `#` and `##` headings
- Markdown tables
- chart placeholders like `*Bar chart of risk findings by severity*`
- citation anchors like `<c>finding-1</c>`
- a `citations` array where each `id` matches those anchors

The frontend turns those pieces into a readable report with citation badges and chart blocks.

## Build

```powershell
cmd.exe /c npm.cmd --prefix frontend run build
```

The build output goes to `frontend/dist`, which is ignored by Git.
