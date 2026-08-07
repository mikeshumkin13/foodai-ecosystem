from __future__ import annotations

from http.cookies import Morsel
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.auth_tokens import hash_token
from accounts.models import EmailVerificationToken, PasswordResetToken, User, UserProfile
from accounts.rbac import Role, user_has_role
from accounts.tests.factories import make_user, make_user_profile

pytestmark = pytest.mark.django_db

PASSWORD = "SafePassword123!"
NEW_PASSWORD = "SaferPassword456!"


@pytest.fixture(autouse=True)
def clear_auth_rate_limit_cache() -> None:
    cache.clear()


def _csrf_client() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get(reverse("auth-csrf"))
    assert response.status_code == status.HTTP_200_OK
    return client, response.json()["csrf_token"]


def _post_with_csrf(
    client: APIClient,
    path_name: str,
    data: dict[str, object],
    csrf_token: str,
) -> Any:
    return client.post(
        reverse(path_name),
        data,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def _last_email_link_params() -> dict[str, str]:
    outbox = cast("list[Any]", mail.outbox)
    body = str(outbox[-1].body)
    link = next(line for line in body.splitlines() if line.startswith("http"))
    parsed = parse_qs(urlparse(link).query)
    return {key: values[0] for key, values in parsed.items()}


def _verify_user_email(client: APIClient, csrf_token: str) -> User:
    params = _last_email_link_params()
    response = _post_with_csrf(
        client,
        "auth-email-verify",
        {
            "token_id": params["token_id"],
            "token": params["token"],
        },
        csrf_token,
    )
    assert response.status_code == status.HTTP_200_OK
    return cast(User, User.objects.get(email="person@example.com"))


def _register_user(client: APIClient, csrf_token: str) -> User:
    response = _post_with_csrf(
        client,
        "auth-register",
        {
            "email": "Person@Example.COM",
            "password": PASSWORD,
            "display_name": "Person",
            "preferred_language": "en",
        },
        csrf_token,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return cast(User, User.objects.get(email="person@example.com"))


def _login(client: APIClient, csrf_token: str, *, password: str = PASSWORD) -> Any:
    return _post_with_csrf(
        client,
        "auth-login",
        {
            "email": "person@example.com",
            "password": password,
        },
        csrf_token,
    )


def _cookie_has_flag(cookie: Morsel[str], flag: str) -> bool:
    return bool(cookie[flag])


def test_csrf_endpoint_sets_csrf_cookie() -> None:
    client = APIClient(enforce_csrf_checks=True)

    response = client.get(reverse("auth-csrf"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == "csrf_cookie_set"
    assert settings.CSRF_COOKIE_NAME in response.cookies
    assert response.cookies[settings.CSRF_COOKIE_NAME]["samesite"] == "Lax"


def test_register_requires_csrf() -> None:
    client = APIClient(enforce_csrf_checks=True)

    response = client.post(
        reverse("auth-register"),
        {"email": "person@example.com", "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_register_creates_inactive_user_profile_role_and_email_token() -> None:
    client, csrf_token = _csrf_client()

    user = _register_user(client, csrf_token)
    params = _last_email_link_params()

    assert user.is_active is False
    assert user_has_role(user, Role.USER) is True
    assert UserProfile.objects.get(user=user).display_name == "Person"
    assert UserProfile.objects.get(user=user).preferred_language == "en"
    token = EmailVerificationToken.objects.get(user=user)
    assert str(token.id) == params["token_id"]
    assert token.token_hash == hash_token(params["token"])
    assert token.token_hash != params["token"]
    assert "password" not in client.get(reverse("auth-csrf")).json()


def test_email_verification_activates_user_and_is_one_time() -> None:
    client, csrf_token = _csrf_client()
    user = _register_user(client, csrf_token)
    params = _last_email_link_params()

    verified_user = _verify_user_email(client, csrf_token)

    assert verified_user.id == user.id
    assert verified_user.is_active is True
    token = EmailVerificationToken.objects.get(id=params["token_id"])
    assert token.used_at is not None

    second_response = _post_with_csrf(
        client,
        "auth-email-verify",
        {
            "token_id": params["token_id"],
            "token": params["token"],
        },
        csrf_token,
    )
    assert second_response.status_code == status.HTTP_403_FORBIDDEN


def test_login_fails_before_email_verification_and_succeeds_after() -> None:
    client, csrf_token = _csrf_client()
    _register_user(client, csrf_token)

    inactive_response = _login(client, csrf_token)

    assert inactive_response.status_code == status.HTTP_400_BAD_REQUEST
    assert inactive_response.json()["non_field_errors"] == ["invalid_credentials"]

    _verify_user_email(client, csrf_token)
    response = _login(client, csrf_token)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == "login_success"
    assert response.json()["user"]["email"] == "person@example.com"
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.json()
    assert settings.SESSION_COOKIE_NAME in response.cookies
    assert settings.CSRF_COOKIE_NAME in response.cookies
    assert _cookie_has_flag(response.cookies[settings.SESSION_COOKIE_NAME], "httponly")
    assert response.cookies[settings.SESSION_COOKIE_NAME]["samesite"] == "Lax"


@override_settings(SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
def test_login_sets_secure_cookies_when_configured() -> None:
    client, csrf_token = _csrf_client()
    _register_user(client, csrf_token)
    _verify_user_email(client, csrf_token)

    response = _login(client, csrf_token)

    assert response.status_code == status.HTTP_200_OK
    assert _cookie_has_flag(response.cookies[settings.SESSION_COOKIE_NAME], "secure")
    assert _cookie_has_flag(response.cookies[settings.CSRF_COOKIE_NAME], "secure")


def test_me_requires_authentication(api_client: APIClient) -> None:
    response = api_client.get(reverse("auth-me"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_email_verification_resend_is_generic_and_rotates_token() -> None:
    client, csrf_token = _csrf_client()
    user = _register_user(client, csrf_token)
    first_token = EmailVerificationToken.objects.get(user=user)
    outbox = cast("list[Any]", mail.outbox)
    outbox.clear()

    existing_response = _post_with_csrf(
        client,
        "auth-email-resend",
        {"email": "person@example.com"},
        csrf_token,
    )
    unknown_response = _post_with_csrf(
        client,
        "auth-email-resend",
        {"email": "unknown@example.com"},
        csrf_token,
    )

    first_token.refresh_from_db()
    active_tokens = EmailVerificationToken.objects.filter(user=user, used_at__isnull=True)

    assert existing_response.status_code == status.HTTP_200_OK
    assert unknown_response.status_code == status.HTTP_200_OK
    assert existing_response.json() == unknown_response.json()
    assert first_token.used_at is not None
    assert active_tokens.count() == 1
    assert len(outbox) == 1


def test_me_returns_current_user_without_sensitive_fields(api_client: APIClient) -> None:
    user = make_user(email="me@example.com", password=PASSWORD)
    make_user_profile(user=user, display_name="Me")
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("auth-me"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "me@example.com"
    assert response.json()["profile"]["display_name"] == "Me"
    assert "password" not in response.json()


def test_refresh_rotates_session_cookie_and_csrf_token() -> None:
    client, csrf_token = _csrf_client()
    _register_user(client, csrf_token)
    _verify_user_email(client, csrf_token)
    login_response = _login(client, csrf_token)
    session_cookie = login_response.cookies[settings.SESSION_COOKIE_NAME].value
    login_csrf_token = login_response.cookies[settings.CSRF_COOKIE_NAME].value

    response = client.post(
        reverse("auth-refresh"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=login_csrf_token,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == "session_refreshed"
    assert response.cookies[settings.SESSION_COOKIE_NAME].value != session_cookie
    assert response.cookies[settings.CSRF_COOKIE_NAME].value != login_csrf_token


def test_logout_flushes_session() -> None:
    client, csrf_token = _csrf_client()
    _register_user(client, csrf_token)
    _verify_user_email(client, csrf_token)
    login_response = _login(client, csrf_token)
    login_csrf_token = login_response.cookies[settings.CSRF_COOKIE_NAME].value

    logout_response = client.post(
        reverse("auth-logout"),
        {},
        format="json",
        HTTP_X_CSRFTOKEN=login_csrf_token,
    )
    me_response = client.get(reverse("auth-me"))

    assert logout_response.status_code == status.HTTP_200_OK
    assert logout_response.json()["code"] == "logout_success"
    assert me_response.status_code == status.HTTP_403_FORBIDDEN


def test_password_reset_request_is_generic_and_confirm_resets_password() -> None:
    user = make_user(email="person@example.com", password=PASSWORD)
    client, csrf_token = _csrf_client()
    outbox = cast("list[Any]", mail.outbox)
    outbox.clear()

    existing_response = _post_with_csrf(
        client,
        "auth-password-reset-request",
        {"email": "person@example.com"},
        csrf_token,
    )
    unknown_response = _post_with_csrf(
        client,
        "auth-password-reset-request",
        {"email": "unknown@example.com"},
        csrf_token,
    )
    params = _last_email_link_params()

    assert existing_response.status_code == status.HTTP_200_OK
    assert unknown_response.status_code == status.HTTP_200_OK
    assert existing_response.json() == unknown_response.json()
    assert len(outbox) == 1
    token = PasswordResetToken.objects.get(user=user)
    assert str(token.id) == params["token_id"]
    assert token.token_hash == hash_token(params["token"])

    confirm_response = _post_with_csrf(
        client,
        "auth-password-reset-confirm",
        {
            "token_id": params["token_id"],
            "token": params["token"],
            "new_password": NEW_PASSWORD,
        },
        csrf_token,
    )
    user.refresh_from_db()
    reused_response = _post_with_csrf(
        client,
        "auth-password-reset-confirm",
        {
            "token_id": params["token_id"],
            "token": params["token"],
            "new_password": PASSWORD,
        },
        csrf_token,
    )

    assert confirm_response.status_code == status.HTTP_200_OK
    assert user.check_password(NEW_PASSWORD) is True
    assert PasswordResetToken.objects.get(id=params["token_id"]).used_at is not None
    assert reused_response.status_code == status.HTTP_403_FORBIDDEN


def test_password_change_requires_current_password_and_keeps_current_session() -> None:
    client, csrf_token = _csrf_client()
    _register_user(client, csrf_token)
    user = _verify_user_email(client, csrf_token)
    login_response = _login(client, csrf_token)
    login_csrf_token = login_response.cookies[settings.CSRF_COOKIE_NAME].value

    wrong_response = client.post(
        reverse("auth-password-change"),
        {"current_password": "wrong-password", "new_password": NEW_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=login_csrf_token,
    )
    response = client.post(
        reverse("auth-password-change"),
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=login_csrf_token,
    )
    me_response = client.get(reverse("auth-me"))
    user.refresh_from_db()

    assert wrong_response.status_code == status.HTTP_403_FORBIDDEN
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["code"] == "password_changed"
    assert user.check_password(NEW_PASSWORD) is True
    assert me_response.status_code == status.HTTP_200_OK


def test_login_is_rate_limited() -> None:
    cache.clear()
    rest_framework_settings = cast("dict[str, Any]", settings.REST_FRAMEWORK)
    throttled_settings = {
        **rest_framework_settings,
        "DEFAULT_THROTTLE_RATES": {
            **rest_framework_settings["DEFAULT_THROTTLE_RATES"],
            "auth_login": "2/minute",
        },
    }
    make_user(email="person@example.com", password=PASSWORD)
    client, csrf_token = _csrf_client()

    with override_settings(REST_FRAMEWORK=throttled_settings):
        first_response = _login(client, csrf_token, password="wrong-password")
        second_response = _login(client, csrf_token, password="wrong-password")
        third_response = _login(client, csrf_token, password="wrong-password")

    assert first_response.status_code == status.HTTP_400_BAD_REQUEST
    assert second_response.status_code == status.HTTP_400_BAD_REQUEST
    assert third_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
