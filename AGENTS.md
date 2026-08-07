# FoodAI Ecosystem Agent Rules

These rules apply to every future Codex session in this repository.

## Required First Steps

1. Read the project documentation before making changes:
   - `docs/PROJECT_CONTEXT.md`
   - `docs/ARCHITECTURE.md`
   - `docs/ROADMAP.md`
   - `docs/STATUS.md`
   - `docs/DECISIONS.md`
   - `docs/SECURITY.md`
   - `docs/API.md`
2. Check Git status and the current branch.
3. If repository code contradicts documentation, identify the reason before changing either side.
4. Do not break existing APIs without an explicit documented decision.
5. Before changing architecture, read `docs/DECISIONS.md` and update it with the new decision.
6. After each task, update `docs/STATUS.md`.
7. Run available tests and linters before completing the task.
8. Do not merge into `develop`, `main`, `release/*`, or `hotfix/*` yourself.

## GitFlow

- Development starts from `develop`.
- Each logical task belongs in a separate `feature/*` branch.
- `main` is for stable releases only.
- Never develop directly on `main`.
- Never merge feature branches yourself unless explicitly instructed.

## Product Safety

FoodAI Ecosystem is not a doctor, licensed nutritionist, psychologist, or medical decision system.

AI features must not:

- diagnose conditions;
- prescribe medicine;
- replace a physician;
- independently make medical decisions.

Potentially dangerous situations require explicit safety logic and escalation guidance.

## Engineering Standards

- Prefer a modular Django monolith for the backend.
- Keep Vision as a separate service only because it has distinct CV/ML dependencies and resource needs.
- Do not create microservices without a concrete need.
- Use type hints, tests, migrations, structured logging, and clear separation of concerns.
- Keep secrets in environment variables only.
- Never commit `.env`, real credentials, tokens, user photos, health data, or generated private artifacts.

