# MVP QA Report / Отчёт по качеству MVP

## Повторная проверка этапа 30

Завершено: 2026-09-14. Интеграционная ветка: `feature/mvp-high-priority-integration`.
Проверяемый код: `e09f085` (ниже сохранён исходный аудит этапа 29).

**Этап 30 завершён в локальной интеграционной ветке.** Исправления 12 BLOCKER/HIGH находок
собраны из семи независимых feature-веток. Все обязательные локальные проверки прошли;
основной MVP flow повторно выполнен после финальной Docker-сборки.
MEDIUM/LOW намеренно не исправлялись. Merge в `develop` и `main` не выполнялся.

| Severity | Исправлено в этапе 30 | Осталось в границах QA |
|---|---:|---:|
| BLOCKER | 4 | 0 |
| CRITICAL | 0 | 0 |
| HIGH | 8 | 0 |
| MEDIUM | 0 | 5 |
| LOW | 0 | 2 |

В число исправлений включены две дополнительные находки повторного QA: 018 и 019.

### Группы исправлений

| Ветка | Commit | Находки |
|---|---|---|
| `feature/mvp-frontend-flow` | `aa490e5` | 001, 002, 003, 004, 009: onboarding, session, profile, coach, browser tests |
| `feature/celery-enqueue-resilience` | `bc011b4` | 005: recoverable broker enqueue failure |
| `feature/ai-provider-production` | `2f3bb11` | 006, 007: provider abstraction, timeout, output schema и 503 |
| `feature/vision-mvp-validation` | `aa78e30` | 008: multi-region inference и licensed exploratory benchmark |
| `feature/dev-postgres-migration-recovery` | `8a6bca7` | 010: versioned volume, inspect/backup без удаления старой БД |
| `feature/vision-runtime-connectivity` | `0a204de` | 018: private mount, warm-up и timeout budgets |
| `feature/scan-confirmation-postgres` | `674a63a` | 019: блокировка только FoodScan, без nullable outer join lock |

Frontend-связанные исправления разделены на осмысленные commits внутри одной группы. Security,
broker, database recovery и ML runtime не смешивались с frontend commits. Все ветки сохранены.

### Сквозной сценарий

2026-09-10, затем повторно 2026-09-14 на финальных Docker-образах выполнен локальный smoke
через Django APIClient с настоящими cookie sessions и
`enforce_csrf_checks=True`. Использовались PostgreSQL 16, Redis, отдельный Celery worker и
реальная прогретая Vision-модель. Celery eager mode отключён. Два временных QA-пользователя
зарегистрированы через API; email verification прочитана из in-memory mail backend.

| Шаг | Результат |
|---|---|
| Register → verification → login | PASS: два независимых активированных аккаунта и cookie sessions |
| Profile | PASS: owner-only чтение/сохранение, consent; чужой UUID возвращает 404 |
| Photo → Celery → Vision | PASS: реальный JPEG из разрешённого fixture, асинхронный анализ и `needs_confirmation` |
| Detected food → estimated portion | PASS: proposals/оценка поступили из реального pipeline; точность массы не заявляется |
| Correction | PASS: исправление food/200 г, удаление лишних и добавление chicken/100 г; исходная оценка сохранена |
| Calculation → confirm | PASS: rice 200 г = 260 ккал; 2 MealItem; повторный confirm возвращает тот же Meal |
| Ручное добавление без AI | PASS: отдельный snack rice 50 г; не зависит от Vision/Celery |
| Snapshot → diary | PASS: изменение тестового FoodNutrient не меняет MealItem; 2 приёма пищи, 490 ккал за дату |
| Cross-user isolation | PASS: чужие profile, scan/results/confirm, meal и photo delete возвращают 404; чужой дневник пуст |
| AI nutrition summary | PASS: schema и дневные агрегаты проверены с mocked LLM; context без email/UUID, история не сохраняется |
| Export → photo/account delete | PASS: экспорт без password/object key, файл удалён из storage, второй аккаунт не затронут |
| Cleanup | PASS: удалены только созданные QA-аккаунты, фото и food entries; audit records сохранены |

