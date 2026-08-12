from __future__ import annotations

import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import NutritionProfile, NutritionSensitiveRestriction
from accounts.rbac import Role, assign_role
from accounts.tests.factories import (
    make_nutrition_profile,
    make_nutrition_sensitive_restriction,
    make_superuser,
    make_user,
)

pytestmark = pytest.mark.django_db


def _nutrition_profile_url(profile_id: object) -> str:
    return reverse("account-nutrition-profile-detail", kwargs={"id": profile_id})


def _nutrition_restriction_url(restriction_id: object) -> str:
    return reverse("account-nutrition-restriction-detail", kwargs={"id": restriction_id})


def test_nutrition_profile_uses_privacy_friendly_age_category() -> None:
    profile = make_nutrition_profile()
    field_names = {field.name for field in NutritionProfile._meta.fields}

    assert isinstance(profile.id, uuid.UUID)
    assert "age_category" in field_names
    assert "birth_year" not in field_names
    assert "date_of_birth" not in field_names
    assert profile.consent_version == NutritionProfile.CONSENT_VERSION
    assert profile.consent_granted_at is None


def test_nutrition_sensitive_restriction_is_separate_from_profile() -> None:
    restriction = make_nutrition_sensitive_restriction(label="Peanut")
    profile_field_names = {field.name for field in NutritionProfile._meta.fields}

    assert "allergies" not in profile_field_names
    assert "medical_restrictions" not in profile_field_names
    assert restriction.label == "Peanut"
    assert restriction.consent_version == NutritionSensitiveRestriction.CONSENT_VERSION
    assert restriction.consent_granted_at is not None


def test_nutrition_profile_endpoint_denies_anonymous_user(api_client: APIClient) -> None:
    profile = make_nutrition_profile()

    response = api_client.get(_nutrition_profile_url(profile.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_can_read_own_nutrition_profile(api_client: APIClient) -> None:
    user = make_user()
    profile = make_nutrition_profile(user=user, goal=NutritionProfile.Goal.IMPROVE_HABITS)
    api_client.force_authenticate(user=user)

    response = api_client.get(_nutrition_profile_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(profile.id)
    assert response.json()["user_id"] == str(user.id)
    assert response.json()["goal"] == NutritionProfile.Goal.IMPROVE_HABITS


def test_user_update_nutrition_profile_requires_consent(api_client: APIClient) -> None:
    user = make_user()
    profile = make_nutrition_profile(user=user)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        _nutrition_profile_url(profile.id),
        {"goal": NutritionProfile.Goal.LOSE_WEIGHT},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["non_field_errors"] == ["nutrition_profile_consent_required"]


def test_user_can_update_own_nutrition_profile_with_consent(api_client: APIClient) -> None:
    user = make_user()
    profile = make_nutrition_profile(user=user)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        _nutrition_profile_url(profile.id),
        {
            "goal": NutritionProfile.Goal.LOSE_WEIGHT,
            "height_cm": 181,
            "mass_kg": "82.40",
            "age_category": NutritionProfile.AgeCategory.AGE_30_39,
            "activity_level": NutritionProfile.ActivityLevel.MODERATE,
            "preferred_units": NutritionProfile.PreferredUnits.METRIC,
            "dietary_preferences": ["vegetarian", "high_protein", "vegetarian"],
            "consent_accepted": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["goal"] == NutritionProfile.Goal.LOSE_WEIGHT
    assert response.json()["height_cm"] == 181
    assert response.json()["mass_kg"] == "82.40"
    assert response.json()["dietary_preferences"] == ["vegetarian", "high_protein"]
    assert response.json()["consent_granted_at"] is not None

    profile.refresh_from_db()
    assert profile.consent_granted_at is not None


def test_dietary_preferences_none_cannot_be_combined(api_client: APIClient) -> None:
    user = make_user()
    profile = make_nutrition_profile(user=user)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        _nutrition_profile_url(profile.id),
        {
            "dietary_preferences": ["none", "vegan"],
            "consent_accepted": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["dietary_preferences"] == ["dietary_preferences_none_must_be_alone"]


def test_idor_user_cannot_read_another_nutrition_profile_by_uuid(
    api_client: APIClient,
) -> None:
    user_a = make_user()
    user_b = make_user()
    profile_b = make_nutrition_profile(user=user_b)
    api_client.force_authenticate(user=user_a)

    response = api_client.get(_nutrition_profile_url(profile_b.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_staff_roles_cannot_read_nutrition_profile_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    target_profile = make_nutrition_profile()
    api_client.force_authenticate(user=actor)

    response = api_client.get(_nutrition_profile_url(target_profile.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_superuser_can_read_nutrition_profile_as_technical_override(
    api_client: APIClient,
) -> None:
    superuser = make_superuser()
    target_profile = make_nutrition_profile()
    api_client.force_authenticate(user=superuser)

    response = api_client.get(_nutrition_profile_url(target_profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(target_profile.id)


def test_user_lists_only_own_sensitive_nutrition_restrictions(api_client: APIClient) -> None:
    user = make_user()
    own_restriction = make_nutrition_sensitive_restriction(user=user, label="Peanut")
    make_nutrition_sensitive_restriction(label="Soy")
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("account-nutrition-restriction-list"))

    assert response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in response.json()] == [str(own_restriction.id)]


def test_user_create_sensitive_restriction_requires_consent(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("account-nutrition-restriction-list"),
        {
            "restriction_type": NutritionSensitiveRestriction.RestrictionType.ALLERGY,
            "label": "Peanut",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["non_field_errors"] == ["sensitive_nutrition_consent_required"]


def test_user_can_create_own_sensitive_restriction_with_consent(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("account-nutrition-restriction-list"),
        {
            "restriction_type": NutritionSensitiveRestriction.RestrictionType.ALLERGY,
            "label": "  Peanut  ",
            "consent_accepted": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["user_id"] == str(user.id)
    assert response.json()["label"] == "Peanut"
    assert response.json()["consent_granted_at"] is not None
    assert NutritionSensitiveRestriction.objects.get(id=response.json()["id"]).user == user


def test_idor_user_cannot_read_another_sensitive_restriction_by_uuid(
    api_client: APIClient,
) -> None:
    user = make_user()
    other_restriction = make_nutrition_sensitive_restriction()
    api_client.force_authenticate(user=user)

    response = api_client.get(_nutrition_restriction_url(other_restriction.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_staff_roles_cannot_read_sensitive_restrictions_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    api_client.force_authenticate(user=actor)

    response = api_client.get(reverse("account-nutrition-restriction-list"))

    assert response.status_code == status.HTTP_403_FORBIDDEN
