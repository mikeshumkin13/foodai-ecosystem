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

## ADR-0011: Privacy-Friendly Nutrition Profile Foundation

Date / Дата: 2026-08-12

Status / Статус: Accepted / принято

Decision / Решение:

MVP nutrition/health profile реализуется в `accounts.NutritionProfile`, отдельно от `accounts.User` и `accounts.UserProfile`.

`NutritionProfile` хранит только минимальные MVP-настройки:

- цель пользователя;
- рост;
- массу;
- age category вместо даты рождения или точного года рождения;
- activity level;
- preferred units;
- dietary preferences;
- consent/version metadata.

Аллергии, intolerance и медицинские ограничения считаются более чувствительными данными и вынесены в отдельную модель `accounts.NutritionSensitiveRestriction`. Модель хранит только тип ограничения, короткую user-provided label, active flag и consent/version metadata. Диагнозы не реализуются.

Business roles `support`, `content_manager` и `admin` не получают API-доступ к nutrition profile и sensitive restrictions по умолчанию. Обычный `user` получает только own permissions; `superuser` остаётся техническим override-механизмом Django.

Rationale / Обоснование:

- Nutrition profile нужен MVP для персонализации дневника питания и будущих расчётов.
- Точная дата рождения или год рождения не нужны MVP; age category снижает privacy risk.
- Аллергии и медицинские ограничения имеют повышенную чувствительность и должны быть логически отделены от обычных предпочтений питания.
- Consent/version fields нужны до production, чтобы future consent copy и schema changes можно было отслеживать без пересоздания модели.
- Support/content/admin доступ к health profile без отдельной процедуры противоречит least privilege.

Consequences / Последствия:

- Новые health/nutrition поля нельзя добавлять в `User` или generic `UserProfile`.
- Новые sensitive health/nutrition данные должны получать отдельную оценку модели, permissions, audit/logging и consent impact.
- API для nutrition profile должен покрываться owner-only и IDOR-тестами.
- AI и future recommendation logic должны получать только минимально необходимый nutrition контекст.
- Это не medical diagnosis model и не заменяет врача, лицензированного нутрициолога или психолога.

## ADR-0012: Extensible Nutrition Catalog Foundation

Date / Дата: 2026-08-12

Status / Статус: Accepted / принято

Decision / Решение:

Nutrition database MVP реализуется отдельным Django app `nutrition`.

Каталог состоит из:

- `FoodCategory` — справочник категорий;
- `FoodDataSource` — источник данных и source reference metadata;
- `Nutrient` — расширяемый справочник нутриентов с unit и nutrient type;
- `FoodItem` — canonical food item с names, synonyms, category, data source, density metadata, verified flag и source reference;
- `FoodNutrient` — значение конкретного nutrient для food item на 100 g.

`FoodItem` не хранит фиксированный набор calories/protein/fat/carbohydrate полей. Все nutrient values хранятся через `FoodNutrient.amount_per_100g`, поэтому micronutrients и future nutrients добавляются через справочник `Nutrient`, без миграции food item schema.

API чтения:

- `GET /api/v1/foods/search/`;
- `GET /api/v1/foods/{id}/`.

Authenticated users получают read-only доступ к nutrition catalog. Изменение catalog API требует centralized permission `accounts.manage_food_catalog`; `content_manager` и `admin` получают nutrition model permissions для Django Admin. `support` не получает write-доступ к catalog по умолчанию.

Rationale / Обоснование:

- Food recognition и meal diary должны опираться на единый managed catalog.
- Каталог должен поддерживать не только КБЖУ, но и micronutrients.
- Источник данных, verified flag и source reference нужны, чтобы отделять demo/manual/external values и не смешивать качество данных.
- Density metadata нужно для будущей оценки объёма/массы порций.
- `content_manager` должен управлять catalog data без доступа к приватным дневникам, фото, AI-диалогам и health profile.

Consequences / Последствия:

- Новые nutrients добавляются как `Nutrient` records, а не новыми колонками в `FoodItem`.
- Импорт внешних баз питания должен маппиться в `FoodDataSource`, `FoodItem`, `Nutrient`, `FoodNutrient`.
- Клиенты API должны читать динамический список nutrients и не предполагать фиксированный набор КБЖУ.
- Demo fixture не должен использоваться как production nutrition guidance.
- Любое расширение catalog write API должно сохранять permission boundary `accounts.manage_food_catalog`.

