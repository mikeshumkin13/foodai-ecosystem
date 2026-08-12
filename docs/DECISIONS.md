# Decisions / Архитектурные решения

## ADR-0001: Monorepo

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

FoodAI Ecosystem создаётся как monorepo с каталогами `backend`, `frontend`, `services/vision`, `infra`, `docs`, `scripts` и `.github`.

Rationale / Обоснование:

- продукт находится на ранней стадии;
- backend, frontend, vision и infra должны развиваться согласованно;
- документация, security-решения и API-контракты должны жить рядом с кодом.

Consequences / Последствия:

- CI должен учитывать несколько частей проекта;
- изменения нужно держать в логических ветках и PR;
- boundaries между модулями должны быть явно описаны.

## ADR-0002: Modular Django Monolith For Backend

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Backend стартует как модульный Django-монолит.

Rationale / Обоснование:

- MVP-сценарии тесно связаны;
- дневник, фото, permissions, экспорт, удаление данных и расчёт нутриентов требуют согласованности;
- монолит снижает операционную сложность.

Consequences / Последствия:

- Django apps должны иметь понятные границы;
- микросервисы не создаются без конкретной необходимости;
- будущая декомпозиция возможна только после появления реального давления.

## ADR-0003: Separate Vision Service

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Vision размещается отдельно в `services/vision`.

Rationale / Обоснование:

- CV/ML-зависимости отличаются от backend;
- Vision может требовать других CPU/GPU ресурсов;
- сбои обработки изображений нужно изолировать от auth, diary и core API.

Consequences / Последствия:

- backend владеет пользователями и долгосрочными данными;
- Vision получает только минимально необходимый контекст;
- контракт backend/Vision должен быть покрыт тестами.

## ADR-0004: Russian And English Primary Languages

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Основные языки проекта и пользовательского продукта: русский (`ru`) и английский (`en`).

Rationale / Обоснование:

- проектная работа и пользовательский продукт должны поддерживать оба языка;
- safety, consent, notifications и AI-ответы должны быть понятны пользователям на русском и английском;
- локализацию нужно учитывать до появления большого объёма UI и контента.

Consequences / Последствия:

- frontend строки должны быть localization-ready;
- API должны предпочитать стабильные error codes вместо prose-only errors;
- пользовательские backend-сообщения должны быть локализуемыми;
- пользовательский каталог и managed content должны поддерживать языковые варианты при необходимости.

## ADR-0005: Backend Foundation Tooling

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Backend foundation использует Django + Django REST Framework, разделённые settings (`base`, `local`, `production`), drf-spectacular для OpenAPI/Swagger, pytest/pytest-django для тестов, Ruff для lint, mypy для type checking и coverage для оценки покрытия.

Зависимости backend описываются в root `pyproject.toml`. Локальная изоляция выполняется через `.venv` и `pip install -e ".[dev]"`.

Rationale / Обоснование:

- `pyproject.toml` даёт единый современный формат для зависимостей и инструментов;
- `.venv + pip` достаточно просты для раннего monorepo и не добавляют отдельный lock-in;
- OpenAPI нужен сразу, чтобы API-контракты не расходились с реализацией;
- mypy полезен уже на foundation-этапе и пока не создаёт искусственной сложности.

Consequences / Последствия:

- команды backend quality gate живут в root `Makefile`;
- настройки Django должны приходить через environment variables;
- каждый новый backend endpoint должен иметь тест;
- при росте зависимостей можно отдельно принять решение о lock-файле или другом dependency manager.

## ADR-0006: Docker Compose For Local Development Infrastructure

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Локальная инфраструктура разработки запускается через Docker Compose и включает `postgres`, `redis` и `backend`.

Rationale / Обоснование:

- PostgreSQL и Redis нужны backend уже на раннем этапе;
- Docker Compose даёт воспроизводимый локальный запуск одной командой;
- named volumes сохраняют состояние между перезапусками;
- healthchecks и explicit wait command делают порядок старта предсказуемым.

Consequences / Последствия:

- `docker-compose.yml` не должен содержать секреты напрямую;
- значения читаются из `.env`, а `.env.example` содержит только безопасные локальные примеры;
- PostgreSQL и Redis не публикуют host-порты без отдельной необходимости;
- backend ждёт PostgreSQL/Redis перед запуском и выполняет migrations через entrypoint;
- production deployment не обязан использовать этот compose-файл без отдельной адаптации.

## ADR-0007: Custom User Model With UUID And Email Login

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Backend использует custom user model `accounts.User` с `AUTH_USER_MODEL = "accounts.User"`.

`User` хранит только authentication/authorization минимум: UUID primary key, уникальный email как основной логин, password hash через стандартный Django механизм, `is_active`, `is_staff`, timestamps и стандартные permission-связи Django.

Дополнительные пользовательские данные размещаются в `accounts.UserProfile`.

Rationale / Обоснование:

- custom user model нужно вводить до появления доменных моделей и production-данных;
- email-login лучше соответствует потребительскому продукту, чем username;
- UUID снижает риск раскрытия последовательных публичных идентификаторов;
- минимальный `User` уменьшает объём чувствительных данных в auth-сущности;
- health/fitness данные должны жить в отдельных доменных моделях с отдельными permissions и retention rules.

Consequences / Последствия:

- все будущие связи с пользователем должны ссылаться на `settings.AUTH_USER_MODEL`;
- нельзя импортировать `django.contrib.auth.models.User` как доменную модель пользователя;
- `UserProfile` не должен становиться местом для health/fitness данных;
- account API будет проектироваться отдельно и должен сохранять object-level permissions.

## ADR-0008: Centralized RBAC With Django Groups And Permissions

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

