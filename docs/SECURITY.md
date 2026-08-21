# Security / Безопасность

FoodAI Ecosystem строится по принципам privacy-by-design и security-by-design.

## Принципы

- Least privilege.
- Deny by default.
- Минимизация собираемых данных.
- UUID вместо последовательных публичных ID там, где это оправдано.
- Секреты только через environment variables.
- `.env` никогда не коммитить.
- Пароли не хранить самостоятельно; использовать безопасный password hashing Django.
- CSRF protection.
- Строгий CORS allowlist.
- Rate limiting.
- Object-level permissions.
- Защита от IDOR.
- Audit log административных операций.
- Фотографии пользователей приватны по умолчанию.

## Чувствительные данные

К чувствительным данным относятся:

- фотографии еды;
- дневник питания;
- health profile;
- nutrition profile;
- allergies, intolerances и medical nutrition restrictions;
- AI-диалоги;
- токены;
- пароли;
- support access logs;
- export files.

Логи не должны содержать пароли, токены, health profile, фотографии и другую чувствительную информацию. Токены и секреты должны редактироваться из логов.

## Account security

- Backend использует custom `accounts.User` с UUID primary key.
- Email является основным логином и хранится уникально.
- Пароли не хранятся в plaintext; используется стандартный Django password hashing.
- `User` хранит только authentication/authorization минимум: email, password hash, active/staff flags и timestamps.
- `UserProfile` отделён от `User` для пользовательских данных, но health/fitness данные не должны храниться ни в `User`, ни в generic profile без отдельного архитектурного решения.
- MVP nutrition settings хранятся отдельно в `NutritionProfile`; allergies/intolerances/medical nutrition restrictions отделены в `NutritionSensitiveRestriction`.
- Все будущие модели, связанные с пользователем, должны ссылаться на `settings.AUTH_USER_MODEL`.

## Nutrition profile privacy

- `NutritionProfile` хранит только MVP-данные: goal, height, mass, age category, activity level, preferred units и dietary preferences.
- Точная дата рождения и год рождения не хранятся; используется privacy-friendly `age_category`.
- Изменение nutrition profile требует consent/version foundation через `consent_accepted`, `consent_version` и `consent_granted_at`.
- Allergies, intolerances и medical nutrition restrictions отделены в `NutritionSensitiveRestriction`.
- `NutritionSensitiveRestriction` не хранит диагнозы и не является medical decision model.
- `support`, `content_manager` и business `admin` не получают API-доступ к nutrition profile и sensitive restrictions по умолчанию.
- Django Admin не регистрирует `NutritionProfile` и `NutritionSensitiveRestriction` на этом этапе.

## Nutrition catalog access

- Nutrition catalog считается managed reference/content data, а не приватными пользовательскими данными.
- Read API доступен authenticated users.
- Изменение catalog API требует `accounts.manage_food_catalog`; эта permission выдаётся `content_manager` и `admin`.
- Django Admin для `nutrition` моделей доступен staff users только при наличии соответствующих model permissions.
- `support` не получает catalog write permissions по умолчанию.
- Каталог хранит values per 100 g через расширяемые `Nutrient`/`FoodNutrient`, включая future micronutrients.

## Diary privacy

- Дневник питания считается чувствительными пользовательскими данными.
- `Meal` всегда принадлежит конкретному `accounts.User`.
- Diary API фильтрует queryset по владельцу до object lookup, поэтому знание UUID чужого `Meal` не раскрывает запись.
- `MealItem` хранит snapshot nutrients на момент добавления, чтобы future изменения global food catalog не переписывали историю пользователя.
- `support`, `content_manager` и business `admin` не получают API-доступ к приватным meals и дневной агрегации по умолчанию.
- Логи не должны содержать состав дневника, nutrient snapshots или пользовательские корректировки без отдельной безопасной процедуры.

## Authentication security

Web authentication использует Django session cookies:

- access token не выдаётся web-клиенту и не хранится в `localStorage`;
- `sessionid` хранится в `HttpOnly` cookie;
- `SameSite=Lax` по умолчанию;
- `Secure` должен быть включён в production;
- unsafe requests требуют CSRF token/header;
- refresh endpoint продлевает session и ротирует session key/CSRF token;
- logout очищает session;
- password change использует `update_session_auth_hash` для текущей session.

