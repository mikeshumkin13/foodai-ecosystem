# Architecture / Архитектура

## Основной принцип

Стартуем с monorepo и не создаём микросервисы без необходимости.

`backend` — модульный Django-монолит. Отдельным сервисом делаем только `services/vision`, потому что у него другие CV/ML-зависимости и требования к ресурсам.

## Структура monorepo

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

## Backend

Целевой стек:

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Redis.
- Celery.
- pytest, pytest-django, Ruff, mypy и coverage для backend quality gate.
- drf-spectacular для OpenAPI/Swagger.

Ответственность:

- authentication и authorization;
- пользовательский профиль и privacy-настройки;
- дневник питания;
- каталог продуктов и расчёт нутриентов;
- метаданные фотографий и ссылки на приватное object storage;
- orchestration задач Vision;
- AI safety boundaries;
- экспорт и удаление данных;
- audit log административных операций.

Текущее foundation-состояние:

- Django project расположен в `backend/config`.
- Настройки разделены на `config.settings.base`, `config.settings.local`, `config.settings.production`.
- Настройки читаются из environment variables.
- Приложение `core` содержит только инфраструктурные endpoint-ы, без доменных моделей.
- Приложение `accounts` содержит custom User model и `UserProfile`.
- `AUTH_USER_MODEL = "accounts.User"`.
- `accounts.User` использует UUID primary key, уникальный email как основной логин, стандартный Django password hashing, `is_active`, `is_staff` и timestamps.
- Пользовательские данные вне authentication/authorization хранятся в `UserProfile`; health/fitness данные не помещаются в `User`.
- RBAC foundation реализован через централизованные Django Groups/Permissions в `accounts.rbac`.
- Роли `user`, `support`, `content_manager` и `admin` являются business roles; `superuser` остаётся отдельным техническим механизмом Django.
- DRF API закрыт по умолчанию через `IsAuthenticated`; публичные endpoint-ы должны явно указывать `AllowAny`.
- Object-level permissions для пользовательских объектов реализуются централизованными DRF permission-классами; текущий `UserProfile` API проверяет владельца и защищён от IDOR по UUID.
- Authentication для web-клиента использует Django session cookie, а не bearer access token в browser storage.
- `sessionid` должен быть `HttpOnly`, `SameSite` и `Secure` в production; unsafe requests защищаются CSRF.
- Email verification и password reset используют одноразовые DB tokens, где хранится только hash токена.
- Login, registration, email verification и password reset endpoints имеют scoped rate limiting.
- Django Admin используется как внутренний protected admin foundation для users/profiles/role groups и read-only admin audit log.
- `accounts.AdminAuditLog` зеркалирует `django_admin_log` и хранит минимальные sanitized metadata административных действий.
- Support/content-manager admin visibility строится через Django model permissions; без явных permissions они не видят чувствительные account/audit/role models.
- `accounts.NutritionProfile` хранит MVP-настройки питания отдельно от `User` и `UserProfile`.
- Возраст хранится как `age_category`, а не дата рождения или точный год рождения.
- Аллергии, intolerance и медицинские ограничения отделены в `accounts.NutritionSensitiveRestriction` и доступны только владельцу через object-level permissions.
- Nutrition profile API требует owner-only доступ и consent/version foundation для изменения пользовательских nutrition/health данных.
- Приложение `nutrition` содержит MVP nutrition catalog: `FoodCategory`, `FoodDataSource`, `Nutrient`, `FoodItem`, `FoodNutrient`.
- `FoodItem` хранит canonical food item, names/synonyms, category, source, density metadata, verified flag и source reference.
- Нутриенты не зашиты как только КБЖУ: `FoodNutrient` связывает food item с расширяемым `Nutrient` и хранит `amount_per_100g`.
- Nutrition calculation engine расположен в `nutrition.calculation`; он принимает canonical `FoodItem` и массу в граммах, использует Decimal-арифметику и возвращает kcal, protein, fat, carbohydrates и доступные micronutrients.
- Единая внутренняя система единиц backend для nutrition calculation: масса в grams (`g`), значения каталога на `100 g`, energy в `kcal`, macronutrients в `g`, micronutrients в catalog-native units.
- `content_manager` управляет каталогом через централизованные Django permissions; обычный authenticated `user` имеет read-only API-доступ.
- Приложение `diary` содержит пользовательский дневник питания: `Meal` и `MealItem`.
- `Meal` всегда принадлежит конкретному `accounts.User` и использует UUID primary key.
- `MealItem` ссылается на `nutrition.FoodItem`, но хранит исторический snapshot названия, source reference, calories/protein/fat/carbs, всех nutrients и micronutrients на момент добавления или ручной корректировки.
- Изменение глобального `FoodItem` или `FoodNutrient` не должно менять исторические записи пользователя.
- Diary API доступен обычному `user` только для собственных meals; `support`, `content_manager` и business `admin` не получают доступ к приватному дневнику по умолчанию.
- Приложение `food_scans` содержит secure food photo upload foundation.
- `FoodScan` принадлежит конкретному `accounts.User`, хранит metadata приватного объекта, фактический image format, размеры, byte sizes, checksum и processing status.
- Пользовательское имя файла не используется для storage key; object key генерируется из UUID.
- Backend проверяет фактический формат через Pillow, разрешает только whitelist `JPEG`/`PNG`, ограничивает upload size и pixel count, удаляет EXIF/metadata перед сохранением.
- Food scan API возвращает metadata без `object_key` и без постоянного публичного URL.
- Private storage подключён через boundary `PrivateObjectStorage`; MVP использует локальный private filesystem storage, production может заменить реализацию на S3-compatible private object storage без изменения API.
- Backend общается с Vision service только через `integrations.vision.client` и доменный adapter `food_scans.vision`; HTTP-вызовы не размещаются в Django views.
- Vision client использует один HTTP-запрос без retries, timeout через `VISION_SERVICE_TIMEOUT_SECONDS` и отдельные ошибки для unavailable, timeout и invalid response.
- Background processing подключён через Celery app `config.celery` и Redis broker/result backend.
- Upload food scan больше не ждёт Vision в request flow: backend создаёт `FoodScan`, ставит `food_scans.process_food_scan_analysis` в очередь и быстро возвращает `scan_id`/`status`.
- Celery task вызывает Vision через существующий `food_scans.orchestration` / `food_scans.vision` boundary, сохраняет proposal detected items и переводит scan в `needs_confirmation`.
- `FoodScan` хранит внутренние поля `analysis_run_id`, `analysis_task_id` и `analysis_attempt_count` для idempotency, controlled retry и защиты от stale tasks.
- Статусы `FoodScan`: `uploaded`, `processing`, `needs_confirmation`, `confirmed`, `failed`.
- `FoodScanDetectedItem` хранит Vision label/confidence, matched `FoodItem`, массу, source, correction flags и proposal nutrient snapshots.
- Portion estimation v1 работает как estimator, а не точное измерение: `FoodScanDetectedItem` хранит активную массу, исходную оценку объёма/массы, min/max interval, method, confidence и отдельную `manual_mass_g` при пользовательской коррекции.
- Оценка порции использует `FoodItem.density_g_per_ml`, density metadata или MVP density table по типу продукта; при наличии segment area и known plate/reference применяется простая геометрия площади и assumed depth.
- Matching Vision label к nutrition catalog выполняется детерминированно через `food_scans.matching` по names/synonyms; fuzzy/ML-ranking не добавлен в MVP foundation.
- Scan results не создают дневник автоматически; только явное подтверждение пользователя создаёт `Meal` и `MealItem`.
- При proposal creation и manual correction scan использует `nutrition.calculation` для пересчёта nutrient snapshot; при confirmation `MealItem` получает копию proposal snapshot из `FoodScanDetectedItem`, чтобы изменения `FoodItem`/`FoodNutrient` после анализа не меняли подтверждённые расчёты.
- Health endpoint: `GET /api/v1/health/`.
- Swagger UI: `GET /api/v1/docs/`.

