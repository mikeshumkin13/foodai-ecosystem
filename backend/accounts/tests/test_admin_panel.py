from __future__ import annotations

from typing import Any, cast

import pytest
from django.contrib import admin
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse

from accounts.models import (
    AdminAuditLog,
    EmailVerificationToken,
    NutritionProfile,
    NutritionSensitiveRestriction,
    PasswordResetToken,
    User,
    UserProfile,
)
from accounts.rbac import Role, assign_role
from accounts.tests.factories import make_superuser, make_user
from audit.models import AuditLog

pytestmark = pytest.mark.django_db

SENSITIVE_ADMIN_MODELS = {
    "accounts.user",
    "accounts.userprofile",
    "accounts.adminauditlog",
    "audit.auditlog",
}


def _staff_user_with_role(role: Role) -> User:
    user = make_user(is_staff=True)
    assign_role(user, role)
    return user


def _admin_request(user: User) -> HttpRequest:
    request = cast(HttpRequest, RequestFactory().get(reverse("admin:index")))
    request.user = user
    return request


def _visible_admin_model_labels(user: User) -> set[str]:
    app_list: list[dict[str, Any]] = admin.site.get_app_list(_admin_request(user))
    return {
        f"{app['app_label']}.{model['object_name'].lower()}"
        for app in app_list
        for model in app["models"]
    }


def test_admin_role_sees_user_roles_and_audit_models_in_admin_index() -> None:
    admin_user = _staff_user_with_role(Role.ADMIN)

    visible_models = _visible_admin_model_labels(admin_user)

    assert {
        "accounts.user",
        "accounts.userprofile",
        "accounts.adminauditlog",
        "audit.auditlog",
        "auth.group",
    }.issubset(visible_models)


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER])
def test_support_and_content_manager_do_not_see_sensitive_admin_models(role: Role) -> None:
    staff_user = _staff_user_with_role(role)

    visible_models = _visible_admin_model_labels(staff_user)

    assert visible_models.isdisjoint(SENSITIVE_ADMIN_MODELS)
    assert "auth.group" not in visible_models


def test_admin_role_can_open_user_profile_roles_and_audit_changelists(client: Client) -> None:
    admin_user = _staff_user_with_role(Role.ADMIN)
    client.force_login(admin_user)

    for url_name in (
        "admin:accounts_user_changelist",
        "admin:accounts_userprofile_changelist",
        "admin:accounts_adminauditlog_changelist",
        "admin:audit_auditlog_changelist",
        "admin:auth_group_changelist",
    ):
        response = client.get(reverse(url_name))

        assert response.status_code == 200, url_name


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER])
@pytest.mark.parametrize(
    "url_name",
    [
        "admin:accounts_user_changelist",
        "admin:accounts_userprofile_changelist",
        "admin:accounts_adminauditlog_changelist",
        "admin:audit_auditlog_changelist",
        "admin:auth_group_changelist",
    ],
)
def test_support_and_content_manager_cannot_open_sensitive_admin_changelists(
    role: Role,
    url_name: str,
    client: Client,
) -> None:
    staff_user = _staff_user_with_role(role)
    client.force_login(staff_user)

    response = client.get(reverse(url_name))

    assert response.status_code == 403


def test_admin_bulk_actions_are_disabled_and_security_tokens_are_hidden() -> None:
    assert admin.site._registry[User].actions is None
    assert admin.site._registry[UserProfile].actions is None
    assert admin.site._registry[Group].actions is None
    assert admin.site._registry[AdminAuditLog].actions is None
    assert admin.site._registry[AuditLog].actions is None
    assert EmailVerificationToken not in admin.site._registry
    assert NutritionProfile not in admin.site._registry
    assert NutritionSensitiveRestriction not in admin.site._registry
    assert PasswordResetToken not in admin.site._registry


def test_admin_audit_log_is_read_only() -> None:
    request = _admin_request(make_superuser())
    audit_admin = admin.site._registry[AdminAuditLog]
    security_audit_admin = admin.site._registry[AuditLog]

    assert audit_admin.has_add_permission(request) is False
    assert audit_admin.has_change_permission(request) is False
    assert audit_admin.has_delete_permission(request) is False
    assert security_audit_admin.has_add_permission(request) is False
    assert security_audit_admin.has_change_permission(request) is False
    assert security_audit_admin.has_delete_permission(request) is False


def test_admin_log_entry_creates_sanitized_audit_log() -> None:
    actor = _staff_user_with_role(Role.ADMIN)
    target_user = make_user(email="private-target@example.com")
    content_type = ContentType.objects.get_for_model(User)

    log_entry = LogEntry.objects.create(
        user=actor,
        content_type=content_type,
        object_id=str(target_user.id),
        object_repr=target_user.email,
        action_flag=CHANGE,
        change_message='[{"changed": {"fields": ["email"]}}]',
    )

    audit_log = AdminAuditLog.objects.get(source_log_entry_id=log_entry.id)
    assert audit_log.actor_id == actor.id
    assert audit_log.action == AdminAuditLog.Action.CHANGE
    assert audit_log.model_label == "accounts.user"
    assert audit_log.object_id == str(target_user.id)
    assert audit_log.object_repr == f"accounts.user:{target_user.id}"
    assert target_user.email not in audit_log.object_repr
    assert audit_log.change_message == [{"changed": {"fields": ["email"]}}]