Последний асинхронный анализ занял 23.01 секунды и вернул 3 предложения. Дополнительно проверены
наличие первоначальной оценки, `min_estimate <= estimated_mass <= max_estimate` и confidence
в диапазоне `[0, 1]`. Это наблюдение на одном fixture, не SLA или оценка accuracy.

Dashboard и пользовательские переходы дополнительно покрываются production-browser Playwright
сценариями; там API детерминированно подменён. Это два дополняющих уровня проверки, а не заявление
о едином browser-тесте со всеми production-зависимостями. Реальная доставка SMTP и платный LLM API
не вызывались. Отказы Vision/Celery/AI, роли support/content_manager/admin, privacy и safety
проверяются отдельными автоматическими regression tests.

PostgreSQL regression gate: **36 passed** за 48.60 секунды. Проверялись
`test_postgres_confirmation.py`, `test_scan_orchestration.py`, `test_background_jobs.py` и
`test_food_diary_api.py` на отдельной тестовой БД, без замены PostgreSQL на SQLite.

### Итоговые проверки

| Проверка | Результат |
|---|---|
| Ruff | PASS |
| mypy backend/Vision | PASS, 183 source files |
| Django system check | PASS |
| Общий pytest backend/Vision/contract | PASS, 287 tests; coverage 88.02%, минимум 80% |
| PostgreSQL regression | PASS, 36 tests на отдельной тестовой PostgreSQL БД |
| Migration dry-run / applied migrations | PASS, нет drift и неприменённых migrations |
| OpenAPI validation / `pip check` | PASS |
| Frontend frozen install | PASS, lockfile не изменён, 412 packages из cache |
| Frontend lint / TypeScript | PASS, lint 69 files |
| Vitest | PASS, 12 files / 21 tests |
| Next.js production build | PASS, 13 static pages generated |
| Playwright Desktop Chromium | PASS, 3 tests |
| Дополнительный Mobile Chromium 390×844 | PASS, те же 3 сценария; QA-скриншоты просмотрены |
| Docker Compose config / backend, Vision, Celery build | PASS |
| Финальный Compose startup | PASS, PostgreSQL/Redis/backend/Vision/Celery: 5/5 healthy |
| Реальный scan/diary/privacy smoke | PASS на пересобранных образах 2026-09-14 |
| Реальный offline Vision benchmark | PASS exploratory gate; recall 0.48, 8 crop, см. `VISION_VALIDATION.md` |
| Production deploy check | PASS с известным `foodai_security.W002` о local storage |
| `git diff --check` | PASS |

Python-часть `make check` прошла 2026-09-10 на том же коде `e09f085`. Frontend-часть первоначально
остановилась из-за sandbox `ENOTFOUND` при доступе к npm/package store. После frozen install
с разрешённым доступом `pnpm check` полностью прошёл 2026-09-14. Проверки не отключались,
пороги coverage/benchmark не снижались ради завершения. Остаётся известный сторонний
`StarletteDeprecationWarning`; в Playwright есть не влияющее на результат предупреждение NO_COLOR.

### Границы результата

- Vision exploratory recall `0.48` на восьми crop не доказывает пользовательскую точность;
  benchmark и CPU latency приведены в `VISION_VALIDATION.md`. Любой scan требует подтверждения.
- Portion estimation остаётся оценкой по ограниченным данным, не измерением точной массы.
- LLM transport проверен mocked HTTP/LLM tests; live quality, RU/EN safety eval и доступность
  выбранной модели в конкретном provider account требуют отдельной проверки.
- MEDIUM: runtime RU/EN, password recovery UI, PostgreSQL/Redis CI, deletion compensation и
  production private S3. LOW: TestClient warning и Docker dependency cache.
- Локальные feature-ветки не отправлялись в GitHub на этапе итоговой интеграции; PR/remote CI и
  merge не заявляются выполненными. `main` и `develop` не изменены.
- Закрытие этапа 30 не означает готовность к production или отсутствие иных уязвимостей.

## Исходные данные этапа 29

Дата аудита: 2026-08-26

Проверяемая ветка: `develop`

Проверяемый commit: `8b09884a06966555579be1f9a5712ea0f97ae265`

Режим работы: аудит без создания feature-ветки и без исправления найденных проблем.

## Исходный итог этапа 29

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

## Методика этапа 29

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

## Основной сценарий на момент этапа 29

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

