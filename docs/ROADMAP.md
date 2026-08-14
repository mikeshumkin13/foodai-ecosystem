# Roadmap / Дорожная карта

## MVP

- Создать foundation репозитория и документацию.
- Scaffold Django backend.
- Настроить PostgreSQL, Redis и Celery.
- Реализовать authentication и базовую модель пользователя.
- Реализовать роли и object-level permissions.
- Реализовать безопасную загрузку фото еды: размер, MIME, фактический формат, EXIF stripping, приватное хранение.
- Добавить базовые сущности дневника питания.
- Добавить базовый каталог продуктов и нутриентов.
- Scaffold Vision service с FastAPI.
- Определить контракт backend/Vision.
- Реализовать первый end-to-end scan orchestration с обязательным подтверждением пользователя перед записью в дневник.
- Scaffold Next.js PWA.
- Добавить основу локализации `ru`/`en`.
- Покрыть MVP unit/API тестами.

## Beta

- Улучшить UX подтверждения и исправления распознавания.
- Добавить daily summary и базовую аналитику рациона.
- Добавить AI-помощника по питанию с safety-логикой.
- Добавить экспорт и удаление пользовательских данных.
- Добавить audit log административных действий.
- Добавить расширенные API integration tests.
- Подготовить закрытое тестирование с реальными пользователями.

## Production

- Провести legal review для стран запуска.
- Провести security review и threat modeling.
- Настроить production CI/CD.
- Настроить monitoring, alerting и incident response.
- Настроить backup и disaster recovery.
- Проверить privacy, data retention, account deletion и export flows.
- Подготовить billing/subscription, если он входит в первый релиз.
- Подготовить release branch и production launch checklist.

## Post-launch

- AI-тренер.
- AI-помощник по привычкам и самочувствию.
- Тренировки и цели.
- Графики прогресса и персонализация.
- Мобильное приложение.
- HealthKit и Health Connect.
- Умные весы и wearable-интеграции.
- B2B API.
- Улучшение CV/ML-моделей на validation datasets.
