from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.core.checks import CheckMessage, Critical, Tags, Warning, register

INSECURE_SECRET_KEYS = {
    "change-me-local-only",
    "local-ci-only",
    "local-check-only",
    "test-secret-key-for-pytest-only",
}

SECURE_SAMESITE_VALUES = {"lax", "strict", "none"}


@register(Tags.security, deploy=True)
def check_security_configuration(
    app_configs: Any,
    **kwargs: Any,
) -> list[CheckMessage]:
    if not _is_production_runtime():
        return []

    messages: list[CheckMessage] = []
    messages.extend(_check_debug_and_secret())
    messages.extend(_check_hosts_and_origins())
    messages.extend(_check_cookies())
    messages.extend(_check_security_headers())
    messages.extend(_check_api_defaults())
    messages.extend(_check_private_storage())
    return messages


def _is_production_runtime() -> bool:
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip()
    return app_env == "production" or settings_module.endswith(".production")


def _check_debug_and_secret() -> list[CheckMessage]:
    messages: list[CheckMessage] = []

    if settings.DEBUG:
        messages.append(
            Critical(
                "Production must not run with DEBUG enabled.",
                hint="Set DJANGO_DEBUG=false for production.",
                id="foodai_security.E001",
            )
        )

    secret_key = str(settings.SECRET_KEY)
    if len(secret_key) < 32 or secret_key in INSECURE_SECRET_KEYS:
        messages.append(
            Critical(
                "Production SECRET_KEY is missing, too short, or uses a documented local value.",
                hint="Generate a unique high-entropy DJANGO_SECRET_KEY outside the repository.",
                id="foodai_security.E002",
            )
        )

    return messages


def _check_hosts_and_origins() -> list[CheckMessage]:
    messages: list[CheckMessage] = []

    allowed_hosts = _as_list(settings.ALLOWED_HOSTS)
    if not allowed_hosts or _contains_wildcard(allowed_hosts):
        messages.append(
            Critical(
                "Production ALLOWED_HOSTS must be an explicit allowlist.",
                hint="Set DJANGO_ALLOWED_HOSTS to concrete production hostnames.",
                id="foodai_security.E003",
            )
        )

    cors_allowed_origins = _as_list(getattr(settings, "CORS_ALLOWED_ORIGINS", []))
    cors_allow_all = bool(getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False))
    if cors_allow_all or _contains_wildcard(cors_allowed_origins):
        messages.append(
            Critical(
                "Production CORS must not allow wildcard origins.",
                hint="Use DJANGO_CORS_ALLOWED_ORIGINS with exact trusted HTTPS origins.",
                id="foodai_security.E004",
            )
        )

    insecure_cors_origins = [origin for origin in cors_allowed_origins if origin.startswith("http://")]
    if insecure_cors_origins:
        messages.append(
            Critical(
                "Production CORS origins must use HTTPS.",
                hint="Remove HTTP origins from DJANGO_CORS_ALLOWED_ORIGINS.",
                id="foodai_security.E005",
            )
        )

    csrf_trusted_origins = _as_list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []))
    if _contains_wildcard(csrf_trusted_origins):
        messages.append(
            Critical(
                "Production CSRF trusted origins must not use wildcards.",
                hint="Set DJANGO_CSRF_TRUSTED_ORIGINS to exact trusted HTTPS origins.",
                id="foodai_security.E006",
            )
        )

    insecure_csrf_origins = [
        origin for origin in csrf_trusted_origins if origin.startswith("http://")
    ]
    if insecure_csrf_origins:
        messages.append(
            Critical(
                "Production CSRF trusted origins must use HTTPS.",
                hint="Remove HTTP origins from DJANGO_CSRF_TRUSTED_ORIGINS.",
                id="foodai_security.E007",
            )
        )

    frontend_base_url = str(getattr(settings, "FRONTEND_BASE_URL", ""))
    if frontend_base_url.startswith("http://"):
        messages.append(
            Critical(
                "Production FRONTEND_BASE_URL must use HTTPS.",
                hint="Set FRONTEND_BASE_URL to the public HTTPS frontend origin.",
                id="foodai_security.E008",
            )
        )

    return messages


