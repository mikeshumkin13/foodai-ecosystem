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


def get_env_float(name: str, *, default: float | None = None) -> float:
    raw_default = None if default is None else str(default)
    return float(get_env(name, default=raw_default))


def get_env_list(name: str, *, default: str | None = None) -> list[str]:
    value = get_env(name, default=default)
    return [item.strip() for item in value.split(",") if item.strip()]


BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent

SECRET_KEY = get_env("DJANGO_SECRET_KEY")
DEBUG = get_env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = get_env_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "audit",
    "accounts",
    "nutrition",
    "diary",
    "food_scans",
    "ai_coach",
    "fitness",
    "wellbeing",
    "privacy",
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
    "audit.middleware.CorrelationIdMiddleware",
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
CELERY_BROKER_URL = get_env("CELERY_BROKER_URL", default=REDIS_URL or "memory://")
CELERY_RESULT_BACKEND = get_env(
    "CELERY_RESULT_BACKEND",
    default=CELERY_BROKER_URL if CELERY_BROKER_URL != "memory://" else "cache+memory://",
)
CELERY_TASK_ALWAYS_EAGER = get_env_bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = get_env_bool("CELERY_TASK_EAGER_PROPAGATES", default=True)
CELERY_TASK_TIME_LIMIT = get_env_int("CELERY_TASK_TIME_LIMIT_SECONDS", default=60)
CELERY_TASK_SOFT_TIME_LIMIT = get_env_int("CELERY_TASK_SOFT_TIME_LIMIT_SECONDS", default=30)
CELERY_WORKER_PREFETCH_MULTIPLIER = get_env_int("CELERY_WORKER_PREFETCH_MULTIPLIER", default=1)
FOOD_SCAN_ANALYSIS_MAX_RETRIES = get_env_int("FOOD_SCAN_ANALYSIS_MAX_RETRIES", default=2)
FOOD_SCAN_ANALYSIS_RETRY_BACKOFF_SECONDS = get_env_int(
    "FOOD_SCAN_ANALYSIS_RETRY_BACKOFF_SECONDS",
    default=5,
)

AUTH_USER_MODEL = "accounts.User"
AUTH_EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS = get_env_int(
    "AUTH_EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS",
    default=60 * 60 * 24,
)
AUTH_PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS = get_env_int(
    "AUTH_PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS",
    default=60 * 60,
)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

EMAIL_BACKEND = get_env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.locmem.EmailBackend",
)
DEFAULT_FROM_EMAIL = get_env("DJANGO_DEFAULT_FROM_EMAIL", default="security@foodai.local")
FRONTEND_BASE_URL = get_env("FRONTEND_BASE_URL", default="http://localhost:3000")

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

FOOD_SCAN_ALLOWED_FORMATS = tuple(
    item.upper() for item in get_env_list("FOOD_SCAN_ALLOWED_FORMATS", default="JPEG,PNG")
)
FOOD_SCAN_MAX_UPLOAD_BYTES = get_env_int("FOOD_SCAN_MAX_UPLOAD_BYTES", default=5 * 1024 * 1024)
FOOD_SCAN_MAX_IMAGE_PIXELS = get_env_int("FOOD_SCAN_MAX_IMAGE_PIXELS", default=20_000_000)
FOOD_SCAN_PRIVATE_STORAGE_BACKEND = get_env(
    "FOOD_SCAN_PRIVATE_STORAGE_BACKEND",
    default="local",
)
FOOD_SCAN_PRIVATE_MEDIA_ROOT = get_env(
    "FOOD_SCAN_PRIVATE_MEDIA_ROOT",
    default=str(ROOT_DIR / "local_uploads" / "private"),
)
VISION_SERVICE_URL = get_env("VISION_SERVICE_URL", default="http://localhost:8001")
VISION_SERVICE_TIMEOUT_SECONDS = get_env_float("VISION_SERVICE_TIMEOUT_SECONDS", default=2.0)
AI_COACH_PROVIDER = get_env("AI_COACH_PROVIDER", default="mock")
AI_COACH_PROVIDER_TIMEOUT_SECONDS = get_env_float(
    "AI_COACH_PROVIDER_TIMEOUT_SECONDS",
    default=10.0,
)
FITNESS_COACH_PROVIDER = get_env("FITNESS_COACH_PROVIDER", default="mock")
FITNESS_COACH_PROVIDER_TIMEOUT_SECONDS = get_env_float(
    "FITNESS_COACH_PROVIDER_TIMEOUT_SECONDS",
    default=10.0,
)
WELLBEING_ASSISTANT_PROVIDER = get_env("WELLBEING_ASSISTANT_PROVIDER", default="mock")
WELLBEING_ASSISTANT_PROVIDER_TIMEOUT_SECONDS = get_env_float(
    "WELLBEING_ASSISTANT_PROVIDER_TIMEOUT_SECONDS",
    default=10.0,
)