RBAC реализуется централизованно через Django Groups/Permissions.

Business roles:

- `user`;
- `support`;
- `content_manager`;
- `admin`.

`superuser` не является business role и остаётся отдельным техническим механизмом Django.

Ролевая матрица и синхронизация групп описаны в `accounts.rbac`. Проверки доступа в API должны использовать централизованные permission-классы, а не распределённые проверки вида `if role == ...` в бизнес-коде.

Rationale / Обоснование:

- Django Groups/Permissions дают стандартный механизм least privilege;
- deny-by-default проще обеспечить на уровне DRF settings и permission classes;
- support и content-management доступы должны развиваться независимо от приватных пользовательских данных;
- object-level permissions нужны с самого начала, чтобы снизить риск IDOR при появлении новых UUID-ресурсов.

Consequences / Последствия:

- новые роли и permissions добавляются через `accounts.rbac`, миграции и `docs/SECURITY.md`;
- новые пользовательские API должны явно тестировать object-level permissions;
- support не получает доступ к health data, фото, дневникам и AI-диалогам без отдельной процедуры и audit log;
- content manager управляет каталогом/контентом, но не приватными дневниками пользователей;
- admin получает административные permissions, но не заменяет `superuser`;
- `superuser` не должен использоваться для повседневной работы.

## ADR-0009: Web Authentication With Django Session Cookies

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Для web-клиента FoodAI Ecosystem использует Django session-cookie authentication:

- backend не выдаёт browser-facing access token;
- access token не хранится в `localStorage`;
- session идентификатор хранится в cookie `sessionid`;
- `sessionid` должен быть `HttpOnly`;
- `Secure` включается в production через environment variables;
- `SameSite` по умолчанию `Lax`;
- unsafe requests требуют CSRF token/header;
- `GET /api/v1/auth/csrf/` выдаёт CSRF cookie/token для web-клиента;
- `POST /api/v1/auth/refresh/` продлевает session, выполняет session key rotation и CSRF rotation.

Refresh token rotation/revocation для bearer token scheme не реализуется на этом этапе, потому что выбранная web-схема не выдаёт bearer refresh token. Logout выполняет `session.flush()`, password change обновляет текущий session auth hash и инвалидирует другие sessions через стандартный Django password hash mechanism.

Email verification и password reset используют одноразовые DB tokens:

- raw token отправляется только через email backend;
- в БД хранится только SHA-256 hash;
- старые unused tokens отзываются при выпуске нового token;
- token помечается `used_at` после успешного применения;
- password reset request всегда возвращает generic response, чтобы не раскрывать наличие аккаунта.

Rationale / Обоснование:

- session-cookie схема снижает риск XSS-кражи bearer access token из browser storage;
- Django уже предоставляет зрелые session, CSRF и password hashing механизмы;
- `HttpOnly` session cookie отделяет credential от JavaScript;
- CSRF защита обязательна, потому что browser автоматически отправляет cookies;
- одноразовые hashed DB tokens дают простую revocation-модель без хранения plaintext secrets.

Consequences / Последствия:

- frontend должен выполнять requests с credentials и передавать `X-CSRFToken` для unsafe методов;
- CORS должен оставаться строгим allowlist и использовать credentials только для доверенных origins;
- production должен включать `DJANGO_SESSION_COOKIE_SECURE=true` и `DJANGO_CSRF_COOKIE_SECURE=true`;
- production email backend должен быть настроен отдельно, без логирования raw tokens;
- мобильное приложение или B2B API могут потребовать отдельную token-схему в будущем через отдельное ADR;
- OAuth не реализуется в этом этапе.

## ADR-0010: Protected Django Admin And Admin Audit Foundation

Date / Дата: 2026-08-07

Status / Статус: Accepted / принято

Decision / Решение:

Django Admin используется как внутренний административный foundation для раннего backend.

На этом этапе в admin регистрируются:

- `accounts.User`;
- `accounts.UserProfile`;
- Django `Group` как управление role groups;
- read-only `accounts.AdminAuditLog`.

Email verification и password reset token-модели не регистрируются в admin. Bulk actions отключаются для зарегистрированных admin-моделей.

`AdminAuditLog` зеркалирует стандартный Django `django_admin_log` через signal и хранит минимальные metadata: actor, action, model label, object id, sanitized object representation, change message и timestamps. Account object representations редактируются до `app.model:object_id`, чтобы не переносить email/profile/token-строки в audit trail без необходимости.

Support и Content Manager не получают доступ к чувствительным account/audit/role models по умолчанию. Для будущих справочников и food catalog добавлены централизованные permission foundations, но доменные food catalog модели будут вводиться отдельной задачей.

Rationale / Обоснование:

- Django Admin нужен для раннего операционного управления пользователями и ролями без разработки отдельной back-office UI.
- Least privilege требует, чтобы support/content роли не получали доступ к приватным дневникам, фото, health data, AI-диалогам, профилям и audit log без отдельного решения.
- Audit trail административных действий нужен до появления production-данных.
- Token metadata не должна появляться в admin без явной необходимости.
- Создание настоящих food catalog моделей вне catalog-этапа увеличило бы доменную поверхность раньше времени.

Consequences / Последствия:

- Новые admin-модели должны иметь search/filter/readonly/timestamps, если это применимо.
- Чувствительные модели нельзя регистрировать в admin без отдельной оценки доступа и audit-поведения.
- Все admin permissions добавляются через `accounts.rbac`, миграции и `docs/SECURITY.md`.
- Support/content-manager admin visibility должна покрываться тестами.
- `AdminAuditLog` read-only; изменение или удаление audit records через обычный admin запрещено.
