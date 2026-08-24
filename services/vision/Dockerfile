FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system foodai \
    && useradd --system --gid foodai --home-dir /app foodai

COPY services/vision/pyproject.toml ./services/vision/pyproject.toml
COPY services/vision/vision_service ./services/vision/vision_service
COPY services/vision/scripts ./services/vision/scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.6.0+cpu" \
    && python -m pip install -e "services/vision"

ENV HF_HOME=/tmp/huggingface

USER foodai

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "vision_service.main:app", "--app-dir", "services/vision", "--host", "0.0.0.0", "--port", "8001"]
