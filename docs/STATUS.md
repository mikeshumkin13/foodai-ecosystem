# Status / Статус

Last updated / Обновлено: 2026-08-12

## Текущий завершённый этап

ЭТАП 8, PROMPT 8 — health/nutrition profile завершён.

## Состояние

- Создан каталог `foodai-ecosystem`.
- Внутри каталога инициализирован Git-репозиторий.
- Основная ветка: `main`.
- Создана структура monorepo.
- Созданы базовые foundation-файлы и документация.
- Django, Next.js и FastAPI не устанавливались.
- После первого commit создана ветка `develop` от `main`.
- Feature-ветка не создавалась.
- Создана ветка `feature/backend-foundation` от `develop`.
- Добавляется Django + Django REST Framework backend foundation.
- Создано приложение `core` без User/Food/Diary моделей.
- Добавлен endpoint `GET /api/v1/health/`.
- Добавлены OpenAPI schema и Swagger UI.
- Добавлены pytest, pytest-django, Ruff, mypy и coverage в `pyproject.toml`.
- Зависимости установлены в локальный `.venv`.
- Добавлено правило: сообщения commit должны быть понятными человеческими фразами, без закодированных префиксов вроде `feat:`, `fix:`, `chore:`.
- Ветка `feature/backend-foundation` переоснована на `origin/develop`, чтобы PR корректно сравнивался с remote `develop`.
- Создана ветка `feature/dev-infrastructure` от `develop`.
- Добавлена локальная Docker Compose инфраструктура: PostgreSQL, Redis, backend, volumes и healthchecks.
- PostgreSQL и Redis не публикуют порты наружу.
- Backend ждёт готовности PostgreSQL/Redis через healthchecks и `wait_for_dependencies`.
- Migrations выполняются предсказуемо через backend entrypoint при `DJANGO_RUN_MIGRATIONS=true`.
- Локальный запуск выполняется одной командой: `make dev-up`.
- Создана ветка `feature/accounts` от `develop`.
- Добавлено Django-приложение `accounts`.
- С самого начала доменной разработки backend использует custom `accounts.User` через `AUTH_USER_MODEL`.
- `accounts.User` использует UUID primary key, уникальный email как основной логин, стандартный Django password hashing, `is_active`, `is_staff` и timestamps.
- Дополнительные пользовательские данные вынесены в `accounts.UserProfile`; health/fitness данные не помещены в `User`.
- Добавлены initial migration, Django admin, test factories и тесты для user creation, superuser creation, unique email и password hashing.
- Создана ветка `feature/rbac` от актуального `develop`.
- RBAC foundation реализован через централизованные Django Groups/Permissions в `accounts.rbac`.
- Добавлены business roles: `user`, `support`, `content_manager`, `admin`.
- `superuser` сохранён как отдельный технический Django-механизм и не входит в business roles.
- DRF API закрыт по умолчанию через `IsAuthenticated`; публичный health endpoint явно использует `AllowAny`.
- Добавлен минимальный `UserProfile` API с object-level permissions.
- Добавлены тесты на role groups, запрет доступа, support/content-manager ограничения, admin/superuser доступ и отдельный IDOR-сценарий по UUID.
- Создана ветка `feature/auth` от актуального `develop`.
- Реализована регистрация через `POST /api/v1/auth/register/`.
- Реализованы login, logout, refresh и endpoint `GET /api/v1/auth/me/`.
- Для web-клиента выбрана session-cookie схема: access token не выдаётся и не хранится в `localStorage`.
- Добавлен CSRF bootstrap endpoint `GET /api/v1/auth/csrf/`.
- Добавлена email verification architecture: inactive user при регистрации, одноразовый hashed DB token, verify/resend endpoints.
- Добавлен password reset flow с одноразовыми hashed DB tokens и generic response без email enumeration.
- Добавлено изменение пароля текущего пользователя.
- Добавлены cookie/session/CSRF настройки через environment variables.
- Добавлены scoped throttles для brute-force/rate limiting.
- OAuth в этом этапе не реализовывался.
- Создана ветка `feature/admin-panel` от актуального `develop`.
- Django Admin усилен для `accounts.User`, `accounts.UserProfile`, Django `Group` как foundation для ролей и `accounts.AdminAuditLog`.
- В admin list view не выводятся password/token fields; `UserProfile` показывает UUID пользователя вместо лишних персональных данных.
- Опасные bulk actions отключены для зарегистрированных admin-моделей.
- Email verification и password reset token-модели не зарегистрированы в Django Admin.
- Добавлен read-only `AdminAuditLog`, который зеркалирует стандартный `django_admin_log` и редактирует представление account-объектов в audit trail.
- RBAC расширен permissions для admin-аудита, role groups, support admin foundation, справочников и будущего food catalog без создания преждевременных food-моделей.
- Добавлены тесты admin permissions: видимость моделей, запрет changelist для `support`/`content_manager`, read-only audit log, отсутствие bulk actions и sanitization audit entry.
- Создана ветка `feature/user-health-profile` от актуального `develop`.
- Добавлен `accounts.NutritionProfile` для MVP-настроек питания: цель, рост, масса, age category, activity level, preferred units, dietary preferences и consent/version metadata.
- Для privacy выбран `age_category`; дата рождения и точный год рождения не хранятся.
- Allergies, intolerance и medical nutrition restrictions вынесены в отдельную sensitive-модель `accounts.NutritionSensitiveRestriction`.
- Диагнозы не реализовывались.
- Новая регистрация создаёт пустой `NutritionProfile` без granted consent.
- Добавлены owner-only API endpoint-ы для nutrition profile и sensitive nutrition restrictions.
- Business roles `support`, `content_manager` и `admin` не получают API-доступ к nutrition profile и sensitive restrictions по умолчанию.
- `NutritionProfile` и `NutritionSensitiveRestriction` не зарегистрированы в Django Admin на этом этапе.
- Добавлены consent checks и IDOR/API tests для nutrition profile и sensitive restrictions.

