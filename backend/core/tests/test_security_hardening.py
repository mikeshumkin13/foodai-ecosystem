from __future__ import annotations

from django.conf import settings
from django.test import Client, override_settings
from django.urls import reverse
from pytest import MonkeyPatch
from rest_framework.test import APIClient

from core.security_checks import check_security_configuration


def test_drf_defaults_remain_deny_by_default() -> None:
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated",
    ]


@override_settings(
    SECURE_CONTENT_TYPE_NOSNIFF=True,
    SECURE_REFERRER_POLICY="same-origin",
    SECURE_CROSS_ORIGIN_OPENER_POLICY="same-origin",
    SECURE_HSTS_SECONDS=31_536_000,
    X_FRAME_OPTIONS="DENY",
)
def test_security_headers_are_emitted_for_https_responses() -> None:
    response = Client().get(reverse("health"), secure=True)

    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Referrer-Policy"] == "same-origin"
    assert response["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response["X-Frame-Options"] == "DENY"
    assert "max-age=31536000" in response["Strict-Transport-Security"]


@override_settings(
    CORS_ALLOWED_ORIGINS=["https://app.foodai.example"],
    CORS_ALLOW_CREDENTIALS=True,
)
def test_cors_uses_explicit_allowlist_with_credentials() -> None:
    client = Client()

    trusted_response = client.get(reverse("health"), HTTP_ORIGIN="https://app.foodai.example")
    untrusted_response = client.get(reverse("health"), HTTP_ORIGIN="https://evil.example")

    assert trusted_response["Access-Control-Allow-Origin"] == "https://app.foodai.example"
    assert trusted_response["Access-Control-Allow-Credentials"] == "true"
    assert "Access-Control-Allow-Origin" not in untrusted_response


def test_public_auth_post_requires_csrf_token() -> None:
    response = APIClient(enforce_csrf_checks=True).post(
        reverse("auth-login"),
        {"email": "person@example.com", "password": "SafePassword123!"},
        format="json",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "csrf_failed"


@override_settings(
    DEBUG=True,
    SECRET_KEY="change-me-local-only",
    ALLOWED_HOSTS=["*"],
    CORS_ALLOW_ALL_ORIGINS=True,
    CORS_ALLOWED_ORIGINS=["http://localhost:3000"],
    CSRF_TRUSTED_ORIGINS=["http://localhost:3000"],
    FRONTEND_BASE_URL="http://localhost:3000",
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=False,
    SESSION_COOKIE_SAMESITE="invalid",
    CSRF_COOKIE_SAMESITE="invalid",
    SECURE_SSL_REDIRECT=False,
    SECURE_CONTENT_TYPE_NOSNIFF=False,
    SECURE_HSTS_SECONDS=0,
    X_FRAME_OPTIONS="SAMEORIGIN",
    FOOD_SCAN_PRIVATE_STORAGE_BACKEND="local",
    REST_FRAMEWORK={"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]},
)
def test_production_security_check_blocks_dangerous_configuration(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    messages = check_security_configuration(None)
    message_ids = {message.id for message in messages}

    assert {
        "foodai_security.E001",
        "foodai_security.E002",
        "foodai_security.E003",
        "foodai_security.E004",
        "foodai_security.E005",
        "foodai_security.E007",
        "foodai_security.E008",
        "foodai_security.E009",
        "foodai_security.E010",
        "foodai_security.E011",
        "foodai_security.E012",
        "foodai_security.E013",
        "foodai_security.E014",
        "foodai_security.E015",
        "foodai_security.E016",
        "foodai_security.W001",
        "foodai_security.W002",
    }.issubset(message_ids)


@override_settings(
    DEBUG=False,
    SECRET_KEY="prod-secret-key-with-at-least-32-characters",
    ALLOWED_HOSTS=["api.foodai.example"],
    CORS_ALLOW_ALL_ORIGINS=False,
    CORS_ALLOWED_ORIGINS=["https://app.foodai.example"],
    CSRF_TRUSTED_ORIGINS=["https://app.foodai.example"],
    FRONTEND_BASE_URL="https://app.foodai.example",
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    CSRF_COOKIE_SAMESITE="Lax",
    SECURE_SSL_REDIRECT=True,
    SECURE_CONTENT_TYPE_NOSNIFF=True,
    SECURE_HSTS_SECONDS=31_536_000,
    X_FRAME_OPTIONS="DENY",
    FOOD_SCAN_PRIVATE_STORAGE_BACKEND="s3-compatible",
    REST_FRAMEWORK={
        "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    },
)
def test_production_security_check_accepts_hardened_configuration(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    assert check_security_configuration(None) == []
