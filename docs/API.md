# API / API-документация

Стабильного публичного API пока нет.

## Принципы API

- Использовать versioning, начиная с `/api/v1/`.
- Требовать authentication для приватных ресурсов.
- Проверять object-level permissions для каждого пользовательского объекта.
- Не раскрывать последовательные публичные ID там, где оправданы UUID.
- Предпочитать стабильные machine-readable error codes вместо ошибок только в виде текста.
- Возвращать структурированные validation errors.
- Не включать чувствительные данные в ошибки и логи.
- Контракты AI и Vision должны быть явными и покрытыми тестами.

## Локализация

Основные пользовательские языки: русский (`ru`) и английский (`en`).

API не должен привязывать клиентов к одному человеческому языку. Если backend генерирует пользовательский текст, он должен проектироваться с локализацией на русский и английский.

## Планируемые области API

- Auth и account management.
- User profile и privacy controls.
- Food photo upload.
- Vision recognition job status.
- Meal diary.
- Nutrition catalog.
- Goals.
- Daily summaries.
- Data export и deletion.
- AI assistant conversations с safety boundaries.

## Текущие endpoint-ы

- `GET /api/v1/health/` — проверка доступности backend. Ответ: `{"status": "ok"}`.
- `GET /api/v1/accounts/profiles/{id}/` — чтение `UserProfile`.
- `PUT/PATCH /api/v1/accounts/profiles/{id}/` — обновление `UserProfile`.
- `GET /api/v1/schema/` — OpenAPI schema.
- `GET /api/v1/docs/` — Swagger UI.

В Docker Compose health endpoint используется также для backend healthcheck после ожидания PostgreSQL/Redis и выполнения migrations.

Account API пока реализован только минимально для `UserProfile`.

Правила доступа:

- unauthenticated requests запрещены для account API;
- обычный `user` читает и изменяет только собственный профиль;
- обращение User A к UUID профиля User B не возвращает чужие данные;
- `support` и `content_manager` не получают доступ к пользовательским профилям по умолчанию;
- `admin` с permission `accounts.administer_accounts` может работать с профилями;
- `superuser` использует технический Django override.

## Breaking changes

Breaking API changes требуют:

1. документированного решения в `docs/DECISIONS.md`;
2. обновления `docs/API.md`;
3. тестов на новое поведение.