## Проверки

- `git branch --show-current` — `main` перед первым commit.
- `git status --short --branch` — проверен перед первым commit.
- Проверка структуры файлов выполнена через `find . -maxdepth 3 -type f -not -path './.git/*'`.
- Тесты: not applicable / неприменимо, потому что код и test runner ещё не созданы.
- Линтеры: not applicable / неприменимо, потому что код и lint-конфигурация ещё не созданы.
- `make test` — passed, 1 test passed, coverage 88.12%.
- `make lint` — passed, Ruff reports no issues.
- `make typecheck` — passed, mypy reports no issues in 17 source files.
- `make django-check` — passed, Django system check identified no issues.
- `make check` — passed, полный backend quality gate пройден.
- `backend/manage.py spectacular --validate` — passed, OpenAPI schema генерируется без ошибок.
- `make check` — passed после обновления правила commit messages.
- `make check` — passed после rebase на `origin/develop`.
- `backend/manage.py spectacular --validate` — passed после rebase на `origin/develop`.
- `git status --short --branch` — clean на `feature/backend-foundation` перед обновлением статуса публикации.
- `make check` — passed для PROMPT 3: Ruff без ошибок, mypy без ошибок в 21 source files, Django system check без ошибок, pytest: 3 passed, coverage 84.62%.
- `backend/manage.py spectacular --validate` с безопасными локальными env — passed, OpenAPI schema валидируется без ошибок.
- `docker compose --env-file .env config --quiet` — passed.
- `make dev-up-detached` — passed, Docker image backend собран, PostgreSQL/Redis/backend запущены.
- `docker compose --env-file .env ps` — PostgreSQL, Redis и backend healthy; PostgreSQL/Redis не публикуют host ports.
- `docker compose --env-file .env exec -T backend python backend/manage.py wait_for_dependencies --timeout 10 --interval 1 --settings=config.settings.local` — passed, backend видит PostgreSQL и Redis.
- `curl -fsS http://127.0.0.1:8000/api/v1/health/` — passed, ответ `{"status":"ok"}`.
- `docker compose --env-file .env exec -T backend python -m pytest` — passed, 3 tests passed, coverage 83.52%.
- `docker compose --env-file .env down` — passed, локальный стек остановлен без удаления volumes.
- `make check` — passed для PROMPT 4: Ruff без ошибок, mypy без ошибок в 29 source files, Django system check без ошибок, pytest: 11 passed, coverage 88.77%.
- `backend/manage.py makemigrations --check --dry-run` с безопасными локальными env — passed, no changes detected.
- `backend/manage.py spectacular --validate` с безопасными локальными env — passed.
- `docker compose --env-file .env config --quiet` — passed.
- `make dev-up-detached` на существующем dev volume из PROMPT 3 выявил ожидаемую локальную проблему `InconsistentMigrationHistory`, потому что volume был создан до `AUTH_USER_MODEL = "accounts.User"`.
- Удаление существующих локальных Docker volumes не выполнялось без явного подтверждения пользователя.
- `docker compose -p foodai_accounts_check --env-file .env up --build -d` — passed на fresh isolated volumes.
- `docker compose -p foodai_accounts_check --env-file .env ps` — PostgreSQL, Redis и backend healthy; PostgreSQL/Redis не публикуют host ports.
- Fresh Docker logs — migrations применены в корректном порядке: `accounts.0001_initial` до `admin.0001_initial`.
- `curl -fsS http://127.0.0.1:8000/api/v1/health/` на isolated stack — passed, ответ `{"status":"ok"}`.
- `docker compose -p foodai_accounts_check --env-file .env exec -T backend python backend/manage.py migrate --check --settings=config.settings.local` — passed, unapplied migrations нет.
- `docker compose -p foodai_accounts_check --env-file .env exec -T backend python -m pytest` — passed, 11 tests passed, coverage 88.07%.
- `docker compose -p foodai_accounts_check --env-file .env down` — passed, isolated stack остановлен без удаления volumes.
- `make check` — passed для PROMPT 5: Ruff без ошибок, mypy без ошибок в 36 source files, Django system check без ошибок, pytest: 25 passed, coverage 90.02%.
- `backend/manage.py makemigrations --check --dry-run` с безопасными локальными env — passed, no changes detected.
- `backend/manage.py spectacular --validate` с безопасными локальными env — passed.
- `docker compose --env-file .env config --quiet` — passed.
- `docker compose --env-file .env build backend` — passed.
- `docker compose -p foodai_rbac_check --env-file .env up --build -d` — passed на fresh isolated volumes.
- `docker compose -p foodai_rbac_check --env-file .env ps` — PostgreSQL, Redis и backend healthy; PostgreSQL/Redis не публикуют host ports.
- Fresh Docker logs — migrations применены в корректном порядке: `accounts.0001_initial`, затем `accounts.0002_rolepermission_alter_userprofile_options`, затем `admin.0001_initial`.
- `curl -fsS http://127.0.0.1:8000/api/v1/health/` на isolated stack — passed, ответ `{"status":"ok"}`.
- `docker compose -p foodai_rbac_check --env-file .env exec -T backend python backend/manage.py migrate --check --settings=config.settings.local` — passed, unapplied migrations нет.
- `docker compose -p foodai_rbac_check --env-file .env exec -T backend python -m pytest` — passed, 25 tests passed, coverage 89.61%.
- `docker compose -p foodai_rbac_check --env-file .env down` — passed, isolated stack остановлен без удаления volumes.
- `make check` — passed для PROMPT 6: Ruff без ошибок, mypy без ошибок в 41 source files, Django system check без ошибок, pytest: 39 passed, coverage 92.71%.
- `backend/manage.py makemigrations --check --dry-run` с безопасными локальными env — passed, no changes detected.
- `backend/manage.py spectacular --validate` с безопасными локальными env — passed, OpenAPI schema валидируется без ошибок.
- `docker compose --env-file .env config --quiet` — passed.
- `docker compose --env-file .env build backend` — passed.
- `make check` — passed для PROMPT 7: Ruff без ошибок, mypy без ошибок в 42 source files, Django system check без ошибок, pytest: 54 passed, coverage 91.64%.
- `backend/manage.py makemigrations --check --dry-run` с безопасными локальными env — passed, no changes detected.
- `backend/manage.py spectacular --validate` с безопасными локальными env — passed, OpenAPI schema валидируется без ошибок.
- `docker compose --env-file .env config --quiet` — passed.
- `docker compose --env-file .env build backend` — blocked в Codex sandbox из-за запрета записи Docker buildx в `~/.docker`; требуется ручная проверка вне sandbox.
- `make check` — passed для PROMPT 8: Ruff без ошибок, mypy без ошибок в 43 source files, Django system check без ошибок, pytest: 73 passed, coverage 88.94%.
- `backend/manage.py makemigrations --check --dry-run` с безопасными локальными env — passed, no changes detected.
- `backend/manage.py spectacular --validate` с безопасными локальными env — passed, OpenAPI schema валидируется без ошибок.
- `docker compose --env-file .env config --quiet` — passed.
- `docker compose --env-file .env build backend` — passed, backend image собран.

## Следующий этап

Остановиться после PROMPT 8. ЭТАП 9 — Nutrition database не начинать до отдельного продолжения после завершения PR/merge этого этапа.
