# Contributing

Thanks for taking a look at the project. This repo is early, so small and clear contributions are the most useful.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
npm --prefix frontend ci
python cli.py
```

Use `mock` first. It keeps the feedback loop cheap and avoids turning every setup problem into an API-key problem.

## Good First Changes

- fix a stale doc section,
- add a focused backend test,
- improve one retrieval query,
- make one frontend state easier to understand,
- improve error messages around missing keys or failed uploads.

## Before Opening A PR

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
cmd.exe /c npm.cmd --prefix frontend run build
```

Also check that you did not stage private files:

```powershell
git diff --cached --name-only
```

Never commit:

- `.env`
- API keys
- uploaded data rooms
- `storage/`
- `.venv/`
- `node_modules/`
- `frontend/dist/`

## Style

Prefer boring code. A plain function with a good name is better than a clever abstraction nobody wants to debug.

For docs, write like you are explaining the repo to a smart friend who has not seen the code yet. A little roughness is fine. Hidden complexity is not.

## Commit Messages

Use short, specific messages:

```text
fix: keep uploaded python files from reloading backend
docs: explain local rag storage
test: cover citation anchor rendering
```

## Reporting Bugs

Include:

- what command you ran,
- which provider you selected,
- whether `mock` mode works,
- the backend error if there is one,
- a tiny sample file if the bug is about extraction.