## Дополнительные сценарии на момент этапа 29

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

**Исправление (PROMPT 30):** устранено в `feature/mvp-frontend-flow`. Добавлен protected route
`/coach`, пункт навигации и centralized client для settings/ask endpoints. UI отображает только
структурированные части schema `ai_nutrition_coach_response_v1`, отдельно показывает safety result
и не сохраняет конкретный запрос/ответ без включённого history consent и отдельного выбора
`store_response`.

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

**Исправление (PROMPT 30):** устранено в `feature/celery-enqueue-resilience`. Ошибка enqueue
переводит ещё не начавшийся run в `failed/task_enqueue_failed`, очищает task metadata и возвращает
стабильный `scan_id/status` вместо HTTP 500. Уже начавшийся `processing` run не перезаписывается;
автоматический retry не выполняется. Добавлены regression tests upload, retry и sanitization
error-monitoring metadata.

### MVP-QA-006 — runtime failure и timeout AI provider не нормализованы

`AICoachAskView` обрабатывает только `AICoachProviderConfigurationError`. Runtime exception или
timeout provider проходит как HTTP 500. Настройка `AI_COACH_PROVIDER_TIMEOUT_SECONDS` объявлена, но
не используется в provider call boundary. Временный probe подтвердил HTTP 500.

**Исправление (PROMPT 30):** устранено в `feature/ai-provider-production`. Provider-specific и
неожиданные runtime errors преобразуются в typed boundary errors; API возвращает generic HTTP 503.
OpenAI adapter использует реальный timeout, а telemetry содержит только безопасные operation/provider
metadata. Добавлены regression tests для timeout и произвольного runtime exception.

### MVP-QA-007 — production AI provider не реализован

`get_ai_coach_provider()` поддерживает только `mock`. Это корректно для foundation/tests, но текущая
AI summary является детерминированным шаблоном, а не интеграцией с production provider.

**Исправление (PROMPT 30):** устранено в `feature/ai-provider-production`. Добавлен production
adapter OpenAI Responses API с конфигурируемой `gpt-5.6-luna`, `store=false`, strict Structured
Outputs и повторной локальной валидацией недоверенного ответа. `mock` сохранён только для local/tests;
production settings требуют секрет через environment. Live provider quality всё ещё требует
отдельного RU/EN eval dataset и не заявляется как доказанная.

### MVP-QA-008 — Vision v1 не покрывает основной multi-food use case — исправлено в этапе 30

Модель `nateraw/food` является Food-101 dish classifier: один top label, без object detection,
segmentation и plate reference. На обычном фото portion estimator обычно использует
low-confidence typical-volume fallback. Ограничение честно документировано, но качество основного
ценностного сценария не валидировано на representative MVP dataset.

**Исправление:** в `feature/vision-mvp-validation` добавлен сменяемый multi-region pipeline на
Grounding DINO Tiny с pinned revision, NMS и ограничением regions. Конкретные detector labels
нормализуются к allowlist; для общих regions сохраняется Food-101 classifier fallback. Internal
contract расширен optional `bounding_box`, который намеренно не используется как segmentation area
для расчёта массы.

Добавлен лицензированный exploratory fixture из официальной FoodSeg103 demonstration figure и
воспроизводимый acceptance benchmark. Результат на восьми crop: `multi_region_rate=1.0`,
`expected_label_recall=0.48`, `confidence_coverage=1.0`, CPU p50 `12428.854 ms`. HIGH-дефект
отсутствия multi-food capability и validation gate закрыт. Низкая label accuracy, semantic
duplicates, CPU latency и отсутствие segmentation остаются рисками Beta; все detections требуют
подтверждения пользователя.

### MVP-QA-009 — отсутствует browser E2E quality gate

Во frontend есть 7 Vitest files / 10 tests, но нет Playwright/Cypress сценария register → diary →
dashboard. Текущие BLOCKER-разрывы не обнаруживаются CI, потому что страницы проверяются отдельно и
production build не проверяет поведение.

**Исправление (PROMPT 30):** устранено в `feature/mvp-frontend-flow`. Добавлен Playwright Chromium
gate с browser-сценариями registration → email verification → login → dashboard,
profile → AI nutrition summary и upload → detected food → confirmation → diary. E2E использует
контролируемый mock API, не требует production secrets/LLM/Vision weights и запускается отдельным
обязательным шагом frontend CI.