## ADR-0013: Historical Meal Nutrient Snapshots

Date / Дата: 2026-08-12

Status / Статус: Accepted / принято

Decision / Решение:

Дневник питания реализуется отдельным Django app `diary`.

`Meal` принадлежит конкретному `accounts.User` и хранит meal type, дату/время, пользовательское название и timestamps.

`MealItem` ссылается на canonical `nutrition.FoodItem`, но дополнительно хранит snapshot на момент добавления или ручной корректировки:

- название продукта;
- source reference;
- массу;
- calories/protein/fat/carbs;
- полный `nutrient_snapshot`;
- отдельный `micronutrient_snapshot`;
- source, confidence и `manually_corrected`.

Изменение `FoodItem`, `FoodNutrient` или справочника `Nutrient` в будущем не изменяет исторические дневниковые записи пользователя.

Diary API выдаёт обычному `user` только собственные meals и дневную агрегацию. `support`, `content_manager` и business `admin` не получают доступ к приватному дневнику по умолчанию. `superuser` остаётся техническим override-механизмом Django.

Rationale / Обоснование:

- Дневник является пользовательской историей и должен быть стабилен во времени.
- Каталог питания будет уточняться, импортироваться и исправляться; эти изменения не должны менять прошлые totals пользователя.
- Snapshot нужен для auditability, объяснимости расчётов и корректной дневной агрегации.
- Owner-only queryset и object-level permissions снижают IDOR риск при UUID lookup.

Consequences / Последствия:

- `MealItem` хранит намеренную денормализацию nutrient values.
- Исправление catalog values влияет только на новые или явно пересчитанные записи, если такая функция будет добавлена отдельным решением.
- Будущие Vision/AI flows должны записывать source/confidence и не подменять пользовательские ручные корректировки без подтверждения.
- Любое расширение diary API должно сохранять owner-only доступ и IDOR-тесты.

## ADR-0014: Secure Food Photo Upload With Private Storage Boundary

Date / Дата: 2026-08-12

Status / Статус: Accepted / принято

Decision / Решение:

Secure food photo upload реализуется отдельным Django app `food_scans` внутри модульного backend-монолита.

`FoodScan` принадлежит конкретному `accounts.User` и хранит только metadata приватного объекта:

- UUID scan;
- owner user;
- processing status;
- private storage backend name;
- private object key;
- фактический image format и normalized content type;
- uploaded/stored byte sizes;
- width/height;
- checksum;
- `exif_stripped`;
- timestamps.

API:

- `POST /api/v1/food-scans/`;
- `GET /api/v1/food-scans/`;
- `GET /api/v1/food-scans/{id}/`.

API не возвращает `object_key`, не доверяет имени файла пользователя и не выдаёт постоянный публичный URL. Доступ к metadata owner-only; `support`, `content_manager` и business `admin` не получают доступ к food photos по умолчанию.

Validation pipeline:

- читать upload поток с hard size limit;
- проверять фактический формат через Pillow;
- разрешать только whitelist `JPEG`/`PNG`;
- ограничивать pixel count;
- переэнкодировать изображение без EXIF/metadata;
- генерировать object key из UUID и валидировать его против path traversal;
- сохранять объект в private storage.

MVP storage backend — локальный private filesystem root. S3-compatible production storage должен реализовать тот же `PrivateObjectStorage` boundary и использовать private bucket; публичные bucket и постоянные public URLs запрещены.

Rationale / Обоснование:

- Фото еды являются чувствительными пользовательскими данными.
- Extension и `Content-Type` контролируются клиентом и не могут быть источником доверия.
- EXIF может содержать geolocation/device metadata и должен удаляться до сохранения.
- Отсутствие публичного URL снижает риск случайного раскрытия фотографии.
- Storage boundary позволяет заменить локальный filesystem на MinIO/S3-compatible storage без изменения доменной модели и API.

Consequences / Последствия:

- Future Vision service должен получать только минимально необходимый private object reference через backend-controlled flow.
- Signed URL можно добавить только отдельным решением с коротким TTL, owner checks и audit/logging policy.
- Локальные файлы в `FOOD_SCAN_PRIVATE_MEDIA_ROOT` считаются private runtime artifacts и не коммитятся.
- Новые upload formats требуют отдельной оценки security/risk и тестов на фактический формат.

## ADR-0015: FastAPI Vision Service Foundation And Backend Client Boundary

Date / Дата: 2026-08-12

Status / Статус: Accepted / принято

