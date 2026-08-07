FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system foodai \
    && useradd --system --gid foodai --home-dir /app foodai

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY scripts ./scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[dev]"

USER foodai

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "scripts/backend-entrypoint.sh"]
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000", "--settings=config.settings.local"]
