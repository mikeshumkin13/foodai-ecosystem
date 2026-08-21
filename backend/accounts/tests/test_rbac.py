from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.rbac import (
    ADMINISTER_ACCOUNTS_PERMISSION,
    CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION,
    CHANGE_OWN_NUTRITION_PROFILE_PERMISSION,
    CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION,
    CHANGE_OWN_PROFILE_PERMISSION,
    CHANGE_OWN_WORKOUT_LOG_PERMISSION,
    CHANGE_OWN_WORKOUT_PLAN_PERMISSION,
    CHANGE_ROLE_GROUP_PERMISSION,
    ROLE_DEFINITIONS,
    USE_AI_COACH_PERMISSION,
    USE_AI_FITNESS_COACH_PERMISSION,
    VIEW_ADMIN_AUDIT_LOG_PERMISSION,
    VIEW_OWN_AI_COACH_SETTINGS_PERMISSION,
    VIEW_OWN_NUTRITION_PROFILE_PERMISSION,
    VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION,
    VIEW_OWN_PROFILE_PERMISSION,
    VIEW_OWN_WORKOUT_LOG_PERMISSION,
    VIEW_OWN_WORKOUT_PLAN_PERMISSION,
    VIEW_ROLE_GROUP_PERMISSION,
    Role,
    assign_role,
    user_has_role,
)
from accounts.tests.factories import make_superuser, make_user, make_user_profile

pytestmark = pytest.mark.django_db


def _group_permission_codes(group_name: str) -> set[str]:
    group = Group.objects.get(name=group_name)
    return {
        f"{app_label}.{codename}"
        for app_label, codename in group.permissions.values_list(
            "content_type__app_label",
            "codename",
        )
    }


def _profile_detail_url(profile_id: object) -> str:
    return reverse("account-profile-detail", kwargs={"id": profile_id})


def test_role_groups_are_seeded_with_expected_permissions() -> None:
    for role, definition in ROLE_DEFINITIONS.items():
        assert Group.objects.filter(name=definition.group_name).exists(), role.value
        assert _group_permission_codes(definition.group_name) == definition.permissions


def test_regular_user_receives_user_role_by_default() -> None:
    user = make_user()

    assert user_has_role(user, Role.USER) is True
    assert user.has_perm(VIEW_OWN_PROFILE_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_PROFILE_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_NUTRITION_PROFILE_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_NUTRITION_PROFILE_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION) is True
    assert user.has_perm(USE_AI_COACH_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_AI_COACH_SETTINGS_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION) is True
    assert user.has_perm(USE_AI_FITNESS_COACH_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_WORKOUT_PLAN_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_WORKOUT_PLAN_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_WORKOUT_LOG_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_WORKOUT_LOG_PERMISSION) is True
    assert user.has_perm(ADMINISTER_ACCOUNTS_PERMISSION) is False


def test_superuser_does_not_receive_business_role_by_default() -> None:
    user = make_superuser()

    assert set(user.groups.values_list("name", flat=True)) == set()


def test_assign_role_replaces_only_foodai_business_roles() -> None:
    user = make_user()
    extra_group = Group.objects.create(name="external-audit")
    user.groups.add(extra_group)

    assign_role(user, Role.SUPPORT)

    assert user_has_role(user, Role.SUPPORT) is True
    assert user_has_role(user, Role.USER) is False
    assert user.groups.filter(name="external-audit").exists() is True


def test_support_and_content_manager_do_not_get_private_user_permissions() -> None:
    forbidden_permissions = {
        "accounts.view_userprofile",
        "accounts.change_userprofile",
        VIEW_OWN_PROFILE_PERMISSION,
        CHANGE_OWN_PROFILE_PERMISSION,
        VIEW_OWN_NUTRITION_PROFILE_PERMISSION,
        CHANGE_OWN_NUTRITION_PROFILE_PERMISSION,
        VIEW_OWN_NUTRITION_RESTRICTION_PERMISSION,
        CHANGE_OWN_NUTRITION_RESTRICTION_PERMISSION,
        USE_AI_COACH_PERMISSION,
        VIEW_OWN_AI_COACH_SETTINGS_PERMISSION,
        CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION,
        USE_AI_FITNESS_COACH_PERMISSION,
        VIEW_OWN_WORKOUT_PLAN_PERMISSION,
        CHANGE_OWN_WORKOUT_PLAN_PERMISSION,
        VIEW_OWN_WORKOUT_LOG_PERMISSION,
        CHANGE_OWN_WORKOUT_LOG_PERMISSION,
        VIEW_ADMIN_AUDIT_LOG_PERMISSION,
        VIEW_ROLE_GROUP_PERMISSION,
        CHANGE_ROLE_GROUP_PERMISSION,
        ADMINISTER_ACCOUNTS_PERMISSION,
    }

    support_permissions = _group_permission_codes(Role.SUPPORT.value)
    content_manager_permissions = _group_permission_codes(Role.CONTENT_MANAGER.value)

    assert support_permissions.isdisjoint(forbidden_permissions)
    assert content_manager_permissions.isdisjoint(forbidden_permissions)


def test_profile_endpoint_denies_anonymous_user(api_client: APIClient) -> None:
    profile = make_user_profile()

    response = api_client.get(_profile_detail_url(profile.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_profile_endpoint_denies_user_without_role(api_client: APIClient) -> None:
    user = make_user()
    user.groups.clear()
    profile = make_user_profile(user=user)
    api_client.force_authenticate(user=user)

    response = api_client.get(_profile_detail_url(profile.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_can_read_own_profile(api_client: APIClient) -> None:
    user = make_user()
    profile = make_user_profile(user=user, display_name="Owner")
    api_client.force_authenticate(user=user)

    response = api_client.get(_profile_detail_url(profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(profile.id)
    assert response.json()["display_name"] == "Owner"


def test_user_can_update_own_profile(api_client: APIClient) -> None:
    user = make_user()
    profile = make_user_profile(user=user)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        _profile_detail_url(profile.id),
        {"display_name": "Updated", "preferred_language": "en"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    profile.refresh_from_db()
    assert profile.display_name == "Updated"
    assert profile.preferred_language == "en"


def test_idor_user_cannot_read_another_user_profile_by_uuid(api_client: APIClient) -> None:
    user_a = make_user()
    user_b = make_user()
    profile_b = make_user_profile(user=user_b)
    api_client.force_authenticate(user=user_a)

    response = api_client.get(_profile_detail_url(profile_b.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER])
def test_non_owner_staff_roles_cannot_read_user_profile(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    target_profile = make_user_profile()
    api_client.force_authenticate(user=actor)

    response = api_client.get(_profile_detail_url(target_profile.id))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_role_can_read_user_profile(api_client: APIClient) -> None:
    admin_user = make_user()
    assign_role(admin_user, Role.ADMIN)
    target_profile = make_user_profile()
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(_profile_detail_url(target_profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(target_profile.id)


def test_superuser_can_read_user_profile_without_business_role(api_client: APIClient) -> None:
    superuser = make_superuser()
    target_profile = make_user_profile()
    api_client.force_authenticate(user=superuser)

    response = api_client.get(_profile_detail_url(target_profile.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(target_profile.id)