Decision / Решение:

Vision foundation реализуется отдельным FastAPI service в `services/vision`.

MVP contract:

- `GET /health`;
- `POST /v1/analyze`;
- request содержит internal `object_reference` на уже безопасно подготовленный backend food scan object: `scan_id`, `storage_backend`, `object_key`, `content_type`, `checksum_sha256`;
- response содержит список detected items с `label` и `confidence`;
- до подключения ML-модели сервис возвращает mock result `rice` с confidence `0.92`.

Backend не размещает HTTP-вызовы к Vision в Django views. Все вызовы идут через `integrations.vision.client`, а доменный adapter для `FoodScan` живёт в `food_scans.vision`.

Client behavior:

- один HTTP request на анализ;
- timeout задаётся через `VISION_SERVICE_TIMEOUT_SECONDS`;
- automatic retries не выполняются;
- unavailable, timeout и invalid response маппятся в отдельные exception-классы.

Rationale / Обоснование:

- Vision имеет отдельные CV/ML зависимости и resource profile, поэтому остаётся отдельным сервисом.
- Backend должен владеть users, permissions, private storage metadata и orchestration, а Vision должен получать минимальный внутренний reference.
- Отдельный client boundary упрощает тестирование контракта, обработку деградации Vision и будущую замену transport/auth без переписывания views.
- Отсутствие retries на foundation-этапе снижает риск retry storm.

Consequences / Последствия:

- Future Vision integration в food scan processing должна использовать `food_scans.vision` или аналогичный service layer, а не прямой `httpx` в views/tasks.
- Добавление signed URL, service-to-service auth или прямой передачи image bytes требует отдельной оценки security и обновления контракта.
- Future ML model подключается внутри `services/vision` без передачи долгосрочных пользовательских данных в Vision.
- Contract tests должны обновляться вместе с изменением request/response schema.

## ADR-0016: User-Confirmed Food Scan Orchestration

Date / Дата: 2026-08-14

Status / Статус: Accepted / принято

Decision / Решение:

Первый end-to-end scan flow реализуется внутри backend-монолита в `food_scans.orchestration`.

MVP status flow:

- `uploaded`;
- `processing`;
- `needs_confirmation`;
- `confirmed`;
- `failed`.

После загрузки фотографии backend синхронно инициирует один Vision-анализ через существующий
`food_scans.vision` / `integrations.vision.client` boundary. Celery orchestration будет добавлена
отдельно, когда появится реальная очередь обработки и требования к latency.

Update / Обновление 2026-08-14: синхронный запуск Vision из request flow заменён на Celery
background processing в ADR-0017. Confirmation boundary, proposal snapshots и idempotent
confirmation остаются без изменений.

Vision result сохраняется как набор `FoodScanDetectedItem` proposal-записей:

- исходный `label` и `confidence`;
- matched `nutrition.FoodItem`, если deterministic catalog matching нашёл продукт;
- пользовательская или MVP-оценочная масса;
- snapshot calories/protein/fat/carbs, всех nutrients и micronutrients для этой массы;
- источник `vision` или `manual`;
- флаг `manually_corrected`;
- soft-delete флаг `is_removed`.

Matching на этом этапе детерминированный и простой: exact match по `name`, `name_ru`, `name_en`,
`synonyms`, затем contains fallback. ML-ranking, fuzzy search и portion estimation не добавляются
без отдельного решения.

Результат scan не попадает в дневник автоматически. Пользователь должен явно подтвердить результат,
предварительно имея возможность исправить продукт, массу, удалить ошибочный item или добавить
отсутствующий item. Только `POST /api/v1/food-scans/{id}/confirm/` создаёт `Meal` и `MealItem`.

При подтверждении `MealItem` получает копию proposal snapshot из `FoodScanDetectedItem`, а не
пересчитывается из текущего состояния глобального catalog. Это делает расчёты воспроизводимыми даже
если `FoodItem`/`FoodNutrient` изменились между анализом и подтверждением.

Ошибки Vision нормализуются в `FoodScan.status=failed` и `failure_code`
(`vision_unavailable`, `vision_timeout`, `vision_invalid_response`) без раскрытия private object key
или содержимого фотографии.

Rationale / Обоснование:

- Основной пользовательский сценарий требует сквозной связи фото → Vision → catalog → diary.
- AI/Vision не должен самостоятельно записывать данные в дневник без подтверждения пользователя.
- Proposal snapshot нужен, чтобы пользователь подтверждал конкретные расчёты, а не подвижное
  состояние catalog.