Frontend foundation следует этой схеме:

- не хранит access token или session material в `localStorage`/`sessionStorage`;
- использует централизованный API client с `credentials: "include"`;
- перед unsafe requests вызывает `GET /api/v1/auth/csrf/`;
- отправляет CSRF token в заголовке `X-CSRFToken`;
- держит обработку API ошибок централизованной и не выводит чувствительные payloads в UI.

Email verification и password reset:

- raw tokens не хранятся в БД;
- хранится только hash token;
- tokens одноразовые и имеют expiry;
- выпуск нового token отзывает старые unused tokens;
- password reset request всегда возвращает generic response для existing и unknown email;
- OAuth не реализован на этом этапе.

Brute-force/rate limiting:

- registration, login, logout, refresh, email verification, password reset и password change имеют scoped throttling;
- login/password reset throttling учитывает IP и нормализованный email hash;
- production multi-instance deployment должен перевести throttle cache на shared backend, например Redis.

## Upload security

Загрузка фотографий должна включать:

- authentication;
- object-level authorization;
- ограничение размера файлов;
- проверку MIME;
- проверку фактического формата файла;
- удаление EXIF/geolocation;
- приватное object storage;
- signed URL только при необходимости.

Текущее secure food photo upload поведение:

- `FoodScan` всегда принадлежит конкретному `accounts.User`.
- API принимает только authenticated requests.
- Разрешённые фактические форматы задаются whitelist `FOOD_SCAN_ALLOWED_FORMATS`, по умолчанию `JPEG,PNG`.
- Фактический формат проверяется через Pillow, а не через extension или `Content-Type`.
- Upload size ограничивается `FOOD_SCAN_MAX_UPLOAD_BYTES`; image dimensions ограничиваются `FOOD_SCAN_MAX_IMAGE_PIXELS`.
- Пользовательское имя файла не используется для storage key.
- Object key генерируется из UUID и валидируется против path traversal.
- Перед сохранением изображение переэнкодируется без EXIF/metadata.
- Локальный MVP storage — private filesystem root `FOOD_SCAN_PRIVATE_MEDIA_ROOT`.
- API не возвращает private `object_key` и не выдаёт постоянный публичный URL.
- S3-compatible production storage должен оставаться private bucket и подключаться через storage boundary без публичных bucket.

## Vision service security

- Vision service является internal service и не владеет пользователями, дневниками или долгосрочными пользовательскими данными.
- Backend передаёт только минимальную internal object reference на уже подготовленный private food scan объект.
- Vision API не должен получать весь user profile, health profile, дневник или AI-историю.
- Docker Compose не публикует Vision port на host по умолчанию; backend обращается к `vision` внутри compose network.
- Backend client использует короткий timeout и не делает automatic retries, чтобы не создавать retry storm при деградации Vision.
- Ошибки Vision нормализуются без включения object key, фото или пользовательских health/nutrition данных в логи/ответы.
- Vision model v1 (`nateraw/food`) выполняет dish-level classification внутри Vision service и возвращает только label/confidence. Низкий confidence не может создать `MealItem` автоматически: backend сохраняет только proposal results и требует явного подтверждения пользователя.
- Перед production требуется отдельная legal/supply-chain проверка выбранной модели, weights artifact и training data provenance; Food-101 dataset metadata указывает unknown license.

## Scan orchestration security

- `FoodScanDetectedItem` считается производной чувствительной информацией пользователя: label, confidence, matched food, portion estimate, ручная коррекция массы и nutrient snapshots не должны попадать в публичные URL, support/content-manager доступ или логи по умолчанию.
- Scan orchestration использует тот же owner-only queryset и `food_scans.view_own_foodscan` / `food_scans.change_own_foodscan` permissions, что и secure upload.
- Знание UUID чужого `FoodScan` или `FoodScanDetectedItem` не должно раскрывать results, correction actions или confirmation flow.
- Vision result никогда не записывается в дневник автоматически. Только явное подтверждение владельца scan создаёт `Meal` и `MealItem`.
- Confirmation копирует сохранённый proposal nutrient snapshot в `MealItem`, поэтому подтверждённая история не зависит от будущих изменений global nutrition catalog.
- Vision failures сохраняются как стабильный `failure_code` без private object key, имени файла пользователя, фото bytes или health/nutrition profile.
- Portion estimation v1 не является точным измерением массы по RGB-фото; API должен показывать estimate/confidence/min/max/method и сохранять user-corrected `manual_mass_g` отдельно от initial estimate.
- Portion estimate metadata хранит только инженерные assumptions и не должна включать фото, object key, health profile или приватный дневник.

