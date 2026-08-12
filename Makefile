PYTHON ?= .venv/bin/python
DOCKER_COMPOSE ?= docker compose
LOCAL_CHECK_ENV = DJANGO_SECRET_KEY=local-check-only DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000 DATABASE_URL=sqlite:///backend/db.sqlite3 REDIS_URL=

.PHONY: venv install test lint format typecheck django-check check ensure-env dev-build dev-up dev-up-detached dev-down dev-logs dev-test dev-health

venv:
	python3 -m venv .venv

install: venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pip install -e "services/vision[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

typecheck:
	$(LOCAL_CHECK_ENV) $(PYTHON) -m mypy backend services/vision

django-check:
	$(LOCAL_CHECK_ENV) $(PYTHON) backend/manage.py check --settings=config.settings.local

check: lint typecheck django-check test

ensure-env:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Создан .env из .env.example"; fi

dev-build: ensure-env
	$(DOCKER_COMPOSE) --env-file .env build

dev-up: ensure-env
	$(DOCKER_COMPOSE) --env-file .env up --build

dev-up-detached: ensure-env
	$(DOCKER_COMPOSE) --env-file .env up --build -d

dev-down:
	$(DOCKER_COMPOSE) --env-file .env down

dev-logs:
	$(DOCKER_COMPOSE) --env-file .env logs -f

dev-test: ensure-env
	$(DOCKER_COMPOSE) --env-file .env run --rm backend python -m pytest

dev-health:
	curl -fsS http://localhost:$${BACKEND_PORT:-8000}/api/v1/health/
