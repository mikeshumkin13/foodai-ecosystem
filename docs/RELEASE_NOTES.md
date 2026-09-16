# FoodAI Ecosystem 0.1.0 / Release Candidate

Подготовлено: 2026-09-16. Статус: **локальный кандидат для QA, не production release**.

## Назначение

Первая версия объединяет ручной дневник питания и поток photo → Vision → correction → confirmation
→ diary. Фотография не записывается в дневник как приём пищи без подтверждения пользователя.
Изменение каталога не пересчитывает исторические nutrient snapshots.

Web-клиент включает dashboard, дневник, scan, профиль, Nutrition Coach и Privacy Center.
Ручное добавление продуктов работает независимо от Vision и Celery. Nutrition Coach имеет
provider abstraction, структурированный ответ и safety layer. Fitness/Wellbeing остаются
структурированными backend foundations; это не обещание готовых отдельных web-приложений.

## Основание и границы релиза

- Ветка `release/0.1.0` создана от `develop` (`363ed3a6864002dda9e75fd4d2279b4bd2ba951e`).
- [PR #49](https://github.com/mikeshumkin13/foodai-ecosystem/pull/49) объединён пользователем в `develop`.
- [CI интеграционной ветки](https://github.com/mikeshumkin13/foodai-ecosystem/actions/runs/34889212744)
  прошёл: Backend, Vision и Frontend. Reviews и открытых review threads на момент проверки не было;
  это не равно независимому security review.
- Изменения подготовки RC ограничены документацией. API, модели, migrations и версии не изменены.
- Тег `v0.1.0` не создан, merge в `main` не выполнен. CI будущего release PR ещё требуется.

## Что проверить пользователю

Следовать [руководству запуска](GETTING_STARTED.md), затем пройти:

1. Регистрация, локальное подтверждение тестового аккаунта, login/logout.
2. Заполнение профиля с явным consent.
3. Ручной приём пищи с несколькими продуктами, изменение массы и проверка дневной суммы.
4. JPEG/PNG → обработка → исправление продукта/массы → подтверждение → запись в Diary.
5. Вход вторым пользователем в отдельном профиле браузера: чужие записи и фотографии недоступны.
6. Экспорт, управление consent и удаление только специально созданных тестовых данных.

## Ограничения и условия выпуска

- Vision выдаёт предложения, а не достоверный состав блюда. Exploratory recall `0.48` получен на
  восьми crop; см. [Vision validation](VISION_VALIDATION.md). Это не production accuracy или SLA.
- Масса оценивается по ограниченным данным RGB и предположениям о геометрии/плотности;
  пользователю нужно проверить продукт и граммы, при необходимости использовать весы.
- AI не ставит диагнозы, не назначает лечение и не заменяет врача. Safety tests не доказывают
  отсутствие всех опасных ответов; live RU/EN оценка провайдера остаётся отдельным условием.
- Локальный `AI_COACH_PROVIDER=mock` не вызывает платный API и не выдаёт настоящий LLM-ответ.
- Письма по умолчанию in-memory; реальная email-доставка не настроена. Восстановление/смена
  пароля доступны через API, но отдельные web-формы ещё отсутствуют.
- Root Compose предназначен для разработки: Django `runserver`, local settings, source mounts.
- Реализован только private local filesystem storage. S3-адаптер пока отсутствует.
- Runtime RU/EN, PostgreSQL/Redis CI, deletion compensation и другие остаточные риски перечислены
  в [QA report](MVP_QA_REPORT.md) и [release checklist](RELEASE_CHECKLIST.md).

**Решение: NO-GO для публичного production и стабильного тега.** Подготовка RC не снимает
deployment-гейты и не означает, что система полностью безопасна.

## Предлагаемый текст PR

Заголовок: `Подготовлен кандидат первого релиза FoodAI Ecosystem 0.1.0`

Описание: первый MVP из `develop` и документация подготовки RC: changelog, release notes,
пошаговый локальный запуск, проверки, backup/rollback и оставшиеся production-условия.
Новых product features в release-ветке нет. Создавать PR `release/0.1.0 → main` как Draft;
не объединять и не публиковать стабильный тег до закрытия checklist, успешного CI и review.
