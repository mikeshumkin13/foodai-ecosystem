# Checklist выпуска 0.1.0

Обновлено: 2026-09-16. Ветка: `release/0.1.0`.
**Текущее решение: NO-GO для публичного production.** RC подготовлен для локальной приёмки.
Незаполненный пункт означает непроверенное/невыполненное условие, а не разрешённое исключение.

## Происхождение и проверки

- [x] `develop` на `363ed3a` содержит объединённый PR #49; tree совпадает с проверенным `97b6295`.
- [x] CI PR #49: Backend, Vision, Frontend success, run `34889212744`.
- [x] Release-ветка создана от указанного `develop`; в подготовке RC нет новых product features.
- [x] Backend/Vision Ruff, mypy по 183 файлам и Django system checks: PASS.
- [x] Общий pytest: 287 passed, coverage 88.02%, threshold 80%; один сторонний warning.
- [x] Frontend lint по 69 файлам, TypeScript, 21 Vitest test и production build: PASS.
- [x] `pip check`: PASS. Это проверка совместимости, не vulnerability audit.
- [x] На настоящем модуле `config.settings.production` с тестовыми env: DEBUG=false,
  HTTPS redirect, HSTS, nosniff, DENY, secure cookies, deny-by-default, host/CORS allowlists и CSRF.
- [x] На временной SQLite БД: migration drift отсутствует, все migrations применены,
  `migrate --check` и OpenAPI validation прошли; `collectstatic` собрал 163 файла.
- [x] Финальный Docker build backend/Vision/Celery завершился успешно 2026-09-15.
- [x] PostgreSQL regression повторён: 36 passed за 49.24 секунды на отдельной тестовой БД;
  applied migrations рабочей локальной БД проверены без изменений.
- [x] После восстановления прерванной установки dependencies выполнен frontend frozen offline
  install (412 packages, lockfile не менялся), lint/typecheck/21 test/build прошли повторно.
- [x] Browser E2E повторён 2026-09-16: 3 Chromium scenarios passed за 8.7 секунды.
- [x] В tracked-файлах не найдены `.env`, private keys, DB dumps и распространённые
  форматы реальных API credentials. Полная история Git и внешние secret stores не аудировались.
- [x] Финальный запуск пересобранных контейнеров 2026-09-16: PostgreSQL, Redis, backend, Vision,
  Celery 5/5 healthy; `GET /api/v1/health/` ответил `{"status":"ok"}`.
- [x] Проверены 7 release-документов, 20 локальных ссылок и закрытие code fences;
  `git diff --check` без ошибок. Изменения только документационные.
- [ ] Strict production deploy check: **FAIL**, `foodai_security.W002` (local photo storage).
- [ ] CI и независимый review release PR на окончательном commit.

Предыдущая интеграционная проверка того же application-кода: 36 PostgreSQL regression tests,
3 desktop и 3 mobile Playwright test, реальные Redis/Celery/Vision и two-user API smoke прошли
2026-09-14. Это историческое свидетельство из [MVP QA](MVP_QA_REPORT.md), а не тест целевого
production-окружения. Browser E2E использует mock API, реальный API smoke проверен отдельно.
Локальные диагностические журналы RC находятся в ignored `.cache/release-*.log`.

## Обязательные production-условия

