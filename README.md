# FoodAI Ecosystem

FoodAI Ecosystem — коммерческий продукт для ведения питания и физической активности с компьютерным зрением и AI-помощниками.

AI является помощником, а не врачом, лицензированным нутрициологом, психологом или системой медицинских решений.

## Основной сценарий

1. Пользователь фотографирует еду.
2. Система распознаёт продукты и ингредиенты.
3. Система оценивает порцию, массу, калории, БЖУ и другие нутриенты.
4. Пользователь подтверждает или исправляет результат.
5. Данные сохраняются в дневник.
6. Система анализирует дневной рацион.

## Языки

Основные языки проекта и пользовательского продукта: русский (`ru`) и английский (`en`).

## Структура

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
├── .editorconfig
├── .env.example
├── .gitignore
└── README.md
```

## Целевой стек

- Backend: Python, Django, Django REST Framework, PostgreSQL, Redis, Celery.
- Vision: Python, FastAPI, OpenCV; CV/ML-библиотеки добавляются только по необходимости.
- Frontend: Next.js, TypeScript, responsive PWA.
- Infrastructure: Docker, Docker Compose, GitHub Actions.
- Storage: приватное S3-compatible object storage; локально допустим MinIO.

## Текущее состояние

Создан backend foundation на Django + Django REST Framework. User/Food/Diary модели пока не создавались.

## Backend: локальная установка

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Минимальные переменные окружения для локального запуска:

```bash
export DJANGO_SECRET_KEY=local-dev-only
export DJANGO_DEBUG=true
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver
export DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000
export DATABASE_URL=sqlite:///backend/db.sqlite3
```

Команды:

```bash
make test
make lint
make typecheck
make django-check
make check
python backend/manage.py runserver 0.0.0.0:8000 --settings=config.settings.local
```

Backend endpoints:

- `GET /api/v1/health/` — health check.
- `GET /api/v1/schema/` — OpenAPI schema.
- `GET /api/v1/docs/` — Swagger UI.
