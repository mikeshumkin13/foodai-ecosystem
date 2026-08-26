# MVP QA Report / Отчёт по качеству MVP

Дата аудита: 2026-08-26

Проверяемая ветка: `develop`

Проверяемый commit: `8b09884a06966555579be1f9a5712ea0f97ae265`

Режим работы: аудит без создания feature-ветки и без исправления найденных проблем.

## Итог

**Вердикт: MVP пока не готов к пользовательскому release.**

Backend-домен, permissions, snapshots, nutrition calculation, privacy foundation и scan confirmation
имеют хорошее автоматическое покрытие. Обязательный web-сценарий при этом разрывается на регистрации,
редактировании профиля и AI nutrition summary. Дополнительно подтверждены неуправляемые HTTP 500 при
недоступном Celery broker и runtime-сбое AI provider.

Найдено:

| Severity | Количество |
|---|---:|
| BLOCKER | 3 |
| CRITICAL | 0 |
| HIGH | 7 |
| MEDIUM | 5 |
| LOW | 2 |

## Методика

- Выполнен статический аудит Django, FastAPI, Celery и Next.js слоёв.
- Проверены API routes, permissions, object ownership, storage boundaries и frontend API clients.
- Выполнен полный локальный quality gate `make check`.
- Выполнены migration check, OpenAPI validation, dependency check и Docker Compose validation.
- Проверены Compose startup и healthchecks как на существующем local volume, так и на свежей
  изолированной PostgreSQL/Redis среде.
- Выполнены два временных failure probe из `/tmp`, не изменявших репозиторий:
  runtime timeout AI provider и отказ Celery broker при enqueue.
- Сценарии ownership, IDOR, roles, privacy, Vision failure и Celery retry сопоставлены с
  существующими integration tests.
- Полного browser E2E теста нет в проекте; это отдельная находка аудита, а не доказательство
  успешного пользовательского сценария.

## Основной сценарий

| Шаг | Статус | Результат |
|---|---|---|
| Register | FAIL | Backend создаёт inactive user и письмо, но frontend сразу отправляет на `/dashboard`; UI подтверждения email отсутствует. |
| Login | PARTIAL | Backend session-cookie login, CSRF и rate limit работают; новый пользователь не может дойти до login через полный UI onboarding. |
| Profile | FAIL | API существует, но `/profile` является статической формой без загрузки, submit и сохранения. |
| Food photo | PASS | JPEG/PNG проверяются по фактическому формату, размеру и pixel count; EXIF удаляется, object key безопасный и приватный. |
| Scan processing | PARTIAL | Асинхронная обработка, polling и controlled retry реализованы; отказ broker при enqueue не обработан. |
| Detected food | PARTIAL | Catalog matching и confidence работают, но Vision v1 возвращает один dish-level class и не выделяет несколько продуктов. |
| Estimated portion | PARTIAL | Estimator возвращает массу, объём, диапазон, confidence и method; для обычного фото без geometry используется низкоуверенный typical-volume fallback. |
| Correction | PASS | Можно менять food и массу, удалять detected item и добавлять отсутствующий; initial estimate сохраняется отдельно. |
| Nutrition calculation | PASS | Единый Decimal-based domain service используется и manual flow, и scan flow. |
| Confirm | PASS | До подтверждения Meal не создаётся; повторное подтверждение не создаёт дубликаты. |
| Diary | PASS | CRUD, date filter, day aggregation, snapshots и owner isolation реализованы. |
| Dashboard | PASS | Показывает дневные calories, target, БЖУ и meals; зависит от API profile, который нельзя заполнить через UI. |
| AI nutrition summary | FAIL | Backend endpoint есть, но frontend route/client/экран отсутствуют; production LLM provider не подключён. |

## Дополнительные сценарии