- Синхронная MVP-оркестрация проще для первого end-to-end flow и не создаёт преждевременную
  Celery-сложность.
- Owner-only access и существующие food scan permissions сохраняют IDOR boundary для фото и
  производных detected items.

Consequences / Последствия:

- Future async processing должен сохранить те же статусы и confirmation boundary.
- Изменение matching algorithm или добавление portion estimation должно обновить contract tests и
  документацию.
- Proposal detected items считаются производными чувствительными данными пользователя и не должны
  попадать в публичные URL, логи или support/content-manager доступ по умолчанию.
- Confirm endpoint должен оставаться идемпотентным для уже подтверждённого scan и не создавать
  дубликаты meals.

## ADR-0017: Celery Background Processing For Food Scan Analysis

Date / Дата: 2026-08-14

Status / Статус: Accepted / принято

Decision / Решение:

Food scan Vision processing переносится из синхронного request flow в Celery background task внутри
существующего backend-монолита.

Используем:

- Celery app `config.celery`;
- Redis как broker и result backend;
- Docker Compose service `celery_worker`;
- task `food_scans.process_food_scan_analysis`;
- внутренние поля `FoodScan.analysis_run_id`, `analysis_task_id`, `analysis_attempt_count`.

`POST /api/v1/food-scans/` после secure upload быстро возвращает только `scan_id` и текущий `status`.
Клиент получает статус и proposal results через polling `GET /api/v1/food-scans/{id}/results/`.

Controlled retry выполняется только для transient Vision failures:

- `vision_unavailable`;
- `vision_timeout`.

`vision_invalid_response` и unexpected task failures переводят scan в `failed` без бесконтрольных
повторов. Количество retry ограничено `FOOD_SCAN_ANALYSIS_MAX_RETRIES`, backoff задаётся через
`FOOD_SCAN_ANALYSIS_RETRY_BACKOFF_SECONDS`, task time limit задаётся через Celery settings.

Idempotency:

- task payload содержит только `food_scan_id` и `analysis_run_id`;
- stale task не записывает results, если пользователь уже запустил более новый analysis run;
- confirmed scan не переобрабатывается;
- processing scan не ставится в очередь повторно;
- подтверждение scan остаётся единственным местом создания `Meal`/`MealItem` и уже идемпотентно
  возвращает существующий meal для confirmed scan.

Rationale / Обоснование:

- Vision processing может быть медленным и не должен держать HTTP request открытым.
- Redis уже является частью backend infrastructure, поэтому Celery добавляет очередь без нового
  микросервиса.
- Run id нужен, чтобы user retry не конфликтовал со старой задачей или delayed retry.
- Bounded retry снижает вероятность retry storm при деградации Vision.
- Task payload не должен содержать фото, private object key, health profile, дневник или nutrient
  snapshots.

Consequences / Последствия:

- Локальный `make dev-up` запускает дополнительный worker container.
- Production deployment должен запускать минимум один Celery worker рядом с backend и Redis.
- API clients должны после upload polling-ом ждать `needs_confirmation` или `failed`.
- Future queue routing, task observability, dead-letter policy и signed object access требуют
  отдельного решения перед production.
- Любые новые background tasks должны сохранять правило: в task payload только минимальные IDs, без
  чувствительного содержимого.

## ADR-0018: Vision Food Recognition Model V1

Date / Дата: 2026-08-14

Status / Статус: Accepted / принято

Decision / Решение:

Первой реальной моделью распознавания еды в `services/vision` выбирается Hugging Face model:

- model: `nateraw/food`;
- pinned revision / версия snapshot: `ddbd0f9ed493f03fc6a45527e5e52904161d3e09`;
- source / источник: Hugging Face model hub, `https://huggingface.co/nateraw/food`;
- base model: `google/vit-base-patch16-224-in21k`;
- task: dish-level image classification по Food-101 labels;
- license / лицензия модели: Apache-2.0 согласно model card;
- runtime libraries: `transformers`, CPU-only `torch==2.6.0`, `Pillow`;
- benchmark entrypoint: `services/vision/scripts/benchmark_food_model.py`.

Vision `POST /v1/analyze` больше не возвращает hardcoded mock. Сервис читает backend-controlled
prepared image из private local storage reference, проверяет SHA-256 checksum и передаёт изображение
в pluggable inference adapter `FoodRecognitionModel`. По умолчанию возвращается один top prediction
с `label` и `confidence`, потому что текущий backend трактует `items` как detected/proposal items, а
не как альтернативные class candidates.

