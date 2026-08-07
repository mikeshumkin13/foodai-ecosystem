from __future__ import annotations

from collections.abc import Iterator
from itertools import count
from typing import Any

from accounts.models import User, UserProfile

_user_sequence: Iterator[int] = count(1)


def make_user(
    *,
    email: str | None = None,
    password: str | None = "SafePassword123!",
    **extra_fields: Any,
) -> User:
    resolved_email = email or f"user{next(_user_sequence)}@example.com"
    return User.objects.create_user(
        email=resolved_email,
        password=password,
        **extra_fields,
    )


def make_superuser(
    *,
    email: str | None = None,
    password: str | None = "SafeAdminPassword123!",
    **extra_fields: Any,
) -> User:
    resolved_email = email or f"admin{next(_user_sequence)}@example.com"
    return User.objects.create_superuser(
        email=resolved_email,
        password=password,
        **extra_fields,
    )


def make_user_profile(
    *,
    user: User | None = None,
    **extra_fields: Any,
) -> UserProfile:
    resolved_user = user or make_user()
    return UserProfile.objects.create(user=resolved_user, **extra_fields)
