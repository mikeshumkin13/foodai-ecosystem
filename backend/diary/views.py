from __future__ import annotations

from datetime import date
from typing import Any, cast

from django.db.models import QuerySet
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.rbac import CHANGE_OWN_MEAL_PERMISSION, VIEW_OWN_MEAL_PERMISSION
from diary.aggregation import aggregate_meals
from diary.models import Meal
from diary.permissions import CanAccessMeal, CanReadDiaryDay
from diary.serializers import MealReadSerializer, MealWriteSerializer


class MealViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanAccessMeal]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[Meal]:
        request_user = self.request.user
        queryset = Meal.objects.select_related("user").prefetch_related(
            "items__food",
            "items__food__nutrient_values__nutrient",
        )

        if not request_user or not request_user.is_authenticated:
            return queryset.none()

        user = cast(User, request_user)
        if user.is_superuser:
            return _apply_date_filters(queryset, self.request)

        if user.has_perm(VIEW_OWN_MEAL_PERMISSION) or user.has_perm(CHANGE_OWN_MEAL_PERMISSION):
            return _apply_date_filters(queryset.filter(user=user), self.request)

        return queryset.none()

    def get_serializer_class(self) -> type[MealReadSerializer] | type[MealWriteSerializer]:
        if self.action in {"create", "update", "partial_update"}:
            return MealWriteSerializer
        return MealReadSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meal = serializer.save(user=cast(User, request.user))
        read_serializer = MealReadSerializer(meal, context=self.get_serializer_context())
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        meal = serializer.save()
        read_serializer = MealReadSerializer(meal, context=self.get_serializer_context())
        return Response(read_serializer.data)


class DiaryDayView(APIView):
    permission_classes = [CanReadDiaryDay]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request: Request) -> Response:
        requested_date = _parse_required_date(request.query_params.get("date"), field_name="date")
        user = cast(User, request.user)
        meals = (
            Meal.objects.filter(user=user, logged_at__date=requested_date)
            .prefetch_related("items")
            .order_by("logged_at", "created_at")
        )
        totals = aggregate_meals(meals)
        return Response(
            {
                "date": requested_date.isoformat(),
                "totals": totals["totals"],
                "micronutrient_totals": totals["micronutrient_totals"],
                "meals": MealReadSerializer(meals, many=True).data,
            },
        )


def _apply_date_filters(queryset: QuerySet[Meal], request: Request) -> QuerySet[Meal]:
    date = request.query_params.get("date")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if date:
        return queryset.filter(logged_at__date=_parse_required_date(date, field_name="date"))
    if date_from:
        queryset = queryset.filter(
            logged_at__date__gte=_parse_required_date(date_from, field_name="date_from"),
        )
    if date_to:
        queryset = queryset.filter(
            logged_at__date__lte=_parse_required_date(date_to, field_name="date_to"),
        )
    return queryset


def _parse_required_date(raw_value: str | None, *, field_name: str) -> date:
    if not raw_value:
        raise ValidationError({field_name: ["date_required"]})
    parsed_date = parse_date(raw_value)
    if parsed_date is None:
        raise ValidationError({field_name: ["invalid_date"]})
    return parsed_date