## Background processing security

- Food scan background tasks используют Celery + Redis и получают только `food_scan_id` и `analysis_run_id`.
- Фото bytes, private `object_key`, nutrient snapshots, health profile и пользовательский дневник не передаются в Celery task payload и не логируются.
- `analysis_run_id` защищает от stale task overwrite: результат старого запуска не должен перезаписывать более новый пользовательский retry.
- Controlled retry включён только для transient Vision failures `vision_unavailable` и `vision_timeout`; `vision_invalid_response` завершает scan как failed без retry storm.
- Повторный запуск пользователем запрещён для confirmed scan и не создаёт дубликаты `MealItem`, потому что запись в дневник остаётся только в идемпотентном confirmation endpoint.

## Dev infrastructure security

- Docker Compose не содержит секретов напрямую, а читает значения из `.env`.
- `.env.example` содержит только безопасные локальные примеры и не должен использоваться как production-конфигурация.
- PostgreSQL и Redis в локальной инфраструктуре не публикуют порты на host без отдельной необходимости.
- Backend публикует только HTTP-порт разработки.
- Redis включён с паролем даже в локальной инфраструктуре.
- Celery worker использует Redis внутри Docker Compose network, не публикует отдельные host-порты и не выполняет migrations параллельно с backend.

## Admin security

- Django Admin доступен только active staff users через стандартную Django admin authentication.
- В admin зарегистрированы текущие операционные модели: `accounts.User`, `accounts.UserProfile`, Django `Group` для role groups, read-only `accounts.AdminAuditLog` и managed reference/content models приложения `nutrition`.
- `EmailVerificationToken` и `PasswordResetToken` не зарегистрированы в admin, чтобы не расширять поверхность доступа к token metadata.
- `User` list view показывает email как login identifier, flags, roles и timestamps; password hash не выводится в списках.
- `UserProfile` list view показывает UUID пользователя и language/timestamps; display name не выводится в списке.
- Bulk actions отключены для зарегистрированных admin-моделей; опасные массовые действия не добавляются.
- `AdminAuditLog` доступен только на чтение, зеркалирует стандартный `django_admin_log` и хранит минимальные metadata: actor, action, model label, object id, sanitized object representation, change message и timestamps.
- Account object representations в audit log редактируются до `app.model:object_id`, чтобы не переносить email/profile/token-строки без необходимости.
- `support` и `content_manager` могут войти в admin только при явном `is_staff=True`, но не видят чувствительные account/audit/role models без model permissions.
- `content_manager` видит и изменяет `nutrition` catalog models в admin через nutrition model permissions.

## Роли и доступ

- `anonymous`: нет доступа к приватным данным.
- `user`: доступ только к собственным данным.
- `support`: по умолчанию нет доступа к дневнику, фото, AI-диалогам и health profile.
- `content_manager`: доступ к каталогу и контенту, без доступа к приватным дневникам.
- `admin`: системное управление согласно permissions.
- `superuser`: технический доступ, не для повседневной работы.

Support-доступ к чувствительным данным возможен только через отдельную процедуру и должен логироваться.

## Permission matrix / Матрица разрешений

RBAC foundation использует Django Groups/Permissions:

- business role group names: `user`, `support`, `content_manager`, `admin`;
- `superuser` не входит в business-role groups и остаётся техническим override-механизмом Django;
- DRF API закрыт по умолчанию через `IsAuthenticated`;
- публичные endpoint-ы должны явно указывать `AllowAny`;
- пользовательские объекты должны иметь object-level permissions и IDOR-тесты.