| Сценарий | Статус | Результат |
|---|---|---|
| Ручное добавление без AI | PASS | Diary UI позволяет искать catalog food, задавать массу и создавать/редактировать Meal. |
| Два разных пользователя | PASS | Backend integration tests создают независимых пользователей и ресурсы. |
| Cross-user isolation / IDOR | PASS | Чужие profile, nutrition profile, sensitive restrictions, meal, scan и photo возвращают 404/deny. |
| User permissions | PASS | Доступ к приватным сущностям ограничен владельцем. |
| Support | PASS | Нет доступа к diary, health profile, photos и AI history по умолчанию; admin-модели скрыты. |
| Content Manager | PASS | Может менять nutrition catalog, но не получает приватные дневники и health data. |
| Admin | PASS | Получает централизованные admin permissions и read-only audit trail; опасные bulk actions отключены. |
| Privacy photo delete | PASS | Удаляются DB row и private object; stale task после удаления пропускается. |
| Privacy AI history delete | PASS | Удаляется только история текущего пользователя. |
| Privacy account delete | PARTIAL | DB/storage/session/cache happy path покрыт; нет компенсации при частичном cross-system failure. |
| Data export | PASS | Экспорт owner-only, без password и private object key; операция аудируется. |
| Failed Vision | PASS | Timeout/unavailable имеют controlled retry и завершают scan в `failed` после лимита. |
| Failed Celery task | PASS | Runtime task exception переводит текущий scan в `failed`; enqueue failure остаётся проблемой. |
| Failed AI provider | FAIL | Configuration error преобразуется в 503, но runtime exception/timeout даёт 500. |
| Compose на текущем local volume | FAIL | Сохранённая migration history несовместима с custom User migration; backend перезапускается. |
| Compose на свежей БД | PASS | Все migrations применены; PostgreSQL, Redis, Vision, backend и Celery healthy. |

## BLOCKER

### MVP-QA-001 — frontend onboarding обрывается после регистрации

**Evidence:** `frontend/src/features/auth/register-form.tsx`, `frontend/src/lib/api/auth.ts`,
`backend/accounts/views.py`, `backend/accounts/tests/test_auth_api.py`.

После успешного `POST /auth/register/` frontend выполняет `window.location.assign("/dashboard")`.
Backend создаёт `is_active=False`, а login до email verification ожидаемо отклоняется. Во frontend нет
страницы verify, обработки verification link, resend и состояния «проверьте почту».

**Impact:** новый пользователь не может завершить регистрацию и основной MVP flow через web client.

**Исправление (PROMPT 30):** устранено в `feature/mvp-frontend-flow`. После регистрации UI показывает
состояние ожидания подтверждения и позволяет повторно отправить письмо. Добавлен route
`/auth/email/verify`, который обрабатывает одноразовую ссылку и не пропускает неактивного
пользователя в защищённую часть приложения.

### MVP-QA-002 — nutrition profile нельзя загрузить или сохранить через UI

**Evidence:** `frontend/src/app/profile/page.tsx`, `frontend/src/lib/api/profile.ts`.

Страница отображает поля, но не вызывает profile API, не содержит form submit, save state, consent
controls и обработку ошибок. Имена визуальных полей также не связаны с API payload
`height_cm`/`mass_kg`.

**Impact:** шаг profile не работает; dashboard target и AI context остаются неполными.

**Исправление (PROMPT 30):** устранено в `feature/mvp-frontend-flow`. `/profile` загружает только
собственный nutrition profile через endpoint `me`, сохраняет его по UUID через centralized API
client и поддерживает loading/error/saved states. Первое изменение требует явного consent; точный
возраст не собирается, а sensitive restrictions не смешиваются с обычными preferences.

### MVP-QA-003 — AI nutrition summary отсутствует во frontend

**Evidence:** список `frontend/src/app/*/page.tsx`, `frontend/src/components/app-shell.tsx`,
`frontend/src/lib/api`.

Нет route, API client, navigation item и UI для `POST /api/v1/ai/coach/ask/`.

**Impact:** обязательный заключительный шаг основного сценария недоступен пользователю.

## CRITICAL

Подтверждённых CRITICAL проблем в границах этого аудита не найдено. Это не означает, что система
«полностью безопасна» или готова к production.

## HIGH

### MVP-QA-004 — отсутствует единое управление authenticated session во frontend

`authApi.me()`, `authApi.logout()` и `authApi.refresh()` не используются UI. Protected pages не имеют
route guard, logout control и централизованной реакции на 401/403. Anonymous user видит shell и
получает разрозненные API errors вместо перехода на login.

