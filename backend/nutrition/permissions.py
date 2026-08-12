from __future__ import annotations

from typing import cast

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from accounts.models import User
from accounts.rbac import MANAGE_FOOD_CATALOG_PERMISSION


class CanReadOrManageNutritionCatalog(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        request_user = request.user
        if not request_user or not request_user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        user = cast(User, request_user)
        return user.is_superuser or user.has_perm(MANAGE_FOOD_CATALOG_PERMISSION)
