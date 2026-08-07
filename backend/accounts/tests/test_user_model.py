from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from accounts.models import User, UserProfile
from accounts.tests.factories import make_superuser, make_user, make_user_profile

pytestmark = pytest.mark.django_db


def test_create_regular_user_with_email_login() -> None:
    user = make_user(email="Person@Example.COM", password="SafePassword123!")

    assert isinstance(user.id, uuid.UUID)
    assert user.email == "person@example.com"
    assert user.USERNAME_FIELD == "email"
    assert user.REQUIRED_FIELDS == []
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert user.check_password("SafePassword123!") is True
    assert user.created_at is not None
    assert user.updated_at is not None


def test_create_superuser_sets_required_flags() -> None:
    user = make_superuser(email="admin@example.com", password="SafeAdminPassword123!")

    assert user.email == "admin@example.com"
    assert user.is_active is True
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.check_password("SafeAdminPassword123!") is True


def test_create_superuser_rejects_missing_staff_flag() -> None:
    with pytest.raises(ValueError, match="is_staff=True"):
        make_superuser(email="admin@example.com", is_staff=False)


def test_create_superuser_rejects_missing_superuser_flag() -> None:
    with pytest.raises(ValueError, match="is_superuser=True"):
        make_superuser(email="admin@example.com", is_superuser=False)


def test_email_is_unique() -> None:
    make_user(email="unique@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        make_user(email="UNIQUE@example.com")


def test_password_is_not_stored_as_plaintext() -> None:
    raw_password = "NeverStoreThisPlaintext123!"
    user = make_user(password=raw_password)

    user.refresh_from_db()

    assert user.password != raw_password
    assert raw_password not in user.password
    assert user.has_usable_password() is True
    assert user.check_password(raw_password) is True


def test_custom_user_model_is_configured() -> None:
    assert get_user_model() is User


def test_user_profile_keeps_non_auth_user_data_outside_user_model() -> None:
    user = make_user()
    profile = make_user_profile(
        user=user,
        display_name="FoodAI User",
        preferred_language="en",
    )

    assert isinstance(profile.id, uuid.UUID)
    assert profile.user == user
    assert profile.display_name == "FoodAI User"
    assert profile.preferred_language == "en"
    assert UserProfile.objects.get(user=user) == profile
