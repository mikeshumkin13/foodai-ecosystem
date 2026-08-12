from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User
from accounts.rbac import CHANGE_OWN_FOOD_SCAN_PERMISSION, VIEW_OWN_FOOD_SCAN_PERMISSION
from food_scans.models import FoodScan
from food_scans.permissions import CanAccessFoodScan
from food_scans.serializers import FoodScanReadSerializer, FoodScanUploadSerializer


class FoodScanViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanAccessFoodScan]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[FoodScan]:
        request_user = self.request.user
        queryset = FoodScan.objects.select_related("user")

        if not request_user or not request_user.is_authenticated:
            return queryset.none()

        user = cast(User, request_user)
        if user.is_superuser:
            return queryset
        if user.has_perm(VIEW_OWN_FOOD_SCAN_PERMISSION) or user.has_perm(
            CHANGE_OWN_FOOD_SCAN_PERMISSION
        ):
            return queryset.filter(user=user)
        return queryset.none()

    def get_serializer_class(
        self,
    ) -> type[FoodScanReadSerializer] | type[FoodScanUploadSerializer]:
        if self.action == "create":
            return FoodScanUploadSerializer
        return FoodScanReadSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        upload_serializer = self.get_serializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        food_scan = upload_serializer.save()
        read_serializer = FoodScanReadSerializer(
            food_scan,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