CORS_ALLOWED_ORIGINS = get_env_list("DJANGO_CORS_ALLOWED_ORIGINS", default="")
CORS_ALLOW_CREDENTIALS = get_env_bool("DJANGO_CORS_ALLOW_CREDENTIALS", default=False)
CSRF_TRUSTED_ORIGINS = get_env_list("DJANGO_CSRF_TRUSTED_ORIGINS", default="")
CSRF_COOKIE_HTTPONLY = get_env_bool("DJANGO_CSRF_COOKIE_HTTPONLY", default=False)
CSRF_COOKIE_NAME = get_env("DJANGO_CSRF_COOKIE_NAME", default="csrftoken")
CSRF_COOKIE_SAMESITE = get_env("DJANGO_CSRF_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_AGE = get_env_int("DJANGO_SESSION_COOKIE_AGE", default=60 * 60 * 24 * 14)
SESSION_COOKIE_HTTPONLY = get_env_bool("DJANGO_SESSION_COOKIE_HTTPONLY", default=True)
SESSION_COOKIE_NAME = get_env("DJANGO_SESSION_COOKIE_NAME", default="sessionid")
SESSION_COOKIE_SAMESITE = get_env("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")
SESSION_SAVE_EVERY_REQUEST = get_env_bool("DJANGO_SESSION_SAVE_EVERY_REQUEST", default=True)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": get_env("AUTH_REGISTER_THROTTLE_RATE", default="5/hour"),
        "auth_login": get_env("AUTH_LOGIN_THROTTLE_RATE", default="5/minute"),
        "auth_logout": get_env("AUTH_LOGOUT_THROTTLE_RATE", default="20/minute"),
        "auth_refresh": get_env("AUTH_REFRESH_THROTTLE_RATE", default="20/minute"),
        "auth_email_verification": get_env(
            "AUTH_EMAIL_VERIFICATION_THROTTLE_RATE",
            default="10/hour",
        ),
        "auth_password_reset": get_env("AUTH_PASSWORD_RESET_THROTTLE_RATE", default="5/hour"),
        "auth_password_change": get_env("AUTH_PASSWORD_CHANGE_THROTTLE_RATE", default="5/hour"),
        "ai_coach_ask": get_env("AI_COACH_ASK_THROTTLE_RATE", default="30/hour"),
        "fitness_coach": get_env("FITNESS_COACH_THROTTLE_RATE", default="30/hour"),
        "wellbeing_assistant": get_env("WELLBEING_ASSISTANT_THROTTLE_RATE", default="30/hour"),
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FoodAI Ecosystem API",
    "DESCRIPTION": "Backend API for FoodAI Ecosystem.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "MealItemSourceEnum": "diary.models.MealItem.Source",
        "FoodScanStatusEnum": "food_scans.models.FoodScan.Status",
        "FoodScanDetectedItemSourceEnum": "food_scans.models.FoodScanDetectedItem.Source",
        "WorkoutPlanGoalEnum": "fitness.models.WorkoutPlan.Goal",
        "WorkoutPlanExperienceLevelEnum": "fitness.models.WorkoutPlan.ExperienceLevel",
        "WorkoutPlanStatusEnum": "fitness.models.WorkoutPlan.Status",
        "WorkoutExerciseIntensityEnum": "fitness.models.WorkoutExercise.Intensity",
    },
}
