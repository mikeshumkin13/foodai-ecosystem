from __future__ import annotations

from typing import cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User
from accounts.rbac import (
    CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION,
    USE_AI_COACH_PERMISSION,
    VIEW_OWN_AI_COACH_SETTINGS_PERMISSION,
)


class CanUseAICoach(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser:
            return True

        action = _resolve_action(request, view)
        if action == "settings_read":
            return user.has_perm(VIEW_OWN_AI_COACH_SETTINGS_PERMISSION)
        if action == "settings_update":
            return user.has_perm(CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION)
        return user.has_perm(USE_AI_COACH_PERMISSION)


def _resolve_action(request: Request, view: APIView) -> str:
    action = getattr(view, "action", "")
    if action:
        return str(action)
    if view.__class__.__name__ == "AICoachSettingsView" and request.method == "GET":
        return "settings_read"
    if view.__class__.__name__ == "AICoachSettingsView" and request.method == "PATCH":
        return "settings_update"
    return "ask"