## Vision Service

Целевой стек:

- Python.
- FastAPI.
- OpenCV.
- CV/ML-библиотеки только по необходимости.

Ответственность:

- проверка MIME и фактического формата изображений;
- удаление EXIF/geolocation;
- распознавание еды, продуктов и ингредиентов;
- оценка порции и массы;
- возврат структурированных candidates в backend.

Vision не владеет пользователями, дневниками, оплатами или долгосрочными пользовательскими данными.

Текущее foundation-состояние:

- FastAPI service расположен в `services/vision`.
- Endpoint `GET /health` возвращает `{"status": "ok"}`.
- Endpoint `POST /v1/analyze` принимает internal object reference на уже подготовленное backend изображение, читает private local object, проверяет checksum и запускает food recognition model через pluggable inference adapter.
- Vision model v1: Hugging Face `nateraw/food`, pinned revision `ddbd0f9ed493f03fc6a45527e5e52904161d3e09`, Apache-2.0 model license, `model.safetensors` weights.
- Текущий v1 является dish-level classifier, а не object detector: он возвращает top label и confidence без bounding boxes, portion size или multi-object segmentation.
- Vision contract поддерживает optional future geometry fields `segment_area_px` и `portion_reference`, но текущая модель их обычно не заполняет; backend portion estimator использует их только если они доступны.
- Low-confidence results не создают diary records автоматически; backend всегда переводит scan в `needs_confirmation` до явного пользовательского подтверждения.
- Vision service запускается отдельным контейнером Docker Compose и не публикует порт на host по умолчанию; backend обращается к нему внутри compose network по `VISION_SERVICE_URL`.
- Benchmark script: `services/vision/scripts/benchmark_food_model.py`.