| Роль | Разрешено | Запрещено по умолчанию |
| --- | --- | --- |
| `anonymous` | Только явно публичные endpoint-ы, например `GET /api/v1/health/`. | Любые приватные профили, дневники, фото, health data, AI-диалоги, admin/support/content endpoints. |
| `user` | Читать и изменять только собственные `UserProfile`, `NutritionProfile`, `NutritionSensitiveRestriction`, meals/diary, food scans и AI coach settings; пользоваться AI coach; читать nutrition catalog; будущие цели только в пределах собственных объектов. | Доступ к чужим UUID-ресурсам, чужим дневникам, чужим фото, AI-диалогам, изменение nutrition catalog, support/admin/content-management функциям. |
| `support` | Support tooling и support admin foundation без приватных пользовательских данных. | Health data, nutrition profile, allergies/medical restrictions, фото еды, дневники, AI coach и AI-диалоги, пользовательские профили, role groups и audit log по умолчанию. |
| `content_manager` | Управление каталогом продуктов, nutrients, справочниками и контентом через catalog/reference permissions. | Приватные дневники пользователей, фото, health data, nutrition profile, allergies/medical restrictions, AI coach и AI-диалоги, пользовательские профили, role groups и audit log по умолчанию. |
| `admin` | Административные permissions для управления users/profiles, role groups, nutrition catalog и просмотра read-only admin audit log согласно Django permissions. | Nutrition profile, sensitive restrictions, AI coach и AI-диалоги без отдельной процедуры; автоматический обход object-level policy без выданных permissions; использование как замена `superuser`; изменение audit log. |
| `superuser` | Полный технический доступ Django для аварийных/системных операций. | Повседневная операционная работа и роль обычного администратора продукта. |

Текущие permission groups:

- `user`: `accounts.view_own_userprofile`, `accounts.change_own_userprofile`, `accounts.view_own_nutritionprofile`, `accounts.change_own_nutritionprofile`, `accounts.view_own_nutritionsensitiverestriction`, `accounts.change_own_nutritionsensitiverestriction`, `diary.view_own_meal`, `diary.change_own_meal`, `food_scans.view_own_foodscan`, `food_scans.change_own_foodscan`, `ai_coach.use_ai_nutrition_coach`, `ai_coach.view_own_aicoachsettings`, `ai_coach.change_own_aicoachsettings`.
- `support`: `accounts.access_support_tools`, `accounts.view_support_admin`.
- `content_manager`: `accounts.manage_catalog_content`, `accounts.manage_reference_data`, `accounts.manage_food_catalog` и `nutrition` model permissions для `FoodCategory`, `FoodDataSource`, `Nutrient`, `FoodItem`, `FoodNutrient`.
- `admin`: `accounts.administer_accounts`, account model permissions, `auth.view_group`, `auth.change_group`, `accounts.view_adminauditlog`, support/content/reference/catalog foundation permissions и `nutrition` model permissions.

IDOR baseline: User A не должен читать или менять ресурс User B даже при знании UUID. Для `UserProfile`, nutrition profile/restrictions, `Meal` и `FoodScan` это покрыто API-тестами.

## AI safety

AI получает только минимально необходимый контекст пользователя.

Текущий AI Nutrition Coach foundation:

- реализован в backend app `ai_coach` через provider abstraction, без привязки бизнес-логики к конкретному LLM-провайдеру;
- получает только цель, дневные агрегаты, разрешённые dietary preferences и текущий запрос пользователя;
- не получает email, display name, UUID пользователя, фотографии, private object keys, sensitive restrictions или полную историю аккаунта;
- использует moderation/safety layer до и после provider call;
- хранит AI response/history только при явном chat history consent пользователя;
- unsafe user requests и unsafe provider outputs не сохраняются как `AICoachMessage`;
- AI-диалоги не регистрируются в Django Admin на этом этапе.

AI не должен:

- ставить диагнозы;
- назначать лекарства;
- заменять врача, лицензированного нутрициолога или психолога;
- самостоятельно принимать медицинские решения.
- отменять назначения врача;
- давать опасные extreme diet рекомендации.

Потенциально опасные ситуации требуют отдельной safety-логики до production.

## Права пользователя

Система должна поддерживать:

- удаление аккаунта;
- удаление связанных пользовательских данных;
- экспорт собственных данных;
- понятную обработку приватных фотографий и производных данных.

Перед production нужна юридическая проверка требований стран запуска.
