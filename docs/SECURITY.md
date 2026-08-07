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
- Все будущие модели, связанные с пользователем, должны ссылаться на `settings.AUTH_USER_MODEL`.

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
| `user` | Читать и изменять только собственный `UserProfile`; будущие дневники, фото и цели только в пределах собственных объектов. | Доступ к чужим UUID-ресурсам, чужим дневникам, чужим фото, support/admin/content-management функциям. |
| `support` | Доступ к support tooling без приватных пользовательских данных. | Health data, фото еды, дневники, AI-диалоги и пользовательские профили по умолчанию. |
| `content_manager` | Управление будущим каталогом продуктов, нутриентами, справочниками и контентом. | Приватные дневники пользователей, фото, health data, AI-диалоги и пользовательские профили по умолчанию. |
| `admin` | Административные permissions для управления users/profiles и системными справочниками согласно Django permissions. | Автоматический обход object-level policy без выданных permissions; использование как замена `superuser`. |
| `superuser` | Полный технический доступ Django для аварийных/системных операций. | Повседневная операционная работа и роль обычного администратора продукта. |

Текущие permission groups:

- `user`: `accounts.view_own_userprofile`, `accounts.change_own_userprofile`.
- `support`: `accounts.access_support_tools`.
- `content_manager`: `accounts.manage_catalog_content`.
- `admin`: `accounts.administer_accounts` и текущие account model permissions.

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
