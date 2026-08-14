from __future__ import annotations

from typing import Any, cast

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User
from accounts.rbac import CHANGE_OWN_FOOD_SCAN_PERMISSION, VIEW_OWN_FOOD_SCAN_PERMISSION
from diary.serializers import MealReadSerializer
from food_scans.jobs import FoodScanJobError, enqueue_food_scan_analysis
from food_scans.models import FoodScan, FoodScanDetectedItem
from food_scans.orchestration import (
    FoodScanWorkflowError,
    add_manual_detected_item,
    confirm_food_scan,
    remove_scan_detected_item,
    update_scan_detected_item,
)
from food_scans.permissions import CanAccessFoodScan
from food_scans.serializers import (
    FoodScanBackgroundStatusSerializer,
    FoodScanConfirmSerializer,
    FoodScanDetectedItemAddSerializer,
    FoodScanDetectedItemReadSerializer,
    FoodScanDetectedItemUpdateSerializer,
    FoodScanReadSerializer,
    FoodScanResultSerializer,
    FoodScanUploadSerializer,
)

ITEM_ID_PARAMETER = OpenApiParameter(
    name="item_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    required=True,
)


class FoodScanViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanAccessFoodScan]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
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
    ) -> (
        type[FoodScanReadSerializer]
        | type[FoodScanUploadSerializer]
        | type[FoodScanBackgroundStatusSerializer]
        | type[FoodScanResultSerializer]
        | type[FoodScanDetectedItemAddSerializer]
        | type[FoodScanDetectedItemUpdateSerializer]
        | type[FoodScanConfirmSerializer]
    ):
        if self.action == "create":
            return FoodScanUploadSerializer
        if self.action == "results":
            return FoodScanResultSerializer
        if self.action == "items":
            return FoodScanDetectedItemAddSerializer
        if self.action == "item":
            return FoodScanDetectedItemUpdateSerializer
        if self.action == "confirm":
            return FoodScanConfirmSerializer
        if self.action == "retry":
            return FoodScanBackgroundStatusSerializer
        return FoodScanReadSerializer

    @extend_schema(
        request=FoodScanUploadSerializer,
        responses={status.HTTP_201_CREATED: FoodScanBackgroundStatusSerializer},
    )
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        upload_serializer = self.get_serializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        food_scan = upload_serializer.save()
        food_scan = enqueue_food_scan_analysis(food_scan=food_scan)
        read_serializer = FoodScanBackgroundStatusSerializer(
            food_scan,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=FoodScanResultSerializer)
    @action(detail=True, methods=["get"], url_path="results")
    def results(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        food_scan = self.get_object()
        serializer = FoodScanResultSerializer(food_scan, context=self.get_serializer_context())
        return Response(serializer.data)

    @extend_schema(
        request=None,
        responses={status.HTTP_202_ACCEPTED: FoodScanBackgroundStatusSerializer},
    )
    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        food_scan = self.get_object()
        try:
            food_scan = enqueue_food_scan_analysis(food_scan=food_scan, force=True)
        except FoodScanJobError as exc:
            raise ValidationError({"detail": [exc.code]}) from exc

        serializer = FoodScanBackgroundStatusSerializer(
            food_scan,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        request=FoodScanDetectedItemAddSerializer,
        responses={status.HTTP_201_CREATED: FoodScanDetectedItemReadSerializer},
    )
    @action(detail=True, methods=["post"], url_path="items")
    def items(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        food_scan = self.get_object()
        serializer = FoodScanDetectedItemAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            detected_item = add_manual_detected_item(
                food_scan=food_scan,
                matched_food=serializer.validated_data["matched_food"],
                mass_g=serializer.validated_data["mass_g"],
                label=serializer.validated_data["label"],
            )
        except FoodScanWorkflowError as exc:
            raise _workflow_validation_error(exc) from exc

        read_serializer = FoodScanDetectedItemReadSerializer(
            detected_item,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        methods=["PATCH"],
        parameters=[ITEM_ID_PARAMETER],
        request=FoodScanDetectedItemUpdateSerializer,
        responses=FoodScanDetectedItemReadSerializer,
    )
    @extend_schema(
        methods=["DELETE"],
        parameters=[ITEM_ID_PARAMETER],
        request=None,
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"items/(?P<item_id>[^/.]+)")
    def item(
        self,
        request: Request,
        item_id: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Response:
        food_scan = self.get_object()
        detected_item = get_object_or_404(
            FoodScanDetectedItem.objects.select_related("matched_food"),
            id=item_id,
            food_scan=food_scan,
        )

        if request.method == "DELETE":
            try:
                remove_scan_detected_item(food_scan=food_scan, detected_item=detected_item)
            except FoodScanWorkflowError as exc:
                raise _workflow_validation_error(exc) from exc
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = FoodScanDetectedItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        matched_food = serializer.validated_data.get("matched_food") or detected_item.matched_food
        if matched_food is None:
            raise ValidationError({"food_id": ["food_match_required"]})
        mass_was_provided = "mass_g" in serializer.validated_data
        mass_g = serializer.validated_data.get("mass_g", detected_item.estimated_mass_g)

        try:
            detected_item = update_scan_detected_item(
                food_scan=food_scan,
                detected_item=detected_item,
                matched_food=matched_food,
                mass_g=mass_g,
                manual_mass_g=mass_g if mass_was_provided else None,
            )
        except FoodScanWorkflowError as exc:
            raise _workflow_validation_error(exc) from exc

        read_serializer = FoodScanDetectedItemReadSerializer(
            detected_item,
            context=self.get_serializer_context(),
        )
        return Response(read_serializer.data)

    @extend_schema(
        request=FoodScanConfirmSerializer,
        responses={
            status.HTTP_200_OK: OpenApiTypes.OBJECT,
            status.HTTP_201_CREATED: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        food_scan = self.get_object()
        serializer = FoodScanConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        already_confirmed = food_scan.status == FoodScan.Status.CONFIRMED

        try:
            meal = confirm_food_scan(
                food_scan=food_scan,
                meal_type=serializer.validated_data["meal_type"],
                logged_at=serializer.validated_data["logged_at"],
                name=serializer.validated_data["name"],
            )
        except FoodScanWorkflowError as exc:
            raise _workflow_validation_error(exc) from exc

        food_scan.refresh_from_db()
        return Response(
            {
                "food_scan": FoodScanResultSerializer(
                    food_scan,
                    context=self.get_serializer_context(),
                ).data,
                "meal": MealReadSerializer(meal, context=self.get_serializer_context()).data,
            },
            status=status.HTTP_200_OK if already_confirmed else status.HTTP_201_CREATED,
        )


def _workflow_validation_error(exc: FoodScanWorkflowError) -> ValidationError:
    payload: dict[str, Any] = {"detail": [exc.code]}
    payload.update(exc.details)
    return ValidationError(payload)