Low confidence не приводит к автоматическому созданию diary records. В текущей архитектуре любой
результат Vision, включая low-confidence, переводит `FoodScan` только в `needs_confirmation`.
Пользователь должен подтвердить, исправить или удалить detected items перед созданием `MealItem`.

Known limitations / Ограничения:

- Это classifier, а не object detector: модель не возвращает bounding boxes и не умеет надёжно
  выделять несколько блюд/ингредиентов на одном фото.
- Модель не оценивает массу, объём или порцию.
- Классы ограничены Food-101; локальные блюда, смешанные тарелки, напитки, упаковки и редкие продукты
  могут распознаваться неверно.
- Accuracy из model card является self-reported evaluation на Food-101 и не является обещанием
  production-точности FoodAI.
- Hugging Face dataset card `ethz/food101` указывает `license: unknown`; перед production/legal
  launch нужна отдельная юридическая проверка допустимости использования модели и training data
  provenance.
- Выбранный revision содержит `model.safetensors`; Vision adapter форсирует `use_safetensors=True`
  и не должен загружать pickle weights. Supply-chain и artifact integrity review всё равно нужны
  перед production.

Rationale / Обоснование:

- У модели есть понятная permissive model license Apache-2.0, в отличие от вариантов с AGPL или
  неясной model license.
- Модель уже специализирована на food image classification и совместима со стандартным
  `transformers` inference.
- Snapshot revision фиксирует воспроизводимость разработки и Docker build; выбран revision с
  `model.safetensors`, чтобы не использовать pickle-based `torch.load` для weights.
- Dish-level classifier достаточен как v1 для подтверждаемого пользователем MVP, потому что результат
  не попадает в дневник автоматически.
- Adapter boundary позволяет позже заменить classifier на detector/segmentation model без переноса
  HTTP-вызовов в Django views и без изменения ownership модели данных backend.

Consequences / Последствия:

- Docker build Vision service скачивает дополнительные ML-зависимости и становится тяжелее.
- Первый request к Vision может быть медленнее из-за lazy model loading; production позже должен
  решить warmup/cache strategy.
- Backend matching остаётся deterministic catalog matching по labels/synonyms и не становится частью
  ML inference.
- Любая замена модели, изменение количества returned items или переход к bounding boxes требует
  обновления `docs/DECISIONS.md`, contract tests и UX подтверждения.

## ADR-0019: Portion Estimation V1 As Explicit Estimator

Date / Дата: 2026-08-14

Status / Статус: Accepted / принято

Decision / Решение:

Portion estimation v1 реализуется как честный estimator, а не как точное измерение массы по одному
RGB-фото.

Оценка выполняется внутри backend `food_scans.portion_estimation` при создании proposal
`FoodScanDetectedItem`. Vision contract расширяется опциональными полями:

- `segment_area_px`;
- `portion_reference.reference_type`;
- `portion_reference.diameter_cm`;
- `portion_reference.area_px`.

Текущая Vision model v1 не возвращает segmentation mask или reference detection, поэтому эти поля
обычно отсутствуют. При их отсутствии backend использует низкоконфидентный fallback:
`food_type_typical_volume_density_table_v1`.

Если доступны segment area и известный физический reference, используется метод:
`segment_area_plate_reference_geometry_v1`.

Формулы MVP:

- площадь reference в `cm²`: `pi * (diameter_cm / 2)^2`;
- площадь сегмента в `cm²`: `reference_area_cm² * segment_area_px / reference_area_px`;
- объём в `ml`: `segment_area_cm² * assumed_depth_cm`;
- масса в `g`: `estimated_volume_ml * density_g_per_ml`.

Density resolution:

1. `FoodItem.density_g_per_ml`, если заполнено;
2. `FoodItem.density_metadata["density_g_per_ml"]`, если есть;
3. MVP density table по типу продукта/category/label.

Food type assumptions включают только грубые MVP-классы: grains, protein foods, fruits,
vegetables, bread/flat foods, liquids и generic mixed food. Для каждого типа задаются
`density_g_per_ml`, `typical_volume_ml` и `assumed_depth_cm`.

`FoodScanDetectedItem` хранит отдельно:

