# Due Diligence Agent Open Plan

Initial migration target:

- Copy only the due diligence backend, graph/team code, prompts, and frontend screens required for the open agent.
- Remove hard-coded provider choices and personal deployment URLs.
- Replace fixed project/bucket/service values with env vars.
- Add mock provider tests for classification, team routing, risk review, and synthesis.
- Use local directory RAG indexing with API-free hashing embeddings, stored under ignored `storage/rag`.
- Never require Gemini for RAG storage. Gemini is only required if the user explicitly selects Gemini as the review model provider.
