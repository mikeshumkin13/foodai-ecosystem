# FoodAI Ecosystem

Commercial nutrition and activity tracking product with computer vision and AI-assisted workflows.

Core flow:

1. A user photographs food.
2. The system recognizes products and ingredients.
3. The system estimates portion size, mass, calories, macronutrients, and other nutrients.
4. The user confirms or corrects the result.
5. Confirmed data is saved to the diary.
6. The system analyzes daily intake.

AI is an assistant only. It does not diagnose, prescribe, or replace medical professionals.

## Languages / Языки

Primary project and user-facing product languages are Russian (`ru`) and English (`en`).

Основные языки проекта и пользовательского продукта: русский (`ru`) и английский (`en`).

## Planned Monorepo Structure

```text
foodai-ecosystem/
├── backend/
├── frontend/
├── services/
│   └── vision/
├── infra/
├── docs/
├── scripts/
├── .github/
├── AGENTS.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## Target Stack

- Backend: Python, Django, Django REST Framework, PostgreSQL, Redis, Celery.
- Vision: Python, FastAPI, OpenCV, CV/ML libraries only when justified.
- Frontend: Next.js, TypeScript, responsive PWA.
- Infrastructure: Docker, Docker Compose, GitHub Actions.
- Image storage: private S3-compatible object storage, MinIO for local development.

## Current Commands

The repository currently contains foundation documentation and validation scripts.

```bash
make test
make lint
make check
```

## Local Environment

Copy `.env.example` to `.env` for local development when services are introduced. Do not commit `.env`.
