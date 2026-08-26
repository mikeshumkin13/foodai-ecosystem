# FoodAI Frontend

Next.js + TypeScript клиент FoodAI Ecosystem.

## Локальный запуск

```bash
cd frontend
pnpm install
pnpm dev
```

По умолчанию frontend обращается к backend по `http://localhost:8000`.

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev
```

## Проверки

```bash
pnpm lint
pnpm typecheck
pnpm build
pnpm check
```

## Auth и CSRF

Web-клиент использует backend session-cookie схему:

- access token не хранится в `localStorage`;
- запросы к API выполняются с `credentials: "include"`;
- перед unsafe request frontend получает CSRF через `GET /api/v1/auth/csrf/`;
- CSRF отправляется в заголовке `X-CSRFToken`.

Регистрация не открывает защищённые страницы до активации аккаунта. Пользователь получает экран
ожидания письма и может повторить отправку; route `/auth/email/verify` подтверждает одноразовую
ссылку backend. `AuthSessionProvider` проверяет текущего пользователя, продлевает активную Django
session через `/auth/refresh/`, централизованно обрабатывает истёкшую сессию и предоставляет logout.
После ротации session/CSRF frontend очищает только in-memory CSRF cache и получает актуальный token
перед следующим unsafe request.

API-вызовы должны идти через `src/lib/api`, а презентационные UI components не должны содержать бизнес-логику API.

## Food Scan UI

`/scan` реализует MVP flow:

- выбор файла или mobile camera input;
- upload через `POST /api/v1/food-scans/`;
- polling `GET /api/v1/food-scans/{id}/results/`;
- карточки detected food с confidence, `≈` estimated grams, диапазоном uncertainty и КБЖУ;
- исправление массы и продукта;
- удаление ошибочного item и добавление отсутствующего продукта;
- confirmation через `POST /api/v1/food-scans/{id}/confirm/`;
- переход в `/diary?date=YYYY-MM-DD`.

`/diary` загружает дневную агрегацию через `GET /api/v1/diary/day/?date=` и показывает созданные после confirmation записи.

## Dashboard и Diary

`/dashboard` показывает сводку текущего дня:

- calories consumed;
- calorie target как MVP-ориентир из текущего nutrition profile;
- protein, fat, carbohydrates;
- meals today;
- быстрые действия для ручного добавления еды и Scan.

`/diary` поддерживает календарную дату, список приёмов пищи, ручное создание еды из nutrition catalog, редактирование и удаление собственных meals.

Ручной diary flow обязателен: пользователь должен иметь возможность вести питание даже при недоступном AI Scan, Vision service или Celery.

## Nutrition Profile

`/profile` загружает профиль через owner-only `GET /api/v1/accounts/nutrition-profiles/me/` и
сохраняет изменения через detail `PATCH`. Первое сохранение требует явного consent. UI использует
privacy-friendly age category и не смешивает dietary preferences с аллергиями или медицинскими
ограничениями. Backend хранит рост и массу в `cm/kg`; при выборе imperial units форма преобразует
значения на API boundary.

## AI Nutrition Coach

`/coach` использует `GET/PATCH /api/v1/ai/coach/settings/` и
`POST /api/v1/ai/coach/ask/`. Ответ отображается по schema
`ai_nutrition_coach_response_v1`: answer, suggestions, nutrition notes, warnings и safety state.
История выключена по умолчанию. Даже после consent пользователь отдельно выбирает сохранение
конкретного запроса и ответа; frontend не передаёт email, UUID, фотографии или полную историю.

## Privacy & Data

`/privacy` реализует owner-only Privacy Center:

- summary категорий данных;
- consent toggles для model improvement и отдельного food photo training consent;
- JSON export собственных данных;
- удаление отдельных food photos;
- удаление AI chat history;
- удаление аккаунта с текущим паролем.

Privacy UI использует `src/lib/api/privacy.ts`; unsafe requests проходят через общий CSRF/session-cookie client.
