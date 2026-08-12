from __future__ import annotations

from collections.abc import Iterator
from itertools import count
from typing import Any

from django.utils import timezone

from accounts.models import NutritionProfile, NutritionSensitiveRestriction, User, UserProfile

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


def make_nutrition_profile(
    *,
    user: User | None = None,
    **extra_fields: Any,
) -> NutritionProfile:
    resolved_user = user or make_user()
    return NutritionProfile.objects.create(user=resolved_user, **extra_fields)


def make_nutrition_sensitive_restriction(
    *,
    user: User | None = None,
    **extra_fields: Any,
) -> NutritionSensitiveRestriction:
    resolved_user = user or make_user()
    extra_fields.setdefault(
        "restriction_type",
        NutritionSensitiveRestriction.RestrictionType.ALLERGY,
    )
    extra_fields.setdefault("label", "Peanut")
    extra_fields.setdefault("consent_granted_at", timezone.now())
    return NutritionSensitiveRestriction.objects.create(user=resolved_user, **extra_fields)
