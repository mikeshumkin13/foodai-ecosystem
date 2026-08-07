from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from rest_framework import mixins, viewsets

from accounts.models import User, UserProfile
from accounts.permissions import CanAccessUserProfile
from accounts.rbac import (
    ADMINISTER_ACCOUNTS_PERMISSION,
    CHANGE_OWN_PROFILE_PERMISSION,
    VIEW_OWN_PROFILE_PERMISSION,
)
from accounts.serializers import UserProfileSerializer


class UserProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserProfileSerializer
    permission_classes = [CanAccessUserProfile]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[UserProfile]:
        request_user = self.request.user
        base_queryset = UserProfile.objects.select_related("user")

        if not request_user or not request_user.is_authenticated:
            return base_queryset.none()

        user = cast(User, request_user)
        if user.is_superuser or user.has_perm(ADMINISTER_ACCOUNTS_PERMISSION):
            return base_queryset

        if user.has_perm(VIEW_OWN_PROFILE_PERMISSION) or user.has_perm(
            CHANGE_OWN_PROFILE_PERMISSION
        ):
            return base_queryset.filter(user=user)

        return base_queryset.none()
