PYTHON ?= .venv/bin/python
DOCKER_COMPOSE ?= docker compose
PNPM ?= $(shell if command -v pnpm >/dev/null 2>&1; then command -v pnpm; elif [ -x "$(HOME)/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm" ]; then printf "%s" "$(HOME)/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm"; else printf "%s" "pnpm"; fi)
BUNDLED_NODE_BIN = $(HOME)/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin
FRONTEND_ENV = PATH=$(if $(wildcard $(BUNDLED_NODE_BIN)/node),$(BUNDLED_NODE_BIN):,)$$PATH
LOCAL_CHECK_ENV = DJANGO_SECRET_KEY=local-check-only DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000 DATABASE_URL=sqlite:///backend/db.sqlite3 REDIS_URL=

.PHONY: venv install test lint format typecheck django-check check frontend-install frontend-lint frontend-typecheck frontend-test frontend-build frontend-check ensure-env dev-build dev-up dev-up-detached dev-down dev-logs dev-test dev-health

venv:
	python3 -m venv .venv

install: venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pip install -e "services/vision[dev]"
	cd frontend && $(FRONTEND_ENV) $(PNPM) install --frozen-lockfile

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

check: lint typecheck django-check test frontend-check

frontend-install:
	cd frontend && $(FRONTEND_ENV) $(PNPM) install --frozen-lockfile

frontend-lint:
	cd frontend && $(FRONTEND_ENV) $(PNPM) lint

frontend-typecheck:
	cd frontend && $(FRONTEND_ENV) $(PNPM) typecheck

frontend-test:
	cd frontend && $(FRONTEND_ENV) $(PNPM) test

frontend-build:
	cd frontend && $(FRONTEND_ENV) $(PNPM) build

frontend-check:
	cd frontend && $(FRONTEND_ENV) $(PNPM) check

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