- активную массу для snapshot/confirmation: `estimated_mass_g`;
- исходную portion estimate mass: `portion_estimated_mass_g`;
- estimated volume: `portion_estimated_volume_ml`;
- uncertainty interval: `portion_min_mass_g`, `portion_max_mass_g`;
- portion confidence: `portion_confidence`;
- method: `portion_estimation_method`;
- metadata assumptions: `portion_estimation_metadata`;
- ручную пользовательскую коррекцию массы: `manual_mass_g`.

Когда пользователь исправляет `mass_g`, backend сохраняет новую активную массу в
`estimated_mass_g`, а ручную массу отдельно в `manual_mass_g`. Исходная оценка порции остаётся
неизменной, чтобы в будущем можно было сравнивать estimate и user correction для улучшения модели.

API scan results возвращает активную `mass_g`, optional `manual_mass_g` и nested
`portion_estimate`:

- `estimated_volume`;
- `estimated_mass`;
- `confidence`;
- `min_estimate`;
- `max_estimate`;
- `method`.

Known limitations / Ограничения:

- Один RGB-снимок без depth sensor, calibration и физического reference не даёт точной массы.
- Geometry v1 использует грубую assumed depth по типу продукта и не учитывает высоту горки,
  скрытые ингредиенты, многослойные блюда, перспективу и частичное перекрытие объектов.
- Без segment/reference используется typical volume fallback с низкой confidence.
- Min/max interval является инженерной оценкой неопределённости, а не статистически
  валидированным доверительным интервалом.
- Оценка порции не должна использоваться как медицинское или диетологическое назначение.
- Пользователь всегда должен иметь возможность исправить массу вручную до подтверждения дневника.

Rationale / Обоснование:

- MVP должен двигаться к end-to-end value, но не должен обещать точность, которой нет.
- Хранение initial estimate и manual correction отдельно создаёт foundation для будущего
  model-improvement dataset без логирования фотографий или раскрытия приватных данных.
- Backend владеет Nutrition Catalog и snapshots, поэтому оценка массы и nutrient recalculation
  остаются рядом с `FoodScanDetectedItem` и confirmation boundary.
- Опциональные geometry поля в Vision contract позволяют позже подключить segmentation/reference
  detection без breaking API change.

Consequences / Последствия:

- `FoodScanDetectedItem.estimated_mass_g` остаётся active mass для текущего proposal, а не только
  raw ML output; клиенты должны читать `portion_estimate`, чтобы показать исходную оценку.
- Confirmation продолжает копировать active mass и nutrient snapshot в `MealItem`; ручная коррекция
  массы помечает item как `manually_corrected`.
- Любое изменение формул, density table, food type assumptions или формата geometry data требует
  обновления ADR/API docs и formula tests.
- Перед production нужны validation dataset, calibration UX и отдельная оценка ошибок по food type.

## ADR-0020: Nutrition Calculation Engine And Internal Units

Date / Дата: 2026-08-17

Status / Статус: Accepted / принято

Decision / Решение:

Nutrition calculation для MVP выносится в backend domain service `nutrition.calculation`.

Сервис принимает canonical `nutrition.FoodItem` и массу `mass_g` в граммах. Он возвращает:

- `kcal`;
- `protein_g`;
- `fat_g`;
- `carbohydrates_g`;
- все доступные `nutrients`;
- доступные `micronutrients`.

Единая внутренняя система единиц backend:

- масса: grams (`g`);
- значения food catalog: amount per `100 g`;
- energy: kilocalories (`kcal`) через nutrient code `energy_kcal`;
- protein/fat/carbohydrate: grams (`g`) через nutrient codes `protein`, `fat`, `carbohydrate`;
- micronutrients: catalog-native units из `Nutrient.unit`, например `mg`, `mcg`, `g`.

Расчёты выполняются через `Decimal` и quantize до `0.0001` для nutrient amounts. Отрицательная масса
недопустима и приводит к `mass_g_must_be_non_negative`. Масса `0 g` допустима для domain service и
возвращает нулевые значения, хотя публичные meal/write serializers могут сохранять более строгий
минимум для пользовательских записей.

`diary.snapshots.build_food_snapshot` остаётся совместимым фасадом, но делегирует расчёт в
`nutrition.calculation`. `diary` и `food_scans` не должны дублировать формулы расчёта nutrients.

Scan flow:

- proposal `FoodScanDetectedItem` создаёт nutrient snapshot через `nutrition.calculation`;
- manual mass correction пересчитывает proposal snapshot через тот же engine;
- confirmation копирует уже сохранённый proposal snapshot в `MealItem`, сохраняя историческую
  воспроизводимость.

