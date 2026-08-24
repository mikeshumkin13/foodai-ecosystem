from __future__ import annotations

from typing import cast

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.http import HttpRequest
from django.test import RequestFactory
from django.urls import reverse

from accounts.models import User
from accounts.rbac import Role, assign_role
from accounts.tests.factories import make_superuser, make_user
from audit.models import AuditLog
from audit.services import REDACTED_VALUE, record_audit_event, record_support_access

pytestmark = pytest.mark.django_db


def _staff_user_with_role(role: Role) -> User:
    user = make_user(is_staff=True)
    assign_role(user, role)
    return user


def _admin_request(user: User, *, correlation_id: str = "audit-test-request") -> HttpRequest:
    request = cast(
        HttpRequest,
        RequestFactory().get(reverse("admin:index"), HTTP_X_REQUEST_ID=correlation_id),
    )
    request.user = user
    return request


def test_record_audit_event_sanitizes_sensitive_metadata_and_sets_correlation_id() -> None:
    actor = make_user()
    request = _admin_request(actor, correlation_id="audit-sanitizer-1")

    audit_log = record_audit_event(
        actor=actor,
        action=AuditLog.Action.DATA_EXPORTED,
        target_type="accounts.user",
        target_id=actor.id,
        metadata={
            "safe_reason": "user_requested_export",
            "password": "PlaintextPassword123!",
            "access_token": "secret-token",
            "food_photo": b"binary-image",
            "nested": {
                "health_profile": {"mass_kg": "80"},
                "count": 1,
            },
        },
        request=request,
    )

    assert audit_log.actor == actor
    assert audit_log.actor_id_snapshot == str(actor.id)
    assert audit_log.request_correlation_id == "audit-sanitizer-1"
    assert audit_log.metadata["safe_reason"] == "user_requested_export"
    assert audit_log.metadata["password"] == REDACTED_VALUE
    assert audit_log.metadata["access_token"] == REDACTED_VALUE
    assert audit_log.metadata["food_photo"] == REDACTED_VALUE
    assert audit_log.metadata["nested"]["health_profile"] == REDACTED_VALUE
    assert audit_log.metadata["nested"]["count"] == 1


def test_support_access_event_records_only_safe_metadata() -> None:
    actor = _staff_user_with_role(Role.SUPPORT)
    target_user = make_user()
    request = _admin_request(actor, correlation_id="support-access-1")

    audit_log = record_support_access(
        actor=actor,
        target_user_id=target_user.id,
        reason_code="account_access_request",
        request=request,
    )

    assert audit_log.action == AuditLog.Action.SUPPORT_ACCESS
    assert audit_log.actor == actor
    assert audit_log.target_type == "accounts.user"
    assert audit_log.target_id == str(target_user.id)
    assert audit_log.metadata == {
        "reason_code": "account_access_request",
        "source": "support_tool",
    }
    assert audit_log.request_correlation_id == "support-access-1"


def test_user_admin_change_records_security_audit_and_role_change_events() -> None:
    actor = _staff_user_with_role(Role.ADMIN)
    target_user = make_user(email="target@example.com")
    user_admin = admin.site._registry[User]
    request = _admin_request(actor, correlation_id="admin-user-change-1")

    user_admin.log_change(
        request,
        target_user,
        [{"changed": {"fields": ["email", "groups"]}}],
    )

    audit_logs = AuditLog.objects.filter(
        target_type="accounts.user",
        target_id=str(target_user.id),
    )
    assert audit_logs.filter(action=AuditLog.Action.ADMIN_USER_CHANGED).count() == 1
    assert audit_logs.filter(action=AuditLog.Action.ROLE_CHANGED).count() == 1
    for audit_log in audit_logs:
        assert audit_log.actor == actor
        assert audit_log.request_correlation_id == "admin-user-change-1"
        assert audit_log.metadata["source"] == "django_admin"
        assert target_user.email not in str(audit_log.metadata)


def test_group_admin_change_records_role_change_event() -> None:
    actor = _staff_user_with_role(Role.ADMIN)
    group = Group.objects.create(name="temporary_role")
    group_admin = admin.site._registry[Group]
    request = _admin_request(actor, correlation_id="admin-role-change-1")

    group_admin.log_change(request, group, [{"changed": {"fields": ["permissions"]}}])

    audit_log = AuditLog.objects.get(
        action=AuditLog.Action.ROLE_CHANGED,
        target_type="auth.group",
        target_id=str(group.id),
    )
    assert audit_log.actor == actor
    assert audit_log.metadata["changed_fields"] == ["permissions"]
    assert audit_log.request_correlation_id == "admin-role-change-1"


def test_audit_log_admin_is_read_only_and_admin_role_only() -> None:
    audit_admin = admin.site._registry[AuditLog]
    superuser_request = _admin_request(make_superuser())
    admin_request = _admin_request(_staff_user_with_role(Role.ADMIN))
    support_request = _admin_request(_staff_user_with_role(Role.SUPPORT))

    assert audit_admin.has_add_permission(superuser_request) is False
    assert audit_admin.has_change_permission(superuser_request) is False
    assert audit_admin.has_delete_permission(superuser_request) is False
    assert audit_admin.has_view_permission(admin_request) is True
    assert audit_admin.has_view_permission(support_request) is False
