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
