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
- `GET /api/v1/auth/csrf/` — выдаёт CSRF cookie/token для browser client.
- `POST /api/v1/auth/register/` — регистрация. Создаёт inactive user, `UserProfile`, role `user` и email verification token.
- `POST /api/v1/auth/login/` — login через Django session cookie. Access/refresh bearer tokens не возвращаются.
- `POST /api/v1/auth/logout/` — logout, очищает текущую session.
- `POST /api/v1/auth/refresh/` — продлевает session, ротирует session key и CSRF token.
- `GET /api/v1/auth/me/` — текущий пользователь без password/token fields.
- `POST /api/v1/auth/email/verify/` — подтверждение email по одноразовому token.
- `POST /api/v1/auth/email/resend/` — повторная отправка verification email с generic response.
- `POST /api/v1/auth/password/reset/request/` — запрос password reset с generic response.
- `POST /api/v1/auth/password/reset/confirm/` — применение password reset token и установка нового пароля.
- `POST /api/v1/auth/password/change/` — изменение пароля текущего пользователя.
- `GET /api/v1/accounts/profiles/{id}/` — чтение `UserProfile`.
- `PUT/PATCH /api/v1/accounts/profiles/{id}/` — обновление `UserProfile`.
- `GET /api/v1/accounts/nutrition-profiles/{id}/` — чтение собственного `NutritionProfile`.
- `PUT/PATCH /api/v1/accounts/nutrition-profiles/{id}/` — обновление собственного `NutritionProfile`; первое изменение требует `consent_accepted=true`.
- `GET /api/v1/accounts/nutrition-restrictions/` — список собственных allergies/intolerances/medical nutrition restrictions.
- `POST /api/v1/accounts/nutrition-restrictions/` — создание собственной sensitive nutrition restriction; требуется `consent_accepted=true`.
- `GET /api/v1/accounts/nutrition-restrictions/{id}/` — чтение собственной sensitive nutrition restriction.
- `PUT/PATCH/DELETE /api/v1/accounts/nutrition-restrictions/{id}/` — изменение или удаление собственной sensitive nutrition restriction.
- `GET /api/v1/foods/search/` — поиск продуктов в nutrition catalog по `q`; возвращает продукты, category, source, density metadata и динамический список nutrients per 100 g.
- `GET /api/v1/foods/{id}/` — карточка продукта по UUID с `Nutrient`/`FoodNutrient` values per 100 g и единицами.
- `POST /api/v1/foods/` — создание food catalog item; требуется catalog write permission.
- `PUT/PATCH/DELETE /api/v1/foods/{id}/` — изменение или удаление food catalog item; требуется catalog write permission.
- `POST /api/v1/meals/` — создание приёма пищи текущего пользователя. `MealItem` создаёт snapshot nutrients из выбранного `food_id` и `mass_g`; ручные значения calories/protein/fat/carbs разрешены и помечаются через `manually_corrected`.
- `GET /api/v1/meals/` — список собственных приёмов пищи; поддерживает фильтры `date`, `date_from`, `date_to` в формате `YYYY-MM-DD`.
- `GET /api/v1/meals/{id}/` — чтение собственного приёма пищи по UUID.
- `PATCH /api/v1/meals/{id}/` — изменение собственного приёма пищи; если передан `items`, состав заменяется новым набором snapshot items.
- `DELETE /api/v1/meals/{id}/` — удаление собственного приёма пищи.
- `GET /api/v1/diary/day/?date=YYYY-MM-DD` — дневная агрегация собственного дневника: totals по calories/protein/fat/carbs, `micronutrient_totals` и список meals за дату.
- `GET /api/v1/schema/` — OpenAPI schema.
- `GET /api/v1/docs/` — Swagger UI.

В Docker Compose health endpoint используется также для backend healthcheck после ожидания PostgreSQL/Redis и выполнения migrations.

Account API пока реализован только минимально для `UserProfile`.

Auth API использует cookie/session схему:

- web-клиент сначала вызывает `GET /api/v1/auth/csrf/`;
- для unsafe methods frontend отправляет `X-CSRFToken`;
- requests должны идти with credentials;
- bearer access/refresh token для web-клиента не выдаётся;
- password reset request и email resend возвращают generic response, чтобы не раскрывать наличие аккаунта.

Правила доступа:

- unauthenticated requests запрещены для account API;
- обычный `user` читает и изменяет только собственный профиль;
- обращение User A к UUID профиля User B не возвращает чужие данные;
- обычный `user` читает и изменяет только собственный nutrition profile и собственные sensitive nutrition restrictions;
- обращение User A к UUID nutrition profile или restriction User B не возвращает чужие данные;
- `support`, `content_manager` и business `admin` не получают доступ к nutrition profile и sensitive nutrition restrictions по умолчанию;
- `support` и `content_manager` не получают доступ к пользовательским профилям по умолчанию;
- `admin` с permission `accounts.administer_accounts` может работать с профилями;
- `superuser` использует технический Django override.
- authenticated users могут читать nutrition catalog через search/detail;
- обычный `user` не может создавать, изменять или удалять food catalog items;
- `content_manager` с permission `accounts.manage_food_catalog` и nutrition model permissions может изменять food catalog;
- `support` не может изменять food catalog;
- business `admin` и `superuser` могут изменять food catalog согласно выданным permissions/technical override.
- обычный `user` читает, создаёт, изменяет и удаляет только собственные meals;
- обращение User A к UUID meal User B не возвращает чужие данные;
- `support`, `content_manager` и business `admin` не получают API-доступ к приватным meals/diary day по умолчанию;
- `superuser` использует технический Django override для diary API.

Nutrition profile не реализует диагнозы. Аллергии, intolerance и medical restrictions хранятся отдельно от обычных dietary preferences.

Nutrition catalog хранит nutrient values как `FoodNutrient.amount_per_100g`, связанный с расширяемым справочником `Nutrient`. Нельзя проектировать клиентов так, будто доступны только calories/protein/fat/carbohydrate.

Meal history хранит nutrient snapshots внутри `MealItem`. Клиенты не должны пересчитывать прошлые дневниковые записи из текущего состояния global nutrition catalog.

## Breaking changes

Breaking API changes требуют:

1. документированного решения в `docs/DECISIONS.md`;
2. обновления `docs/API.md`;
3. тестов на новое поведение.
