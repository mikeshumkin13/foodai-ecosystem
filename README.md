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
- Vision: Python, FastAPI, Pillow, Transformers, PyTorch CPU; OpenCV добавляется только при реальной необходимости.
- Frontend: Next.js, TypeScript, responsive PWA-ready client.
- Infrastructure: Docker, Docker Compose, GitHub Actions.
- Storage: приватное S3-compatible object storage; локально допустим MinIO.

## Текущее состояние

Создан backend foundation на Django + Django REST Framework, локальная Docker Compose инфраструктура с PostgreSQL, Redis, backend, Celery worker и Vision service, приложение `accounts` с custom User model, RBAC foundation, session-cookie authentication, защищённой Django Admin foundation и MVP nutrition profile. Добавлены приложение `nutrition` с расширяемым каталогом продуктов, нутриентов и calculation engine для КБЖУ/micronutrients, приложение `diary` с Meal/MealItem, историческими nutrient snapshots и дневной агрегацией, `food_scans` для безопасной загрузки фотографий еды в private storage, async Vision processing через Celery, estimator оценки порции v1, AI Nutrition/Fitness/Wellbeing foundations, Privacy Center для export/consent/deletion controls, `audit` security audit trail и безопасный structured observability foundation. FastAPI `services/vision` содержит real food recognition model v1. Frontend foundation расположен в `frontend`: Next.js + TypeScript App Router, responsive PWA-ready shell, страницы `/login`, `/register`, `/dashboard`, `/diary`, `/scan`, `/profile`, `/privacy`, централизованный API client и CSRF/session-cookie flow без access token в `localStorage`.

## Backend: локальная установка

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pip install -e "services/vision[dev]"
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

## CI для pull request

GitHub Actions запускает независимые обязательные проверки Backend, Vision и Frontend для pull
request в `develop` и `main`. Workflow выполняет lint, type checks, migration/Django checks, tests,
coverage и production frontend build; dependency caches используют Python manifests и
`frontend/pnpm-lock.yaml`. Production secrets и постоянные внешние service credentials в CI не
используются.

Vision service локально без Docker:

```bash
python -m uvicorn vision_service.main:app --app-dir services/vision --host 0.0.0.0 --port 8001
```

Celery worker локально без Docker, если Redis доступен через `REDIS_URL`:

```bash
celery -A config worker --loglevel=INFO --concurrency=1
```

Observability настраивается через `LOG_LEVEL`, `OBSERVABILITY_METRICS_BACKEND` и
`ERROR_MONITORING_BACKEND`. По умолчанию backend пишет безопасные JSON-события и metric events в
console, а внешний error monitoring отключён. API-ответы содержат `X-Request-ID`; этот ID можно
передать во входном `X-Request-ID` или `X-Correlation-ID` в безопасном формате.

Backend endpoints:

- `GET /admin/` — Django Admin для внутренних ролей, пользователей, read-only admin audit mirror и read-only security audit trail.
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
- `GET /api/v1/foods/search/` — поиск продуктов в nutrition catalog.
- `GET /api/v1/foods/{id}/` — карточка продукта с nutrients per 100 g и единицами измерения.
- `POST /api/v1/foods/` — создание food catalog item для `content_manager`/`admin`.
- `PUT/PATCH/DELETE /api/v1/foods/{id}/` — изменение food catalog item для `content_manager`/`admin`.
- `POST /api/v1/meals/` — создание приёма пищи текущего пользователя.
- `GET /api/v1/meals/` — список собственных приёмов пищи; поддерживает фильтры `date`, `date_from`, `date_to`.
- `GET /api/v1/meals/{id}/` — чтение собственного приёма пищи по UUID.
- `PATCH /api/v1/meals/{id}/` — частичное изменение собственного приёма пищи; переданные `items` заменяют состав приёма пищи.
- `DELETE /api/v1/meals/{id}/` — удаление собственного приёма пищи.
- `GET /api/v1/diary/day/?date=YYYY-MM-DD` — дневная агрегация calories/protein/fat/carbs и micronutrients по собственному дневнику.
- `POST /api/v1/food-scans/` — загрузка фотографии блюда в private storage; принимает `multipart/form-data` поле `photo`, быстро возвращает `scan_id` и `status`, а Vision processing выполняется в Celery worker.
- `GET /api/v1/food-scans/` — список собственных food scans без постоянных публичных URL.
- `GET /api/v1/food-scans/{id}/` — metadata собственного food scan по UUID без `object_key` и публичного URL.
- `GET /api/v1/food-scans/{id}/results/` — polling результатов scan после background processing: detected items, активная `mass_g`, `manual_mass_g`, `portion_estimate` и nutrient snapshots.
- `POST /api/v1/food-scans/{id}/retry/` — повторно поставить scan в обработку, если он не confirmed и не processing.
- `PATCH /api/v1/food-scans/{id}/items/{item_id}/` — исправить продукт и/или массу; ручная масса сохраняется отдельно от initial portion estimate.
- `POST /api/v1/food-scans/{id}/confirm/` — подтвердить results и создать `Meal`/`MealItem`; endpoint идемпотентен.
- `GET /api/v1/privacy/data-summary/` — summary категорий собственных данных.
- `GET /api/v1/privacy/export/` — скачать JSON export собственных данных.
- `GET/PATCH /api/v1/privacy/consent/` — чтение и изменение consent для model improvement и отдельного food photo training consent.
- `DELETE /api/v1/privacy/food-photos/{scan_id}/` — удалить собственное food photo из PostgreSQL/private storage.
- `DELETE /api/v1/privacy/ai-chat-history/` — удалить сохранённую AI chat history текущего пользователя.
- `DELETE /api/v1/privacy/account/` — удалить аккаунт и связанные данные после проверки текущего пароля.
- `GET /api/v1/schema/` — OpenAPI schema.
- `GET /api/v1/docs/` — Swagger UI.

Internal Vision endpoints:

- `GET /health` — health check Vision service.
- `POST /v1/analyze` — internal food recognition v1 для подготовленного private food scan object reference. Возвращает `{"items": [{"label": "...", "confidence": 0.0-1.0}]}`; текущая модель является dish-level classifier без bounding boxes и оценки порции.

Benchmark Vision model v1:

```bash
python services/vision/scripts/benchmark_food_model.py --synthetic
```

## Frontend: локальная установка

Для frontend используется `pnpm`.

```bash
cd frontend
pnpm install
pnpm dev
```

Проверки frontend:

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm check
```

Frontend API client находится в `frontend/src/lib/api`. Web-клиент использует backend session-cookie схему: requests идут с `credentials: "include"`, unsafe requests получают CSRF через `GET /api/v1/auth/csrf/` и отправляют `X-CSRFToken`. Browser-facing access token не выдаётся и не хранится в `localStorage`.

Демо-данные nutrition catalog для локальной разработки:

```bash
python backend/manage.py loaddata demo_nutrition_catalog --settings=config.settings.local
```

## Локальная инфраструктура через Docker Compose

Одна команда для локального запуска backend, Celery worker, Vision service, PostgreSQL и Redis:

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
- `celery_worker` — Celery worker для background Vision processing; ждёт PostgreSQL, Redis, Vision и healthy backend, не запускает migrations параллельно с backend.
- `vision` — FastAPI Vision service с `GET /health` и real food recognition v1 в `POST /v1/analyze`.

Health endpoint после запуска:

```bash
curl http://localhost:8000/api/v1/health/
```

Если локальная Docker Compose БД была создана до появления `accounts.User`, Django может сообщить `InconsistentMigrationHistory` из-за старой истории `admin` migrations. Это относится только к локальным dev volumes. Если данные не нужны, после явного подтверждения удаления локальной dev БД можно пересоздать volumes командой `docker compose --env-file .env down -v`, затем снова выполнить `make dev-up`.

Food scan uploads в local development сохраняются в приватный filesystem root `FOOD_SCAN_PRIVATE_MEDIA_ROOT`. API не возвращает постоянный публичный URL; будущий S3-compatible backend должен подключаться через private storage boundary.

В Docker Compose backend обращается к Vision по `VISION_SERVICE_URL=http://vision:8001`. Vision port не публикуется на host по умолчанию; для прямого локального теста запускайте сервис командой `uvicorn` выше.

Celery использует Redis как broker/result backend. Upload endpoint не ждёт Vision: клиент получает `scan_id`, затем опрашивает `GET /api/v1/food-scans/{id}/results/` до статуса `needs_confirmation`, `failed` или `confirmed`.