def _check_cookies() -> list[CheckMessage]:
    messages: list[CheckMessage] = []

    if not settings.SESSION_COOKIE_SECURE:
        messages.append(
            Critical(
                "Production session cookie must be Secure.",
                hint="Set DJANGO_SESSION_COOKIE_SECURE=true.",
                id="foodai_security.E009",
            )
        )
    if not settings.CSRF_COOKIE_SECURE:
        messages.append(
            Critical(
                "Production CSRF cookie must be Secure.",
                hint="Set DJANGO_CSRF_COOKIE_SECURE=true.",
                id="foodai_security.E010",
            )
        )
    if not settings.SESSION_COOKIE_HTTPONLY:
        messages.append(
            Critical(
                "Production session cookie must be HttpOnly.",
                hint="Set DJANGO_SESSION_COOKIE_HTTPONLY=true.",
                id="foodai_security.E011",
            )
        )

    messages.extend(_check_samesite("SESSION_COOKIE_SAMESITE", settings.SESSION_COOKIE_SAMESITE))
    messages.extend(_check_samesite("CSRF_COOKIE_SAMESITE", settings.CSRF_COOKIE_SAMESITE))
    return messages


def _check_samesite(setting_name: str, value: object) -> list[CheckMessage]:
    normalized = str(value).strip().lower()
    if normalized not in SECURE_SAMESITE_VALUES:
        return [
            Critical(
                f"Production {setting_name} must be Lax, Strict, or None.",
                hint=f"Review {setting_name}; Lax is the current default for the web client.",
                id="foodai_security.E012",
            )
        ]
    return []


def _check_security_headers() -> list[CheckMessage]:
    messages: list[CheckMessage] = []

    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        messages.append(
            Critical(
                "Production must redirect HTTP to HTTPS.",
                hint="Set DJANGO_SECURE_SSL_REDIRECT=true behind a correctly configured proxy.",
                id="foodai_security.E013",
            )
        )
    if not getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False):
        messages.append(
            Critical(
                "Production must enable X-Content-Type-Options: nosniff.",
                hint="Set DJANGO_SECURE_CONTENT_TYPE_NOSNIFF=true.",
                id="foodai_security.E014",
            )
        )
    if getattr(settings, "X_FRAME_OPTIONS", "").upper() != "DENY":
        messages.append(
            Critical(
                "Production must deny framing by default.",
                hint='Set X_FRAME_OPTIONS = "DENY".',
                id="foodai_security.E015",
            )
        )
    if int(getattr(settings, "SECURE_HSTS_SECONDS", 0)) < 31_536_000:
        messages.append(
            Warning(
                "Production HSTS is shorter than one year.",
                hint="Keep SECURE_HSTS_SECONDS at least 31536000 after HTTPS rollout is verified.",
                id="foodai_security.W001",
            )
        )

    return messages


def _check_api_defaults() -> list[CheckMessage]:
    default_permissions = [
        str(permission)
        for permission in settings.REST_FRAMEWORK.get("DEFAULT_PERMISSION_CLASSES", [])
    ]
    if "rest_framework.permissions.IsAuthenticated" not in default_permissions:
        return [
            Critical(
                "DRF default permissions must remain deny-by-default.",
                hint="Keep DEFAULT_PERMISSION_CLASSES set to IsAuthenticated.",
                id="foodai_security.E016",
            )
        ]
    return []


def _check_private_storage() -> list[CheckMessage]:
    storage_backend = str(getattr(settings, "FOOD_SCAN_PRIVATE_STORAGE_BACKEND", "local")).lower()
    if storage_backend == "local":
        return [
            Warning(
                "Production food photo storage is configured as local filesystem.",
                hint=(
                    "Use a private S3-compatible object storage implementation before production "
                    "or document the deployment-specific private volume boundary."
                ),
                id="foodai_security.W002",
            )
        ]
    return []


def _contains_wildcard(values: Iterable[str]) -> bool:
    return any(value.strip() in {"*", "http://*", "https://*"} for value in values)


def _as_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value]
    return []

