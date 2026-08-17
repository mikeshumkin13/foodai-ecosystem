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