**Исправление (PROMPT 30):** устранено в `feature/mvp-frontend-flow`. Добавлен единый session
provider, owner pages закрыты проверкой `/auth/me/`, 401/unauthenticated 403 переводят пользователя
на login с безопасным same-site `next`, в shell добавлен logout. Активная Django session продлевается
через `/auth/refresh/`; после login/refresh очищается устаревший in-memory CSRF token.

### MVP-QA-005 — Celery broker failure оставляет scan без задачи

`food_scans.jobs.enqueue_food_scan_analysis()` сначала сохраняет `uploaded` и task metadata, затем
вызывает `apply_async()` без обработки ошибки. Временный probe подтвердил HTTP 500 и оставшийся
`FoodScan(status="uploaded", failure_code="")`, хотя задача не поставлена в очередь.

### MVP-QA-006 — runtime failure и timeout AI provider не нормализованы

`AICoachAskView` обрабатывает только `AICoachProviderConfigurationError`. Runtime exception или
timeout provider проходит как HTTP 500. Настройка `AI_COACH_PROVIDER_TIMEOUT_SECONDS` объявлена, но
не используется в provider call boundary. Временный probe подтвердил HTTP 500.

### MVP-QA-007 — production AI provider не реализован

`get_ai_coach_provider()` поддерживает только `mock`. Это корректно для foundation/tests, но текущая
AI summary является детерминированным шаблоном, а не интеграцией с production provider.

### MVP-QA-008 — Vision v1 не покрывает основной multi-food use case

Модель `nateraw/food` является Food-101 dish classifier: один top label, без object detection,
segmentation и plate reference. На обычном фото portion estimator обычно использует
low-confidence typical-volume fallback. Ограничение честно документировано, но качество основного
ценностного сценария не валидировано на representative MVP dataset.

### MVP-QA-009 — отсутствует browser E2E quality gate

Во frontend есть 7 Vitest files / 10 tests, но нет Playwright/Cypress сценария register → diary →
dashboard. Текущие BLOCKER-разрывы не обнаруживаются CI, потому что страницы проверяются отдельно и
production build не проверяет поведение.

### MVP-QA-010 — существующий local PostgreSQL volume не запускается после custom User migration

Обычный `docker compose up` на сохранённом `foodai-ecosystem_postgres_data` завершается
`InconsistentMigrationHistory`: `admin.0001_initial` применена раньше зависимости
`accounts.0001_initial`. Backend становится unhealthy, Celery не стартует. На новой изолированной
БД текущий migration graph применяется полностью и все сервисы healthy.

**Impact:** текущая локальная среда пользователя не запускается без осознанного recovery/reset;
удалять volume автоматически нельзя, потому что это уничтожит данные. Нужны документированный
recovery path и проверка, есть ли в старой БД ценные данные.

## MEDIUM

### MVP-QA-011 — выбор русского/английского языка не применяется

RU/EN messages существуют, но все страницы и компоненты используют `messages.ru`, а root layout
жёстко задаёт `lang="ru"`. Сохранённый `preferred_language="en"` не влияет на интерфейс.

### MVP-QA-012 — password reset и password change не доступны из web client

Backend endpoints и security tests существуют, но frontend не содержит API methods, страниц и
переходов восстановления/изменения пароля.

### MVP-QA-013 — CI не проверяет PostgreSQL и Redis integration

Backend CI использует SQLite in-memory, Celery memory broker и не поднимает PostgreSQL/Redis service
containers. Миграции и большинство domain tests проверяются, но различия SQL, connections и broker
integration могут проявиться только вне CI.

### MVP-QA-014 — account deletion не имеет компенсации между storage и PostgreSQL

Private objects удаляются до database transaction. Если последующее DB/audit удаление завершится
ошибкой, файлы уже потеряны, а account rows могут остаться. Happy path и stale-task protection
покрыты, failure injection/compensation workflow отсутствует.

### MVP-QA-015 — production S3-compatible storage backend не реализован

`PrivateObjectStorage` является корректной abstraction boundary, но factory поддерживает только
локальную файловую систему. Production deploy check закономерно выдаёт `foodai_security.W002`.
Private S3-compatible bucket, credentials boundary и signed access остаются до production release.

## LOW

### MVP-QA-016 — устаревающая связка FastAPI TestClient/httpx

Полный pytest выдаёт `StarletteDeprecationWarning` о текущем TestClient/httpx integration. Сейчас
тесты проходят, но dependency update может сделать warning ошибкой.

