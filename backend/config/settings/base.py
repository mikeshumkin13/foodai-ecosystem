from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import dj_database_url
from django.core.exceptions import ImproperlyConfigured


def get_env(name: str, *, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        msg = f"Environment variable {name} is required."
        raise ImproperlyConfigured(msg)
    return value


def get_env_bool(name: str, *, default: bool | None = None) -> bool:
    raw_default = None if default is None else str(default).lower()
    value = get_env(name, default=raw_default).strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_env_int(name: str, *, default: int | None = None) -> int:
    raw_default = None if default is None else str(default)
    return int(get_env(name, default=raw_default))


def get_env_list(name: str, *, default: str | None = None) -> list[str]:
    value = get_env(name, default=default)
    return [item.strip() for item in value.split(",") if item.strip()]


BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent

SECRET_KEY = get_env("DJANGO_SECRET_KEY")
DEBUG = get_env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = get_env_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASE_URL = get_env("DATABASE_URL")
DB_CONN_MAX_AGE = get_env_int("DJANGO_DB_CONN_MAX_AGE", default=60)
DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=DB_CONN_MAX_AGE),
}
REDIS_URL = get_env("REDIS_URL", default="")

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = get_env("DJANGO_LANGUAGE_CODE", default="ru")
LANGUAGES = [
    ("ru", "Russian"),
    ("en", "English"),
]
TIME_ZONE = get_env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = get_env("DJANGO_STATIC_URL", default="static/")
STATIC_ROOT = get_env("DJANGO_STATIC_ROOT", default=str(ROOT_DIR / "staticfiles"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = get_env_list("DJANGO_CORS_ALLOWED_ORIGINS", default="")
CSRF_TRUSTED_ORIGINS = get_env_list("DJANGO_CSRF_TRUSTED_ORIGINS", default="")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FoodAI Ecosystem API",
    "DESCRIPTION": "Backend API for FoodAI Ecosystem.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