## Frontend

Целевой стек:

- Next.js.
- TypeScript.
- Responsive PWA.

Ответственность:

- UX фото еды;
- подтверждение и исправление результата распознавания;
- дневник питания;
- цели и графики прогресса;
- AI-сценарии с safety boundaries.

Пользовательские строки фронтенда должны быть готовы к локализации на русский (`ru`) и английский (`en`).

Текущее foundation-состояние:

- Frontend расположен в `frontend`.
- Используется Next.js App Router + TypeScript.
- Реализованы базовые маршруты `/login`, `/register`, `/dashboard`, `/diary`, `/scan`, `/profile`.
- UI shell responsive: sidebar на desktop и нижняя навигация на mobile.
- Приложение PWA-ready: добавлены manifest, icon и service worker registration для production build.
- Централизованный API client расположен в `frontend/src/lib/api`.
- Auth flow соответствует backend ADR-0009: requests выполняются с `credentials: "include"`, unsafe requests получают CSRF через `GET /api/v1/auth/csrf/` и отправляют `X-CSRFToken`.
- Browser-facing access token не выдаётся и не хранится в `localStorage`.
- Базовые UI components в `frontend/src/components/ui` не содержат бизнес-логику API; API-вызовы находятся в feature/components и `src/lib/api`.
- Пользовательские строки вынесены в localization-ready словарь `frontend/src/lib/i18n/messages.ts` с `ru` и `en`.
- `/scan` реализует клиентский Food Scan flow поверх backend API: upload/camera file input, polling статуса, review detected items, отображение confidence, estimate mass, min/max uncertainty, КБЖУ, correction controls, add/remove detected item и explicit confirmation.
- UI не показывает массу как точное измерение: estimated grams отображаются как `≈`, рядом показывается диапазон portion estimate, а ручная коррекция массы остаётся отдельным действием пользователя.
- `/diary` подтягивает `GET /api/v1/diary/day/?date=` и показывает дневные totals и meal cards; после confirmation scan frontend открывает дневник за дату созданного meal.
- Component tests для scan review components выполняются через Vitest и `react-dom/server`, без добавления browser token storage или прямых API-вызовов вне centralized API client.
- Frontend quality gate: custom project linter, TypeScript typecheck, Vitest unit tests и `next build`.

## Infrastructure

Локально планируются:

- PostgreSQL.
- Redis.
- MinIO как приватное S3-compatible object storage.

Production-окружение должно использовать deny-by-default, least privilege, приватное object storage и безопасное управление секретами.

Текущее dev-состояние:

- локальная инфраструктура запускается через Docker Compose;
- `postgres` и `redis` не публикуют порты наружу и доступны backend только внутри compose-сети;
- данные PostgreSQL и Redis хранятся в named volumes `postgres_data` и `redis_data`;
- backend container ждёт готовности PostgreSQL и Redis через healthchecks и management command `wait_for_dependencies`;
- vision container имеет собственный healthcheck `GET /health`;
- `celery_worker` ждёт PostgreSQL, Redis, Vision и healthy backend, использует тот же backend image и не запускает migrations параллельно с backend;
- migrations выполняются при старте backend через `migrate --noinput`, если `DJANGO_RUN_MIGRATIONS=true`;
- один понятный запуск для разработки: `make dev-up`.

## API и i18n

Стабильного публичного API пока нет.

API должны:

- использовать versioning, начиная с `/api/v1/`;
- возвращать стабильные machine-readable error codes;
- не связывать клиентов с одним человеческим языком;
- поддерживать локализацию пользовательских сообщений на русский и английский, когда backend генерирует такие сообщения.