| ID | Что отсутствует / риск | Критерий закрытия | Ответственный |
|---|---|---|---|
| RC-01 | Compose принудительно использует local settings и `runserver`; dev dependencies и source mounts | Отдельная production-конфигурация, WSGI/ASGI server, immutable images, non-root/least privilege, без лишних mounts/секретов | DevOps/backend, назначить |
| RC-02 | Private S3 не реализован, только filesystem; strict check выдаёт W002 | Реальный private S3-compatible adapter, запрет public access, owner checks, ограниченные credentials, удаление/export, интеграционные тесты | Backend, назначить |
| RC-03 | SMTP env подключены; local-test verification проверяется через Mailpit. Внешняя доставка/staging ещё не проверены | Реальная безопасная доставка verification/reset на staging, verified sender, корректный HTTPS frontend URL, отсутствие токенов в логах | Backend/operations, назначить |
| RC-04 | `CACHES` не настроен: throttles используют per-process LocMemCache; Redis broker это не исправляет | Общий ограниченный cache/rate limiter, проверка brute-force через несколько workers, private Redis/ACL | Backend/security, назначить |
| RC-05 | Нет принятой схемы TLS proxy/static/frontend deployment | HTTPS без redirect loop, доверие forwarding headers только своему proxy, явные hosts/origins, `/static/`, правильный build-time API URL | DevOps, назначить |
| RC-06 | Backup/restore и rollback не отрепетированы на целевом окружении | Восстановление БД и фото на изолированном стенде, проверенные RPO/RTO, retention/deletion policy и владелец | Operations, назначить |
| RC-07 | Health endpoints в основном liveness; внешние monitoring/alerts не подключены | Dependency readiness, worker/Vision warm-up, alert на queue delay/ошибки/latency, privacy review telemetry | Operations/backend, назначить |
| RC-08 | Нет release dependency vulnerability gate/зафиксированного backend dependency set | Audit Python/npm/images, проверка лицензий, исправление или документированная оценка находок, фиксация deployable artifacts/digests | Security/release owner, назначить |
| RC-09 | Paid LLM, реальный SMTP, production safety и юридическая приёмка не проводились | Отдельное согласование бюджета, ключей, регионов/retention, RU/EN safety eval и условий стран запуска | Product/security/legal, назначить |

Эти условия не меняют задним числом severity аудита MVP. В частности, MVP-QA-015 был MEDIUM для
локального MVP, но отсутствие private S3 блокирует production по требованиям проекта.
Нельзя указать фиктивный `FOOD_SCAN_PRIVATE_STORAGE_BACKEND=s3-compatible`: factory отклоняет
неподдерживаемые реализации. Нельзя скрывать W002 или снижать fail-level ради зелёного выпуска.
Процедуру выдачи доступа support и восстановление удалённых данных также проверить при запуске.

## Конфигурация и секреты

- [ ] Внешняя система передаёт уникальные `DJANGO_SECRET_KEY`, DB/Redis credentials и ключ провайдера;
  значений нет в Git, image layers, shell history, public frontend env и CI logs.
- [ ] `DJANGO_SETTINGS_MODULE=config.settings.production`, `APP_ENV=production`, `DJANGO_DEBUG=false`.
- [ ] `DJANGO_ALLOWED_HOSTS` содержит точные реальные hosts, не `*`; TLS и hostname проверены снаружи.
- [ ] CORS/CSRF origins ограничены нужными HTTPS origins; credentials нужны только доверенному web.
- [ ] Secure/HttpOnly cookies и выбранный SameSite проверены в реальном браузере; CSRF не отключён.
- [ ] `FRONTEND_BASE_URL` и build-time `NEXT_PUBLIC_API_BASE_URL` указывают на согласованные HTTPS адреса,
  не localhost. `.env` backend не настраивает автоматически build frontend.
- [ ] `DJANGO_STATIC_URL=/static/`; собранный STATIC_ROOT обслуживает web server, не Django runserver.
- [ ] Приватные фото не находятся в static root, не обслуживаются CDN как public media; Vision имеет
  только нужный доступ. Vision endpoint не доступен из публичной сети.
- [ ] HSTS includeSubDomains/preload согласован для всех поддоменов; это не включается без проверки TLS.
- [ ] Таймауты Vision/Celery согласованы с реальным warm-up и CPU: local baseline 60/90/120 секунд
  для Vision/soft/hard; production бюджеты измерить отдельно. Eager mode выключен.
- [ ] Dev Compose `env_file: .env` не скопирован в production как есть: каждому сервису только его секреты.
- [ ] Логи разделены на errors/security/metrics, redact sensitive payload; установлен retention/access,
  проверен внешний monitoring adapter без отправки фото, диалогов и подробного профиля.

## Воспроизведение проверок

Локально из корня проекта после установки зависимостей:

```bash
make check
.venv/bin/python -m pip check
cd frontend
pnpm test:e2e
```

Следующие команды выполняет release operator **в изолированном staging-контейнере с production
settings и staging credentials**, а не над пользовательской локальной или production БД.
Environment уже должен быть передан извне; `.env` автоматически `manage.py` не загружает.

```bash
python backend/manage.py check --settings=config.settings.production
python backend/manage.py check --deploy --fail-level WARNING --settings=config.settings.production
python backend/manage.py makemigrations --check --dry-run --settings=config.settings.production
python backend/manage.py migrate --plan --settings=config.settings.production
python backend/manage.py migrate --noinput --settings=config.settings.production
python backend/manage.py migrate --check --settings=config.settings.production
python backend/manage.py collectstatic --noinput --settings=config.settings.production
python backend/manage.py spectacular --validate --file /tmp/openapi.yml --settings=config.settings.production
```

