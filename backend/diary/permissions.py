from __future__ import annotations

from typing import Any, cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User
from accounts.rbac import CHANGE_OWN_MEAL_PERMISSION, VIEW_OWN_MEAL_PERMISSION
from diary.models import Meal


class CanAccessMeal(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser:
            return True

        action = getattr(view, "action", "")
        if action in {"list", "retrieve"}:
            return user.has_perm(VIEW_OWN_MEAL_PERMISSION)
        if action in {"create", "partial_update", "update", "destroy"}:
            return user.has_perm(CHANGE_OWN_MEAL_PERMISSION)
        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not isinstance(obj, Meal):
            return False

        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser:
            return True
        if obj.user_id != user.id:
            return False

        action = getattr(view, "action", "")
        if action in {"list", "retrieve"}:
            return user.has_perm(VIEW_OWN_MEAL_PERMISSION)
        if action in {"create", "partial_update", "update", "destroy"}:
            return user.has_perm(CHANGE_OWN_MEAL_PERMISSION)
        return False


class CanReadDiaryDay(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        return user.is_superuser or user.has_perm(VIEW_OWN_MEAL_PERMISSION)
