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
