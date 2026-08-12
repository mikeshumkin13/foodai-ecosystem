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

Создан backend foundation на Django + Django REST Framework, локальная Docker Compose инфраструктура с PostgreSQL, Redis и backend, а также приложение `accounts` с custom User model, RBAC foundation, session-cookie authentication, защищённой Django Admin foundation и MVP nutrition profile. Food/Diary модели пока не создавались.

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
export DJANGO_CORS_ALLOW_CREDENTIALS=true
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

- `GET /admin/` — Django Admin для внутренних ролей, пользователей и read-only audit foundation.
- `GET /api/v1/health/` — health check.
- `GET /api/v1/auth/csrf/` — выдаёт CSRF cookie/token для web-клиента.
- `POST /api/v1/auth/register/` — регистрация, создаёт inactive user и email verification token.
- `POST /api/v1/auth/login/` — login через Django session cookie; access token не выдаётся.
- `POST /api/v1/auth/logout/` — logout и сброс session.
- `POST /api/v1/auth/refresh/` — продление session и ротация session/CSRF.
- `GET /api/v1/auth/me/` — текущий пользователь.
- `POST /api/v1/auth/email/verify/` и `POST /api/v1/auth/email/resend/` — email verification flow.
- `POST /api/v1/auth/password/reset/request/` и `POST /api/v1/auth/password/reset/confirm/` — password reset flow.
- `POST /api/v1/auth/password/change/` — изменение пароля текущего пользователя.
- `GET /api/v1/accounts/profiles/{id}/` — чтение профиля с object-level permissions.
- `PUT/PATCH /api/v1/accounts/profiles/{id}/` — обновление профиля с object-level permissions.
- `GET /api/v1/accounts/nutrition-profiles/{id}/` — чтение собственного nutrition profile.
- `PUT/PATCH /api/v1/accounts/nutrition-profiles/{id}/` — обновление собственного nutrition profile с consent foundation.
- `GET/POST /api/v1/accounts/nutrition-restrictions/` — список и создание собственных sensitive nutrition restrictions.
- `GET/PUT/PATCH/DELETE /api/v1/accounts/nutrition-restrictions/{id}/` — работа только с собственными sensitive nutrition restrictions.
- `GET /api/v1/schema/` — OpenAPI schema.
- `GET /api/v1/docs/` — Swagger UI.

## Локальная инфраструктура через Docker Compose

Одна команда для локального запуска backend с PostgreSQL и Redis:

```bash
make dev-up
```

Если `.env` отсутствует, команда создаст его из безопасного `.env.example`. PostgreSQL и Redis доступны только внутри Docker Compose network и не публикуют порты на host.

Полезные команды:

```bash
make dev-up-detached
make dev-health
make dev-test
make dev-logs
make dev-down
```

Что запускается:

- `postgres` — PostgreSQL с volume `postgres_data` и healthcheck.
- `redis` — Redis с volume `redis_data` и healthcheck.
- `backend` — Django backend, который ждёт PostgreSQL/Redis, предсказуемо выполняет `migrate --noinput`, затем стартует `runserver`.

Health endpoint после запуска:

```bash
curl http://localhost:8000/api/v1/health/
```

Если локальная Docker Compose БД была создана до появления `accounts.User`, Django может сообщить `InconsistentMigrationHistory` из-за старой истории `admin` migrations. Это относится только к локальным dev volumes. Если данные не нужны, после явного подтверждения удаления локальной dev БД можно пересоздать volumes командой `docker compose --env-file .env down -v`, затем снова выполнить `make dev-up`.
