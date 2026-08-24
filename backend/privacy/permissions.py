from __future__ import annotations

from typing import cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User
from accounts.rbac import (
    CHANGE_OWN_PRIVACY_SETTINGS_PERMISSION,
    DELETE_OWN_DATA_PERMISSION,
    EXPORT_OWN_DATA_PERMISSION,
    VIEW_OWN_PRIVACY_SETTINGS_PERMISSION,
)


class CanUsePrivacyCenter(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser:
            return True

        action = _resolve_action(request, view)
        if action in {"summary", "consent_read"}:
            return user.has_perm(VIEW_OWN_PRIVACY_SETTINGS_PERMISSION)
        if action == "consent_update":
            return user.has_perm(CHANGE_OWN_PRIVACY_SETTINGS_PERMISSION)
        if action == "export":
            return user.has_perm(EXPORT_OWN_DATA_PERMISSION)
        if action in {"delete_photo", "delete_ai_history", "delete_account"}:
            return user.has_perm(DELETE_OWN_DATA_PERMISSION)
        return False


def _resolve_action(request: Request, view: APIView) -> str:
    action = getattr(view, "privacy_action", "")
    if action:
        return str(action)
    if view.__class__.__name__ == "PrivacyConsentView" and request.method == "PATCH":
        return "consent_update"
    if view.__class__.__name__ == "PrivacyConsentView" and request.method == "GET":
        return "consent_read"
    view_name = view.__class__.__name__
    return {
        "PrivacyDataSummaryView": "summary",
        "PrivacyDataExportView": "export",
        "PrivacyConsentView": "consent_read",
        "PrivacyFoodPhotoDeleteView": "delete_photo",
        "PrivacyAIChatHistoryDeleteView": "delete_ai_history",
        "PrivacyAccountDeleteView": "delete_account",
    }.get(view_name, "")
