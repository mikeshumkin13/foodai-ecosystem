from __future__ import annotations

from typing import Any, cast

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User
from accounts.rbac import (
    CHANGE_OWN_WORKOUT_LOG_PERMISSION,
    CHANGE_OWN_WORKOUT_PLAN_PERMISSION,
    MANAGE_FITNESS_CATALOG_PERMISSION,
    USE_AI_FITNESS_COACH_PERMISSION,
    VIEW_OWN_WORKOUT_LOG_PERMISSION,
    VIEW_OWN_WORKOUT_PLAN_PERMISSION,
)
from fitness.models import WorkoutLog, WorkoutPlan


class CanReadOrManageExerciseCatalog(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        user = cast(User, request_user)
        return user.is_superuser or user.has_perm(MANAGE_FITNESS_CATALOG_PERMISSION)


class CanAccessWorkoutPlan(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser:
            return True

        action = getattr(view, "action", "")
        if action in {"list", "retrieve"}:
            return user.has_perm(VIEW_OWN_WORKOUT_PLAN_PERMISSION)
        if action in {"partial_update", "update", "destroy"}:
            return user.has_perm(CHANGE_OWN_WORKOUT_PLAN_PERMISSION)
        if action == "generate":
            return user.has_perm(USE_AI_FITNESS_COACH_PERMISSION) and user.has_perm(
                CHANGE_OWN_WORKOUT_PLAN_PERMISSION
            )
        if action == "adapt":
            return (
                user.has_perm(USE_AI_FITNESS_COACH_PERMISSION)
                and user.has_perm(CHANGE_OWN_WORKOUT_PLAN_PERMISSION)
                and user.has_perm(VIEW_OWN_WORKOUT_PLAN_PERMISSION)
            )
        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not isinstance(obj, WorkoutPlan):
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
        if action in {"retrieve"}:
            return user.has_perm(VIEW_OWN_WORKOUT_PLAN_PERMISSION)
        if action in {"partial_update", "update", "destroy", "adapt"}:
            return user.has_perm(CHANGE_OWN_WORKOUT_PLAN_PERMISSION)
        return False


class CanAccessWorkoutLog(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        user = cast(User, request_user)
        if user.is_superuser:
            return True

        action = getattr(view, "action", "")
        if action in {"list", "retrieve"}:
            return user.has_perm(VIEW_OWN_WORKOUT_LOG_PERMISSION)
        if action in {"create", "partial_update", "update", "destroy"}:
            return user.has_perm(CHANGE_OWN_WORKOUT_LOG_PERMISSION)
        return False

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if not isinstance(obj, WorkoutLog):
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
        if action in {"retrieve"}:
            return user.has_perm(VIEW_OWN_WORKOUT_LOG_PERMISSION)
        if action in {"partial_update", "update", "destroy"}:
            return user.has_perm(CHANGE_OWN_WORKOUT_LOG_PERMISSION)
        return False
