# Due Diligence Agent Open Plan

This file is the migration scratchpad. It is less polished than the README on purpose: it records what this open-source version was trying to become.

Initial migration target:

- Copy only the due diligence backend, graph/team code, prompts, and frontend screens required for the open agent.
- Remove hard-coded provider choices and personal deployment URLs.
- Replace fixed project/bucket/service values with env vars.
- Add mock provider tests for classification, team routing, risk review, and synthesis.
- Use local directory RAG indexing with API-free hashing embeddings, stored under ignored `storage/rag`.
- Never require Gemini for RAG storage. Gemini is only required if the user explicitly selects Gemini as the review model provider.

Current status:

- Local uploads are indexed automatically.
- Optional local directory pre-indexing is available from the CLI and API.
- The backend supports mock, OpenAI, Anthropic, Gemini, and OpenRouter providers.
- Broad diligence prompts run a multi-pass domain pipeline.
- The final response is a cited Markdown memo with tables and chart placeholders.

Next sensible improvements:

- add OCR for scanned PDFs,
- split the frontend bundle,
- add more provider-specific tests with mocked SDK clients,
- improve file-type classification before domain routing,
- add export to Markdown/PDF.
