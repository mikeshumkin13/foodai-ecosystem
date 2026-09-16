# История изменений / Changelog

## 0.1.0 — кандидат релиза, ещё не опубликован

Дата подготовки: 2026-09-16. Ветка: `release/0.1.0`.
Основание: `develop` на `363ed3a`, после [PR #49](https://github.com/mikeshumkin13/foodai-ecosystem/pull/49).
Версии backend, Vision, frontend и OpenAPI уже равны `0.1.0`; это не означает выпуск стабильной версии.

### В составе первого MVP

- Django/DRF backend, PostgreSQL, Redis/Celery и отдельный FastAPI Vision service.
- UUID/email accounts, session-cookie authentication, CSRF, email verification и password reset API.
- Централизованные роли/permissions, ограничения Django Admin и read-only audit trail.
- Отдельный nutrition profile, consent и приватные sensitive restrictions.
- Расширяемый каталог FoodItem/Nutrient/FoodNutrient и Decimal calculation engine.
- Дневник с ручным добавлением еды, дневной агрегацией и историческими nutrient snapshots.
- Проверка и очистка JPEG/PNG, private local storage, асинхронное распознавание и исправление результатов.
- Оценка порции с uncertainty и отдельным хранением ручной коррекции; обязательное подтверждение scan.
- Next.js интерфейс регистрации, профиля, dashboard, diary, scan, coach и Privacy Center.
- Структурированные Nutrition/Fitness/Wellbeing foundations с safety boundaries.
- Data export, consent, удаление фотографий, истории AI и аккаунта.
- Structured logging, correlation ID, metrics/error monitoring abstractions и CI.

### Исправления этапа 30

- Восстановлены onboarding, email verification UI, session lifecycle, профиль и AI summary UI.
- Broker failure переводит scan в управляемое состояние ошибки с возможностью повторного запуска.
- Добавлены production LLM transport, ограничение времени и обработка некорректных ответов.
- Расширено multi-region распознавание; исправлены private mount, model warm-up и timeout budgets.
- Исправлено подтверждение scan на PostgreSQL; повторный confirm не создаёт второй Meal.
- Добавлен non-destructive recovery устаревшего локального PostgreSQL volume.
- Закрыты 4 BLOCKER и 8 HIGH в пределах [MVP QA](docs/MVP_QA_REPORT.md).

### Подготовка release candidate

- Добавлены [release notes](docs/RELEASE_NOTES.md), [checklist выпуска](docs/RELEASE_CHECKLIST.md)
  и [пошаговое руководство](docs/GETTING_STARTED.md).
- Повторены локальные проверки и аудит production-конфигурации; новые product features не добавлялись.
- Публичный production-выпуск пока запрещён: незакрытые deployment, storage, email, cache,
  backup/restore и эксплуатационные условия перечислены в checklist.

### Известные ограничения

Оценка массы не является измерением. Exploratory Vision benchmark не доказывает точность на
пользовательских фотографиях. AI не заменяет медицинского специалиста. Реальная SMTP-доставка,
платный LLM и production-инфраструктура не прошли приёмку. В MVP остаются 5 MEDIUM и 2 LOW,
включая неполную RU/EN локализацию и отсутствие web-форм восстановления/смены пароля.
