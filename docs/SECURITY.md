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

## Dev infrastructure security

- Docker Compose не содержит секретов напрямую, а читает значения из `.env`.
- `.env.example` содержит только безопасные локальные примеры и не должен использоваться как production-конфигурация.
- PostgreSQL и Redis в локальной инфраструктуре не публикуют порты на host без отдельной необходимости.
- Backend публикует только HTTP-порт разработки.
- Redis включён с паролем даже в локальной инфраструктуре.

## Admin security

- Django Admin доступен только active staff users через стандартную Django admin authentication.
- В admin зарегистрированы только текущие операционные модели: `accounts.User`, `accounts.UserProfile`, Django `Group` для role groups и read-only `accounts.AdminAuditLog`.
- `EmailVerificationToken` и `PasswordResetToken` не зарегистрированы в admin, чтобы не расширять поверхность доступа к token metadata.
- `User` list view показывает email как login identifier, flags, roles и timestamps; password hash не выводится в списках.
- `UserProfile` list view показывает UUID пользователя и language/timestamps; display name не выводится в списке.
- Bulk actions отключены для зарегистрированных admin-моделей; опасные массовые действия не добавляются.
- `AdminAuditLog` доступен только на чтение, зеркалирует стандартный `django_admin_log` и хранит минимальные metadata: actor, action, model label, object id, sanitized object representation, change message и timestamps.
- Account object representations в audit log редактируются до `app.model:object_id`, чтобы не переносить email/profile/token-строки без необходимости.
- `support` и `content_manager` могут войти в admin только при явном `is_staff=True`, но не видят чувствительные account/audit/role models без model permissions.

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
| `user` | Читать и изменять только собственные `UserProfile`, `NutritionProfile` и `NutritionSensitiveRestriction`; будущие дневники, фото и цели только в пределах собственных объектов. | Доступ к чужим UUID-ресурсам, чужим дневникам, чужим фото, support/admin/content-management функциям. |
| `support` | Support tooling и support admin foundation без приватных пользовательских данных. | Health data, nutrition profile, allergies/medical restrictions, фото еды, дневники, AI-диалоги, пользовательские профили, role groups и audit log по умолчанию. |
| `content_manager` | Управление будущим каталогом продуктов, нутриентами, справочниками и контентом через catalog/reference permissions. | Приватные дневники пользователей, фото, health data, nutrition profile, allergies/medical restrictions, AI-диалоги, пользовательские профили, role groups и audit log по умолчанию. |
| `admin` | Административные permissions для управления users/profiles, role groups и просмотра read-only admin audit log согласно Django permissions. | Nutrition profile и sensitive restrictions без отдельной процедуры; автоматический обход object-level policy без выданных permissions; использование как замена `superuser`; изменение audit log. |
| `superuser` | Полный технический доступ Django для аварийных/системных операций. | Повседневная операционная работа и роль обычного администратора продукта. |

Текущие permission groups:

- `user`: `accounts.view_own_userprofile`, `accounts.change_own_userprofile`, `accounts.view_own_nutritionprofile`, `accounts.change_own_nutritionprofile`, `accounts.view_own_nutritionsensitiverestriction`, `accounts.change_own_nutritionsensitiverestriction`.
- `support`: `accounts.access_support_tools`, `accounts.view_support_admin`.
- `content_manager`: `accounts.manage_catalog_content`, `accounts.manage_reference_data`, `accounts.manage_food_catalog`.
- `admin`: `accounts.administer_accounts`, account model permissions, `auth.view_group`, `auth.change_group`, `accounts.view_adminauditlog`, support/content/reference/catalog foundation permissions.

IDOR baseline: User A не должен читать или менять ресурс User B даже при знании UUID. Для `UserProfile` это покрыто API-тестом.

## AI safety

AI получает только минимально необходимый контекст пользователя.

AI не должен:

- ставить диагнозы;
- назначать лекарства;
- заменять врача, лицензированного нутрициолога или психолога;
- самостоятельно принимать медицинские решения.

Потенциально опасные ситуации требуют отдельной safety-логики до production.

## Права пользователя

Система должна поддерживать:

- удаление аккаунта;
- удаление связанных пользовательских данных;
- экспорт собственных данных;
- понятную обработку приватных фотографий и производных данных.

Перед production нужна юридическая проверка требований стран запуска.
