PYTHON ?= .venv/bin/python
LOCAL_CHECK_ENV = DJANGO_SECRET_KEY=local-check-only DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000 DATABASE_URL=sqlite:///backend/db.sqlite3

.PHONY: venv install test lint format typecheck django-check check

venv:
	python3 -m venv .venv

install: venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

typecheck:
	$(LOCAL_CHECK_ENV) $(PYTHON) -m mypy backend

django-check:
	$(LOCAL_CHECK_ENV) $(PYTHON) backend/manage.py check --settings=config.settings.local

check: lint typecheck django-check test
