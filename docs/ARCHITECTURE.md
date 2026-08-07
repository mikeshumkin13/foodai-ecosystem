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
- migrations выполняются при старте backend через `migrate --noinput`, если `DJANGO_RUN_MIGRATIONS=true`;
- один понятный запуск для разработки: `make dev-up`.

## API и i18n

Стабильного публичного API пока нет.

API должны:

- использовать versioning, начиная с `/api/v1/`;
- возвращать стабильные machine-readable error codes;
- не связывать клиентов с одним человеческим языком;
- поддерживать локализацию пользовательских сообщений на русский и английский, когда backend генерирует такие сообщения.
