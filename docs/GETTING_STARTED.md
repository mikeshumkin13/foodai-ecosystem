# Запуск и использование FoodAI Ecosystem

Для локальной версии `0.1.0` / release candidate. Обновлено: 2026-09-16.
Это инструкция для вашего компьютера, **не инструкция публикации в интернете**.
Production пока имеет незакрытые условия из [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

## 1. Что открыть и установить

Откройте в PyCharm через File → Open именно папку
`/Users/a12345/Documents/fitnes/foodai-ecosystem`, не родительскую `fitnes`.
Команды можно вводить в Terminal на Mac или во вкладке Terminal в PyCharm: результат одинаков.
В терминале сначала перейдите в корень проекта:

```bash
cd /Users/a12345/Documents/fitnes/foodai-ecosystem
git status
git branch --show-current
```

Для этого кандидата нужна ветка `release/0.1.0`. При чистом working tree:

```bash
git switch release/0.1.0
```

Если Git сообщает о локальных изменениях, не используйте reset/force checkout: сначала сохраните
свою работу. Не выполняйте `git pull origin develop` из release-ветки: это смешает ветки.

Необходимы Docker Desktop с Compose v2, Node.js 22.13+ и pnpm версии из `frontend/package.json`
(`11.19.0` для этого RC). Python 3.12 нужен только для локальных Python-проверок/IDE;
backend, PostgreSQL, Redis, Celery и Vision запускаются в Docker.

```bash
docker version
docker compose version
node --version
pnpm --version
```

Если pnpm отсутствует, при уже установленном Node/npm:

```bash
npm install --global pnpm@11.19.0
```

Первый запуск скачивает Docker images, npm/Python dependencies и веса Vision-моделей.
Нужны интернет, свободное место и достаточная память Docker. CPU inference может быть медленным.

## 2. Настроить локальный environment

Существующий `.env` **не перезаписывать**. Если его нет:

```bash
test -f .env || cp .env.example .env
```

Откройте `.env` в редакторе. Для локального тестирования проверьте следующие значения:

```dotenv
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000
DJANGO_CORS_ALLOW_CREDENTIALS=true
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:3000
FRONTEND_BASE_URL=http://localhost:3000
BACKEND_PORT=127.0.0.1:8000
DJANGO_RUN_MIGRATIONS=true
DJANGO_EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend
AI_COACH_PROVIDER=mock
VISION_SERVICE_TIMEOUT_SECONDS=60.0
CELERY_TASK_SOFT_TIME_LIMIT_SECONDS=90
CELERY_TASK_TIME_LIMIT_SECONDS=120
```

`BACKEND_PORT=127.0.0.1:8000` ограничивает Compose port mapping вашим компьютером.
Остальные обязательные параметры, включая `DATABASE_URL`, `REDIS_URL`, пути storage и pinned
model revisions, берите из `.env.example`. Не меняйте существующий `POSTGRES_VOLUME_NAME`:
иначе можно случайно открыть другую пустую БД. Изменение пароля в `.env` само по себе не меняет
пароль PostgreSQL в уже созданном volume.

`mock` позволяет проверить Coach без платного LLM API. Настоящий LLM требует отдельно настроенного
provider account/ключа, проверки доступности модели и бюджета. Не помещайте ключи в frontend
`NEXT_PUBLIC_*`, Git, чат или screenshots. `.env.example` содержит только локальные примеры;
для production они непригодны. Не используйте console email backend: одноразовые ссылки не должны
попадать в логи приложения.

## 3. Запустить backend и зависимости

Запустите Docker Desktop и дождитесь готовности, затем из корня проекта:

```bash
docker compose --env-file .env up --build -d
docker compose --env-file .env ps
```

Ожидаются пять работающих сервисов: `postgres`, `redis`, `backend`, `vision`, `celery_worker`.
На первом старте Vision загружает и прогревает модели, поэтому `starting` может сохраняться
дольше остальных. Worker ждёт готовности Vision. Не повторяйте upload много раз во время прогрева.

```bash
curl -fsS http://localhost:8000/api/v1/health/
docker compose --env-file .env exec backend python backend/manage.py migrate --check
```

Health должен ответить HTTP 200 с `status: ok`; migration check завершиться без ошибки.
Migrations при локальном старте запускает entrypoint. Не удаляйте volumes и не применяйте `--fake`
при ошибке. Для legacy PostgreSQL см. [порядок recovery](../scripts/postgres-volume-recovery.sh)
и [QA report](MVP_QA_REPORT.md).

Если это новая пустая локальная база, один раз загрузите небольшой демонстрационный каталог:

```bash
docker compose --env-file .env exec backend python backend/manage.py loaddata demo_nutrition_catalog
```

Не запускайте fixture повторно над отредактированным каталогом: совпадающие fixture IDs могут
перезаписать изменения. Demo dataset мал и не заменяет полноценную проверенную nutrition database.

## 4. Запустить frontend

Откройте второй терминал:

```bash
cd /Users/a12345/Documents/fitnes/foodai-ecosystem/frontend
pnpm install --frozen-lockfile
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev --hostname 127.0.0.1 --port 3000
```

Откройте [приложение](http://localhost:3000). Терминал frontend должен оставаться работающим.
Если порт занят, сначала выясните, какой процесс его использует; при смене frontend-порта нужно
согласованно изменить backend CORS/CSRF/FRONTEND_BASE_URL и пересоздать backend. Не смешивайте
`localhost` и `127.0.0.1` в адресах браузера и API: cookies и origins должны совпадать со схемой.

Адреса:

| Что | Адрес |
|---|---|
| Регистрация / вход | `http://localhost:3000/register`, `/login` |
| Сводка дня | `http://localhost:3000/dashboard` |
| Дневник | `http://localhost:3000/diary` |
| Фото блюда | `http://localhost:3000/scan` |
| Профиль | `http://localhost:3000/profile` |
| Nutrition Coach | `http://localhost:3000/coach` |
| Privacy & Data | `http://localhost:3000/privacy` |
| API docs | `http://localhost:8000/api/v1/docs/` |
| Django Admin | `http://localhost:8000/admin/` |

## 5. Зарегистрировать тестового пользователя

1. Откройте `/register`, укажите отдельный тестовый email и пароль, не используемый в других сервисах.
2. После регистрации появится ожидание email verification. Это ожидаемо: default locmem backend
   не отправляет письмо в настоящий почтовый ящик; повторная отправка этого не исправляет.
3. Только для собственного локального тестового аккаунта разработчик может имитировать получение
   одноразовой ссылки через Django shell. Это привилегированная QA-операция, **не проверка владения
   email и не способ активации пользователей в production**.

Из корня проекта:

```bash
docker compose --env-file .env exec backend python backend/manage.py shell
```

В открывшейся Python-консоли выполните:

```python
from django.conf import settings
from accounts.models import User
from accounts.auth_tokens import issue_email_verification_token, consume_email_verification_token

assert settings.DEBUG and settings.SETTINGS_MODULE == "config.settings.local"
assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"
email = input("Email вашего локального тестового аккаунта: ").strip().lower()
user = User.objects.get(email=email, is_active=False)
issued = issue_email_verification_token(user)
activated = consume_email_verification_token(issued.token_id, issued.token)
assert activated is not None
print("Локальный тестовый аккаунт подтвержден. Теперь можно войти через /login.")
exit()
```

Пароль и token не выводятся. Если аккаунт уже активен, условие `is_active=False` не найдёт его:
просто войдите через `/login`. Для production требуется настоящая доставка письма и переход по
одноразовой ссылке в интерфейсе; ручная QA-операция выше там не применяется.

## 6. Пользоваться приложением

### Профиль и dashboard

Откройте `/profile`, задайте цель, рост, массу, age category, активность, единицы и dietary
preferences. Сохранение требует явного consent. Не вносите диагнозы в свободный текст.
На `/dashboard` будут дневные калории, БЖУ, число приёмов пищи и оценочный calorie target.
Target не является медицинским назначением; без данных профиля он может отсутствовать.

### Ручной дневник без AI

1. Откройте `/diary` и выберите дату.
2. Добавьте приём пищи, его тип/время, найдите продукт в каталоге и укажите граммы.
3. Добавьте ещё продукты при необходимости и сохраните.
4. Проверьте КБЖУ и дневную сумму; измените массу или удалите тестовый meal.

Этот способ работает без Vision/Celery. Если поиск пуст, проверьте наличие demo catalog или
попросите content manager наполнить каталог. Произвольный неизвестный продукт нельзя считать
автоматически нутриентно достоверным.

### Scan фотографии

1. Дождитесь `healthy` для Vision/worker. Откройте `/scan`, выберите JPEG/PNG до 5 MiB и 20 млн pixels
   при стандартных лимитах. На совместимом мобильном браузере доступен camera input.
2. После загрузки дождитесь результатов. Фото ещё не создаёт запись в Diary.
3. Проверьте каждую карточку: продукт, confidence, оценочную массу/диапазон и КБЖУ.
4. Исправьте продукт и граммы, удалите ложные detections, добавьте пропущенное из каталога.
5. Подтвердите состав. Только после этого создаётся Meal и открывается Diary.

Оценка по RGB может существенно ошибаться; при необходимости используйте кухонные весы.
Низкий confidence не означает безопасную или точную оценку. Повторное подтверждение одного scan
не должно создавать дубликат. При недоступном Vision воспользуйтесь ручным дневником.

### Coach и приватность

В `/coach` можно запросить объяснение дневного баланса. При `AI_COACH_PROVIDER=mock` ответ
демонстрационный, а не настоящий LLM-анализ. История по умолчанию выключена: хранение требует
consent и отдельного выбора сохранения ответа. AI не заменяет врача или лечение.

В `/privacy` доступны категории данных, JSON export, настройки согласий, удаление фото и истории.
Фотографии по умолчанию не разрешены для обучения. Удаление аккаунта требует текущего пароля.
Проверяйте необратимые действия только на специально созданных тестовых данных. Export содержит
приватные данные: не публикуйте его. Export не заменяет backup системы.

### Django Admin

Только для начальной локальной настройки:

```bash
docker compose --env-file .env exec backend python backend/manage.py createsuperuser
```

Пароль вводится интерактивно. Superuser имеет технический полный доступ: не используйте его для
повседневного дневника. Support/content manager видят только разрешённые модели; наличие staff
само по себе не заменяет permissions. Матрица ролей: [SECURITY.md](SECURITY.md).

## 7. Проверить перед использованием

- Создать два тестовых аккаунта в разных профилях браузера. Meals, scans и profiles второго
  не должны быть видны первому даже при известном UUID.
- Создать meal из двух продуктов и проверить сумму; изменение каталога не должно менять старую запись.
- Проверить scan → correction → confirm → diary и ручное добавление без Scan.
- Проверить logout, export и удаление только собственных тестовых данных.
- Не считать показанный confidence доказательством точности или медицинской безопасности.

Полные автоматические проверки, при установленном Python 3.12 и локальном virtualenv:

```bash
cd /Users/a12345/Documents/fitnes/foodai-ecosystem
test -x .venv/bin/python || python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip install -e 'services/vision[dev]'
make check
cd frontend
pnpm exec playwright install chromium
pnpm test:e2e
```

Не пересоздавайте исправное существующее `.venv` без необходимости. Для PyCharm выберите existing
interpreter `/Users/a12345/Documents/fitnes/foodai-ecosystem/.venv/bin/python`.
Тесты используют отдельную БД; не подставляйте production credentials.

## 8. Остановка, повторный запуск и ошибки

Frontend: `Ctrl+C` в его терминале. Backend и зависимости из корня:

```bash
docker compose --env-file .env stop
```

Повторный запуск без пересборки:

```bash
docker compose --env-file .env up -d
```

Frontend запускается отдельно командой из шага 4. Не используйте `down -v`: это удаляет volumes
с данными. Перед обновлением делайте согласованный backup, см. release checklist.

| Симптом | Что сделать |
|---|---|
| Cannot connect to Docker daemon | Открыть Docker Desktop, дождаться Engine running, повторить `docker version` |
| Нет нужной ветки в PyCharm | Проверить корень Git; открыть `foodai-ecosystem`, выполнить `git fetch origin`, посмотреть `git branch -a` |
| `tsc`/`next`/`playwright` not found | Установка зависимостей не завершена; повторить `pnpm install --frozen-lockfile`, не менять lockfile вслепую |
| Не пришло письмо / login не проходит после регистрации | Default locmem не отправляет email; для локального QA выполнить шаг 5 |
| 403 CSRF / Failed to fetch | Проверить backend health, одинаковый hostname, CORS/CSRF origins; после правки `.env` пересоздать backend |
| Пустой каталог | Для новой тестовой БД один раз загрузить demo fixture; не перезаписывать рабочий каталог |
| Scan долго processing / failed | Проверить Vision/worker health и загрузку моделей; после устранения причины один раз retry, либо ручной дневник |
| Coach недоступен | Проверить выбранный provider; для бесплатного локального QA выбрать mock, не вставлять ключ в UI |
| Migration error / старая база | Остановиться, сохранить backup и изучить recovery; не удалять volume и не применять `--fake` |

Диагностика инфраструктуры:

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=50 backend celery_worker vision
```

Не публикуйте полный `.env`, `docker inspect` или конфигурацию с подставленными секретами.
При обращении за помощью достаточно названия сервиса, времени, безопасного кода ошибки и
`X-Request-ID`. Перед передачей журналов удаляйте чувствительные значения.