При любой ошибке остановить выпуск. Нужны как fresh PostgreSQL migrations, так и обновление копии
предыдущей БД; SQLite не заменяет PostgreSQL locking/integration tests. На production миграции
выполняются одним migration job после backup, до запуска новой версии, не каждым worker.
Не использовать `--fake`, удаление migrations или `docker compose down -v` для сокрытия ошибок.

## Backup, восстановление и rollback

Это план для согласования, **не уже работающий backup-сервис**. До GO оператор заполняет:

| Параметр | Утверждённое значение |
|---|---|
| Владелец и контакт при инциденте | Не назначен |
| RPO: допустимая потеря данных | Не согласовано |
| RTO: время восстановления | Не согласовано |
| Частота/retention и место encrypted off-host backup | Не согласовано |
| Дата restore drill и измеренное время | Не выполнено |

1. До изменения схемы сохранить совместимые версии application/images, dependency manifest,
   migrations и конфигурации; секреты хранить отдельно с ограниченным доступом.
2. Получить согласованный backup PostgreSQL и private objects. Для начального варианта запланировать
   maintenance window: остановить новые записи/uploads/deletions, дождаться/корректно остановить
   Celery tasks, затем создать DB dump и snapshot фото. Одного `pg_dump` недостаточно для согласованности
   с filesystem/S3. Для меньшего RPO отдельно спроектировать WAL/PITR и object versioning.
3. Хранить encrypted backups вне узла приложения; ограничить IAM, проверять checksum и расписание.
   Не помещать dumps в Git, web-root или CI artifacts. Redis queue/cache не являются источником дневника.
4. Восстановить в новую изолированную PostgreSQL БД и отдельное private storage, отключить внешние
   письма/LLM и workers. Проверить migrations, FK/counts, роли, audit, доступность фото, snapshots,
   две учётные записи и IDOR. `pg_restore --list` подтверждает структуру архива, но не restore drill.
5. Перед включением workers исключить повторную обработку старых задач и подтвердить idempotency.
   Проверить восстановление account/photo deletion requests, чтобы backup не вернул удалённые данные
   в обычный доступ; политика retention и исполнения удалений требует согласования.
6. Rollback application на предыдущий image допустим только при совместимой схеме. Иначе forward fix
   либо отдельно разрешённое восстановление backup с объявленной потерей данных и maintenance window.
   Не откатывать migrations/volumes вслепую. Для первого релиза в `main` ещё нет рабочей предыдущей
   production-версии; rollback может означать остановку сервиса, а не переключение на `main`.

## Проверка пользователем и merge

1. Пройти [пошаговый запуск и пользовательскую приёмку](GETTING_STARTED.md). Не использовать реальные
   чувствительные данные на демонстрационном стенде.
2. Закрыть RC-01–RC-09, повторить проверки на окончательном commit, приложить результаты staging,
   backup restore и review. Только bugfix/docs/version/deployment config в release-ветке.
3. Проверить `git status` и `git branch --show-current`. Для публикации кандидата:

```bash
git switch release/0.1.0
git status
git push -u origin release/0.1.0
```

4. Создать **Draft PR `release/0.1.0 → main`** с текстом из [release notes](RELEASE_NOTES.md).
   Push release-ветки сам по себе не запускает текущий workflow: CI запускается на PR в main/develop.
5. Дождаться всех обязательных jobs, отсутствия конфликтов и закрытия review findings. Пока решение
   NO-GO, PR остаётся Draft. Не обходить failing checks и не публиковать стабильный тег.
6. После письменной приёмки release owner пользователь самостоятельно выполняет merge PR в `main`,
   затем синхронизирует release-исправления обратно в `develop` отдельным PR с CI.
7. Только после проверки merge commit пользователь создаёт тег `v0.1.0` на принятом `main` commit
   и GitHub Release по этим notes. Локальные и remote feature/release-ветки сохранить. Force push не нужен.

Ориентиры: [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[публикация static](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/) и
[PostgreSQL backup](https://www.postgresql.org/docs/16/backup-dump.html). Они не заменяют проверку
конкретного окружения и политики обработки пользовательских данных.
