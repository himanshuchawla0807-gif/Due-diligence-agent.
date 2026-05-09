# Security

Please do not post secrets, API keys, customer data, or private data-room files in public GitHub issues.

## Supported Version

This repo is pre-1.0. Security fixes should target `main`.

## Reporting A Problem

If you find a secret leak or a security issue, contact the maintainer privately first. If private contact is not available yet, open a minimal GitHub issue that says there is a security concern, but do not include the secret or exploit details.

## What This Project Tries To Protect

- User API keys in `.env`
- Uploaded documents in `storage/uploads`
- Local vector indexes in `storage/rag`
- Citation snippets returned from uploaded documents

## What Is Out Of Scope Right Now

This open-source version is designed for localhost development. It is not hardened as a multi-tenant hosted service yet.

Before running it for other users, you should add:

- authentication,
- per-user storage isolation,
- upload malware scanning,
- rate limits,
- request logging with secret redaction,
- deployment-specific CORS settings,
- a proper data retention policy.
