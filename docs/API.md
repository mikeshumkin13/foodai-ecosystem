# API

No stable public API exists yet.

## API Principles

- Use explicit versioning, starting with `/api/v1/`.
- Use authentication for private resources.
- Enforce object-level permissions on every user-owned object.
- Do not expose sequential public IDs where UUIDs are more appropriate.
- Prefer stable machine-readable error codes over prose-only errors, so Russian and English UI messages can be localized consistently.
- Return structured validation errors.
- Keep AI and Vision contracts explicit and test-covered.
- Do not include sensitive data in error messages or logs.

## Localization / Локализация

Primary user-facing languages are Russian (`ru`) and English (`en`).

Основные пользовательские языки: русский (`ru`) и английский (`en`).

API responses should avoid coupling clients to a single human language. Where backend-generated user-facing text is unavoidable, it must be designed for Russian and English localization.

## Planned API Areas

- Auth and session/account management.
- User profile and privacy controls.
- Food photo upload.
- Vision recognition job status.
- Meal diary.
- Nutrition catalog.
- Goals.
- Daily summaries.
- Data export and deletion.
- AI assistant conversations with safety boundaries.

## Breaking Changes

Breaking API changes require:

1. A documented reason in `docs/DECISIONS.md`.
2. Updated API documentation.
3. Tests covering the new behavior.