### MVP-QA-017 — backend Docker layer cache неэффективен

Dockerfile копирует backend source до `pip install -e ".[dev]"`, поэтому обычное изменение Python
кода инвалидирует дорогой dependency layer. Это не runtime defect, но заметно замедляет повторные
проверки и CI/local build.

## Подтверждённо работающие области

- Cookie/session authentication без access token в `localStorage`, CSRF checks и auth throttles.
- UUID ownership filters и deny-by-default permissions для приватных API.
- Nutrition catalog RBAC и расширяемые `Nutrient`/`FoodNutrient`.
- Decimal calculation для 0/50/100/250 g, missing nutrient и negative mass validation.
- Неизменяемые исторические nutrient snapshots MealItem после изменения catalog.
- Scan correction, explicit confirmation и idempotent confirmation boundary.
- Private upload validation, EXIF removal и отсутствие permanent public URL.
- Vision timeout/unavailable classification, bounded retry и stale-task protection.
- Privacy consent default-off для model improvement и food photo training.
- Export/delete ownership, account deletion happy path и audit events.
- AI safety/moderation и минимизация передаваемого provider context.

## Выполненные проверки

| Проверка | Результат |
|---|---|
| `make check` | PASS |
| Ruff | PASS |
| mypy | PASS, 177 source files |
| Django system check | PASS |
| pytest | PASS, 249 tests |
| Coverage | PASS, 88.66% при минимуме 80% |
| Frontend lint | PASS, 55 files |
| Frontend typecheck | PASS |
| Vitest | PASS, 7 files / 10 tests |
| Next.js production build | PASS, 11 routes |
| `makemigrations --check --dry-run` | PASS, no changes detected |
| OpenAPI `spectacular --validate` | PASS |
| `docker compose config --quiet` | PASS |
| Docker build backend/Vision/Celery | PASS |
| Compose startup на существующем volume | FAIL: inconsistent historical migrations |
| Compose startup на свежих volumes | PASS: 5/5 services healthy, health endpoint OK |
| Production deploy check | PASS с известным warning `foodai_security.W002` |
| `pip check` | PASS, broken requirements отсутствуют |
| Temporary failure probes | PASS: подтверждены два ожидаемых дефекта HTTP 500 |

## Предлагаемые feature branches

Ветки перечислены в порядке выполнения. На этом этапе они **не создавались**.

1. `feature/mvp-onboarding-flow` — email verification/resend UI, корректный post-register state.
2. `feature/frontend-nutrition-profile` — рабочая profile form, consent и сохранение.
3. `feature/frontend-ai-nutrition-coach` — AI summary route, client, states и safety presentation.
4. `feature/frontend-auth-session` — route guard, `me`, logout и session expiry handling.
5. `feature/celery-enqueue-resilience` — broker failure state, recoverable retry и tests.
6. `feature/dev-postgres-migration-recovery` — безопасный recovery/documentation для старого volume.
7. `feature/ai-provider-resilience` — timeout boundary, normalized 503 и runtime failure tests.
8. `feature/ai-provider-production` — выбранный provider adapter, schema validation и privacy review.
9. `feature/vision-mvp-validation` — representative licensed dataset, acceptance metrics и benchmark.
10. `feature/mvp-browser-e2e` — Playwright для onboarding, manual diary, scan и privacy smoke flows.
11. `feature/frontend-i18n-runtime` — применение RU/EN locale во всём client UI.
12. `feature/frontend-account-recovery` — reset/change password screens и API integration.
13. `feature/ci-postgres-redis` — PostgreSQL/Redis integration job без production secrets.
14. `feature/privacy-deletion-resilience` — failure compensation/reconciliation для object storage.
15. `feature/production-object-storage` — private S3-compatible backend и signed access policy.
16. `feature/dependency-maintenance` — TestClient/httpx compatibility и Docker cache layers.

## Release gate

До MVP release необходимо закрыть все BLOCKER, повторить полный backend/frontend quality gate и
добавить browser E2E для основного пользовательского сценария. HIGH findings по Celery/AI failure
handling должны быть закрыты до предоставления scan/AI функций внешним пользователям. Ограничения
Vision должны быть подтверждены продуктовым acceptance threshold на разрешённом validation dataset.
