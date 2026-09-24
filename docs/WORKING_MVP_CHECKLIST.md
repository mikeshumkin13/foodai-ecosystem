# Рабочая версия FoodAI: критерии готовности

Обновлено: 2026-09-24. Этот документ не является заявлением готовности всего продукта.
Текущий ориентир: полноценный web MVP на Mac и телефоне; запуск в интернете имеет отдельные условия.
Нативное мобильное приложение, wearable-интеграции, подписка и B2B остаются в ROADMAP, а не
подменяются заглушками ради отметки «готово».

## Пользовательские сценарии

| Область | Текущее подтверждённое состояние | Что осталось |
|---|---|---|
| Запуск | Launcher, 6 healthy сервисов, local/LAN origins, migrations, безопасный demo seed | Проверить на чистом окружении; локальная почта не заменяет внешнюю |
| Регистрация/вход | Реальный HTTP и mobile Chromium: SMTP Mailpit, resend, verify, login | Внешний SMTP, sender/domain и deliverability при публикации |
| Восстановление доступа | `feature/frontend-account-recovery`: reset/change UI, mobile logout; real SMTP/browser regression прошёл | Commit/PR/CI и интеграция в develop |
| Профиль | Owner-only API/UI, согласие, питание, цель | Runtime RU/EN предпочтение пока не применяется |
| Питание вручную | CRUD, даты, Decimal, исторические snapshots, Dashboard | Расширение проверенного nutrition catalog сверх 3 demo foods |
| Фото еды | Настоящие Redis/Celery/Vision, correction/confirm/diary, IDOR, bounded retries | ML accuracy не гарантируется; representative evaluation и ручное подтверждение обязательны |
| Тренировки | Structured domain models/API, rule-based планы, safety tests | Пользовательские экраны планов, упражнений и выполнения |
| Привычки | Safety-aware backend/API с минимальным контекстом | Пользовательский экран, малые действия/reflection и состояния ошибок |
| Nutrition Coach | UI/API, schema, safety, минимальный контекст | Реальная provider quality/budget проверка; local-test использует mock |
| Приватность | Export, consent, собственные photos/history/account deletion happy path | Надёжное завершение удаления при частичном DB/storage failure |
| Локализация | RU/EN словари присутствуют | Применение locale, форматы чисел/дат, перевод hardcoded UI |

## Отдельные группы доработки

1. `feature/frontend-account-recovery`: закрыть MVP-QA-012, доступный mobile logout.
2. `feature/frontend-i18n-runtime`: MVP-QA-011, единый runtime locale перед новыми экранами.
3. `feature/frontend-fitness`: планы и журнал тренировок поверх существующего API, без свободной генерации нагрузки.
4. `feature/frontend-wellbeing`: интерфейс помощника по привычкам с safety responses и consent.
5. `feature/privacy-deletion-resilience`: MVP-QA-014, durable workflow и failure-injection tests.
6. `feature/ci-postgres-redis`: MVP-QA-013, regression на реальных PostgreSQL/Redis.
7. `feature/production-object-storage`: MVP-QA-015, private S3-compatible adapter и integration tests.
8. Deployment/security: общий rate limiter, production server/proxy/static/readiness, dependency audit,
   reproducible dependencies, Docker layer cache (MVP-QA-016/017), backup/restore rehearsal.

Имена являются списком работ, не утверждением создания или завершения веток.
Изменения группировать по области, от актуального develop; сохранять feature-ветки, не merge в main.
Перед объединением нужны тесты, lint/typecheck/build, CI и проверка замечаний PR.

## Внешние условия

- Production hostname, сервер/регион и TLS требуют выбранной среды; не разворачивать в случайный аккаунт.
- SMTP credentials и verified sender в environment, не в Git/чате. Mailpit только для тестов.
- Платный LLM нельзя считать проверенным по mock-ответу или вызывать без согласованного бюджета.
- Юридические требования стран запуска и medical/safety evaluation требуют отдельной приёмки.
- Оставшиеся production gates перечислены в RELEASE_CHECKLIST.md; успешный local CI не снимает их.

## Финальная приёмка

Два независимых аккаунта: register/verify/login/reset/change/logout, profile, manual diary,
photo/processing/correction/confirm, diary/dashboard, coach, workout plan/log, wellbeing,
export/consent/delete. Отдельно проверить отказы Vision, broker, LLM и storage; mobile/desktop,
RU/EN, CSRF и чужие UUID. Результаты записывать по фактическим проверкам, не по наличию endpoint.
