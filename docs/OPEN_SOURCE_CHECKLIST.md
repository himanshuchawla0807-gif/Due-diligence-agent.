# Open Source Checklist

This checklist is here so releases do not depend on memory.

## Before Pushing

- [ ] `.env` is not staged.
- [ ] `storage/` is not staged.
- [ ] `.venv/` is not staged.
- [ ] `node_modules/` is not staged.
- [ ] `frontend/dist/` is not staged.
- [ ] No uploaded data-room files are staged.
- [ ] No provider keys are present in tracked files.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
cmd.exe /c npm.cmd --prefix frontend run build
git status --short
```

Secret scan:

```powershell
Get-ChildItem -Recurse -File -Force -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FullName -notmatch '\\(storage|\.venv|\.git|\.tmp|\.test-tmp|\.npm-cache|node_modules|dist|__pycache__|\.pytest_cache)\\' -and
    $_.Name -ne '.env'
  } |
  Select-String -Pattern 'BEGIN PRIVATE KEY','private_key','client_secret_','AIza','sk-[A-Za-z0-9_-]{20,}','firebase-adminsdk' -CaseSensitive:$false |
  Select-Object Path,LineNumber,Line
```

The `.gitignore` line for `*firebase-adminsdk*.json` is an expected false positive if it appears.

## What Good Looks Like

- A new user can run `python cli.py` and choose `mock`.
- Uploading a small folder produces a cited report.
- The report is Markdown, not plain chat text.
- Tables show as tables.
- Chart placeholders render when the table has numeric values.
- Citation badges open source snippets.

## Not Ready Yet

These are future hardening items, not blockers for localhost open source:

- hosted auth,
- hosted storage isolation,
- scanned-PDF OCR,
- frontend code splitting,
- deployment guides,
- hosted observability.
