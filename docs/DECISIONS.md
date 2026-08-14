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