Rationale / Обоснование:

- Nutrition catalog владеет `FoodItem`, `Nutrient` и `FoodNutrient`, поэтому расчёт по per-100g
  значениям должен жить рядом с каталогом, а не в API views или scan orchestration.
- Один engine снижает риск расхождения между ручным diary flow, Vision scan flow и будущими imports.
- Decimal нужен для стабильных финансово-похожих вычислений нутриентов, где float rounding создаёт
  непредсказуемые API snapshots.
- Единые internal units нужны до появления frontend, HealthKit/Health Connect и B2B API, чтобы не
  смешивать grams, ounces, servings и provider-specific micronutrient units.

Consequences / Последствия:

- Новые flows, которые создают `MealItem` или proposal nutrient snapshot, должны использовать
  `nutrition.calculation`.
- Если появятся serving units, imperial units или provider-specific nutrient mappings, они должны
  конвертироваться в internal grams/per-100g до вызова calculation engine.
- Изменение rounding, nutrient code mapping или internal units требует обновления ADR/API docs и
  unit tests формул.
- Historical `MealItem` snapshots остаются source of truth для дневника; клиенты не должны
  пересчитывать историю из текущего catalog state.

## ADR-0021: Next.js Frontend Foundation With Session Cookie API Client

Date / Дата: 2026-08-17

Status / Статус: Accepted / принято

Decision / Решение:

Frontend foundation реализуется в `frontend` как Next.js App Router + TypeScript приложение.

MVP frontend строится как responsive PWA-ready web client:

- маршруты `/login`, `/register`, `/dashboard`, `/diary`, `/scan`, `/profile`;
- manifest/icon/service worker registration для production PWA foundation;
- responsive shell с desktop sidebar и mobile bottom navigation;
- централизованный API client в `frontend/src/lib/api`;
- централизованная обработка API ошибок;
- локализационный словарь `ru`/`en` в `frontend/src/lib/i18n/messages.ts`;
- базовые UI components без бизнес-логики API;
- loading и empty states на MVP-экранах.

Auth/API схема frontend следует ADR-0009:

- web-клиент не хранит access token в `localStorage` или `sessionStorage`;
- API requests выполняются с `credentials: "include"`;
- unsafe requests получают CSRF через `GET /api/v1/auth/csrf/`;
- CSRF отправляется в `X-CSRFToken`.

Frontend quality gate использует:

- project frontend linter для security/architecture rules;
- TypeScript `tsc --noEmit`;
- Vitest unit tests;
- `next build`.

Rationale / Обоснование:

- Backend уже выбрал session-cookie authentication, поэтому frontend должен быть спроектирован вокруг cookie/CSRF, а не browser token storage.
- Централизованный API client снижает риск расхождения CSRF, credentials и error handling между страницами.
- PWA-ready foundation нужен до scan/camera UX, но полноценные offline flows и push notifications не добавляются преждевременно.
- UI components без API-логики упрощают тестирование и дальнейшую реализацию scan/diary flows.
- Локализация ru/en учитывается до появления большого объёма пользовательских строк.

Consequences / Последствия:

- Новые frontend API calls должны добавляться через `frontend/src/lib/api`, а не прямой `fetch` в UI components.
- Нельзя добавлять access token storage в `localStorage`/`sessionStorage` без нового security ADR.
- Scan UI и diary UI должны переиспользовать существующий shell, loading/empty states и centralized error handling.
- При добавлении полноценного camera/offline UX нужно отдельно проверить browser permissions, privacy copy, fallback states и PWA caching policy.

## ADR-0022: Dashboard And Manual Diary Fallback Before Goals

Date / Дата: 2026-08-19

Status / Статус: Accepted / принято

Decision / Решение:

Dashboard MVP использует уже существующие данные дневника и nutrition profile, не вводя отдельную
goals-модель раньше времени.

- `calories consumed`, protein, fat, carbohydrates и `meals today` берутся из
  `GET /api/v1/diary/day/?date=YYYY-MM-DD`.
- `calorie target` на этом этапе является осторожным ориентиром frontend, рассчитанным из
  `NutritionProfile.mass_kg`, `activity_level` и `goal`.
- Если данных профиля недостаточно или `age_category=under_18`, target не рассчитывается и UI
  показывает отсутствие ориентира.
