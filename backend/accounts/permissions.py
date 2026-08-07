from __future__ import annotations

from typing import Any, cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User, UserProfile
from accounts.rbac import (
    ADMINISTER_ACCOUNTS_PERMISSION,
    CHANGE_OWN_PROFILE_PERMISSION,
    VIEW_OWN_PROFILE_PERMISSION,
)


class CanAccessUserProfile(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser or user.has_perm(ADMINISTER_ACCOUNTS_PERMISSION):
            return True

        action = getattr(view, "action", "")
        if action == "retrieve":
            return user.has_perm(VIEW_OWN_PROFILE_PERMISSION)
        if action in {"partial_update", "update"}:
            return user.has_perm(CHANGE_OWN_PROFILE_PERMISSION)
        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not isinstance(obj, UserProfile):
            return False

        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser or user.has_perm(ADMINISTER_ACCOUNTS_PERMISSION):
            return True

        action = getattr(view, "action", "")
        if action == "retrieve":
            return obj.user_id == user.id and user.has_perm(VIEW_OWN_PROFILE_PERMISSION)
        if action in {"partial_update", "update"}:
            return obj.user_id == user.id and user.has_perm(CHANGE_OWN_PROFILE_PERMISSION)
        return False
