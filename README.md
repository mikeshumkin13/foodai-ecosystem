# FoodAI Ecosystem

FoodAI Ecosystem — коммерческий продукт для ведения питания и физической активности с компьютерным зрением и AI-помощниками.

AI является помощником, а не врачом, лицензированным нутрициологом, психологом или системой медицинских решений.

## Основной сценарий

1. Пользователь фотографирует еду.
2. Система распознаёт продукты и ингредиенты.
3. Система оценивает порцию, массу, калории, БЖУ и другие нутриенты.
4. Пользователь подтверждает или исправляет результат.
5. Данные сохраняются в дневник.
6. Система анализирует дневной рацион.

## Языки

Основные языки проекта и пользовательского продукта: русский (`ru`) и английский (`en`).

## Структура

```text
foodai-ecosystem/
├── backend/
├── frontend/
├── services/
│   └── vision/
├── infra/
├── docs/
├── scripts/
├── .github/
├── AGENTS.md
├── .editorconfig
├── .env.example
├── .gitignore
└── README.md
```

## Целевой стек

- Backend: Python, Django, Django REST Framework, PostgreSQL, Redis, Celery.
- Vision: Python, FastAPI, OpenCV; CV/ML-библиотеки добавляются только по необходимости.
- Frontend: Next.js, TypeScript, responsive PWA.
- Infrastructure: Docker, Docker Compose, GitHub Actions.
- Storage: приватное S3-compatible object storage; локально допустим MinIO.

## Текущее состояние

Создан только фундамент репозитория. Django, Next.js и FastAPI в этом задании не устанавливаются.