- Для чтения текущего nutrition profile добавлен additive endpoint
  `GET /api/v1/accounts/nutrition-profiles/me/`.
- Diary UI должен поддерживать ручное создание, редактирование и удаление meals через existing
  Meals API, чтобы продукт оставался usable даже при недоступном AI Scan.

Rationale / Обоснование:

- Stage 20 требует dashboard target, но полноценные goals/calorie planning модели ещё не введены.
- Раннее добавление отдельной goals-доменной модели увеличило бы scope и privacy-поверхность без
  явного требования текущего этапа.
- Manual diary fallback является продуктовой отказоустойчивостью: пользователь не должен зависеть
  от Vision/Celery/AI для базового ведения питания.
- Additive `nutrition-profiles/me/` упрощает frontend и не раскрывает чужие profile UUID, потому что
  endpoint использует owner-only queryset и existing nutrition profile permissions.

Consequences / Последствия:

- Dashboard target нельзя трактовать как медицинское или диетологическое назначение.
- Будущий этап goals должен заменить frontend-estimated calorie target на user-owned goals API.
- При появлении точных целей, gender/sex fields, clinical restrictions или coach logic потребуется
  отдельное privacy/safety решение.
- Ручное создание `MealItem` продолжает использовать backend `nutrition.calculation` через Meals API,
  поэтому historical nutrient snapshots остаются воспроизводимыми.

## ADR-0023: AI Nutrition Coach Provider Boundary And Safety Layer

Date / Дата: 2026-08-19

Status / Статус: Accepted / принято

Decision / Решение:

AI Nutrition Coach foundation реализуется внутри backend-монолита отдельным Django app `ai_coach`.
Бизнес-логика не вызывает конкретный LLM напрямую и работает через provider abstraction
`ai_coach.providers.AICoachProvider`.

Текущий provider по умолчанию: `mock`. Он нужен для development/tests и не является обещанием
production-качества AI-ответов. Подключение конкретного внешнего LLM-провайдера, ключей, retention
policy и provider-specific safety требует отдельного решения.

AI coach получает только структурированный минимальный context:

- цель пользователя из `NutritionProfile.goal`;
- дневные агрегаты из `MealItem` snapshots за выбранную дату;
- разрешённые dietary preferences;
- текущий запрос пользователя;
- locale `ru`/`en` для ответа.

Context не включает email, display name, UUID пользователя, фотографии, private object keys,
sensitive restrictions, полную историю аккаунта или историю AI-чата.

Output schema фиксируется как `ai_nutrition_coach_response_v1`:

- `answer`;
- `suggestions`;
- `nutrition_notes`;
- `warnings`;
- `safety`;
- `provider`;
- `stored`.

Safety layer выполняется до и после provider call. Он блокирует запросы и ответы, связанные с:

- диагнозами;
- назначением или отменой лекарств;
- заменой врача, лицензированного нутрициолога или психолога;
- dangerous/extreme diet рекомендациями.

AI response/history хранится в `AICoachMessage` только если пользователь явно дал consent на историю
AI-чата через `AICoachSettings`. Unsafe user requests и unsafe provider outputs не сохраняются даже
при наличии consent. `AICoachMessage` не регистрируется в Django Admin на этом этапе.

Rationale / Обоснование:

- AI coach нужен как отдельная product capability, но LLM-провайдер может меняться по стоимости,
  качеству, privacy и legal причинам.
- Минимальный context снижает privacy risk и соответствует принципу data minimization.
- Diary aggregates достаточно для MVP-объяснения дневного баланса; полная история дневника и фото
  не нужны для одного ответа.
- Consent-only storage нужен, потому что AI-диалоги являются чувствительными пользовательскими
  данными.
- Rule-based safety foundation не заменяет production moderation, но задаёт явную границу для
  запрета medical и extreme diet сценариев уже в MVP.

Consequences / Последствия:

- Новые AI-сценарии должны использовать provider abstraction и explicit context builder, а не
  напрямую собирать данные пользователя во views.
- Подключение OpenAI, Anthropic, локальной модели или другого LLM требует отдельного ADR с
  retention, logging, timeout, cost-control и legal/safety оценкой.
- Future AI history UI/API должен читать только собственные сообщения пользователя и иметь
  отдельные IDOR tests.
- Support, content_manager и business admin не получают доступ к AI-диалогам по умолчанию.
- Любое расширение context должно проходить privacy review и обновлять `docs/SECURITY.md` /
  `docs/API.md`.