### MVP-QA-010 — существующий local PostgreSQL volume не запускается после custom User migration — исправлено в этапе 30

Обычный `docker compose up` на сохранённом `foodai-ecosystem_postgres_data` завершается
`InconsistentMigrationHistory`: `admin.0001_initial` применена раньше зависимости
`accounts.0001_initial`. Backend становится unhealthy, Celery не стартует. На новой изолированной
БД текущий migration graph применяется полностью и все сервисы healthy.

**Impact:** текущая локальная среда пользователя не запускается без осознанного recovery/reset;
удалять volume автоматически нельзя, потому что это уничтожит данные. Нужны документированный
recovery path и проверка, есть ли в старой БД ценные данные.

**Исправление (PROMPT 30):** local Compose использует versioned physical volume
`foodai-ecosystem_postgres_data_v2`, поэтому обычный запуск больше не подключает несовместимую
историю. Legacy volume сохраняется. Добавлен non-destructive recovery script для inspect и
проверенного custom-format backup; migrations, restore и удаление volume скрипт не выполняет.

Фактическая инспекция `foodai-ecosystem_postgres_data` на текущей машине показала только
`admin.0001–0003`, `auth_user=0` и отсутствие FoodAI domain tables. Backup создан и проверен через
`pg_restore --list`. На свежем v2 volume все migrations применились в корректном порядке,
PostgreSQL/Redis/backend стали healthy, `migrate --check` и `/api/v1/health/` прошли. Если на другой
машине legacy volume содержит данные, остаётся обязательным отдельный контролируемый data migration.

## Дополнительные находки при повторной проверке этапа 30

### MVP-QA-018 (HIGH) — healthy Vision не мог обработать локальную фотографию

У Vision отсутствовал mount приватного каталога, в который backend сохраняет подготовленное
изображение. Кроме того, прежний timeout 2 секунды был короче измеренного CPU inference.
Health endpoint без загрузки модели не доказывал готовность к анализу.

**Исправление:** `feature/vision-runtime-connectivity`, commit `0a204de`. Один private каталог
монтируется в backend/Celery и только для чтения в Vision. Добавлены persistent model cache,
прогрев в том же процессе до запуска HTTP и согласованные бюджеты времени 60/90/120 секунд.
Контракт проверяется `backend/core/tests/test_vision_runtime.py`; архитектура описана в ADR-0034.
Это локальная файловая интеграция, а не реализация production S3.

### MVP-QA-019 (BLOCKER) — первое подтверждение scan падало в PostgreSQL

Живой сквозной тест остановился на `POST /food-scans/{id}/confirm/`:
`FOR UPDATE cannot be applied to the nullable side of an outer join`.
`select_related("confirmed_meal")` создавал nullable outer join, к которому применялась блокировка.
SQLite не выявляла ошибку, поскольку не выполняет такую блокировку строк.

**Исправление:** `feature/scan-confirmation-postgres`, commit `674a63a`.
`select_for_update(of=("self",))` блокирует только FoodScan; transaction и проверка уже созданного
Meal сохраняются. Добавлен regression test первого и повторного подтверждения, количества
Meal/MealItem и фактического PostgreSQL SQL locking clause. Тест прошёл на PostgreSQL.
Необходимость PostgreSQL/Redis job в CI (MVP-QA-013) остаётся отдельной MEDIUM-задачей.

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

## Выполненные проверки этапа 29

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

## Исходный список feature branches этапа 29

Ветки перечислены в порядке, предложенном аудитом. На этапе 29 они **не создавались**.
Фактические группы исправлений этапа 30 перечисляются отдельно; MEDIUM/LOW не входят в его scope.

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

## Исходный release gate этапа 29

До MVP release необходимо закрыть все BLOCKER, повторить полный backend/frontend quality gate и
добавить browser E2E для основного пользовательского сценария. HIGH findings по Celery/AI failure
handling должны быть закрыты до предоставления scan/AI функций внешним пользователям. Ограничения
Vision должны быть подтверждены продуктовым acceptance threshold на разрешённом validation dataset.
