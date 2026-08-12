from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from nutrition.models import FoodItem
from nutrition.permissions import CanReadOrManageNutritionCatalog
from nutrition.serializers import FoodItemReadSerializer, FoodItemWriteSerializer


class FoodItemViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanReadOrManageNutritionCatalog]
    lookup_field = "id"

    def get_queryset(self) -> QuerySet[FoodItem]:
        return (
            FoodItem.objects.select_related("canonical_food", "category", "data_source")
            .prefetch_related("nutrient_values__nutrient")
            .order_by("name", "id")
        )

    def get_serializer_class(self) -> type[FoodItemReadSerializer] | type[FoodItemWriteSerializer]:
        if self.action in {"create", "update", "partial_update"}:
            return FoodItemWriteSerializer
        return FoodItemReadSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        food_item = write_serializer.save()
        read_serializer = FoodItemReadSerializer(food_item, context=self.get_serializer_context())
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        food_item = write_serializer.save()
        read_serializer = FoodItemReadSerializer(food_item, context=self.get_serializer_context())
        return Response(read_serializer.data)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request: Request) -> Response:
        raw_query = request.query_params.get("q", "")
        query = raw_query.strip().casefold()
        limit = _search_limit(request.query_params.get("limit"))

        food_items = list(self.get_queryset())
        if query:
            food_items = [
                food_item for food_item in food_items if _matches_food_item(food_item, query)
            ]

        serializer = FoodItemReadSerializer(
            food_items[:limit],
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)


def _search_limit(raw_limit: str | None) -> int:
    if raw_limit is None:
        return 20
    try:
        return min(max(int(raw_limit), 1), 50)
    except ValueError:
        return 20


def _matches_food_item(food_item: FoodItem, query: str) -> bool:
    searchable_values = [
        food_item.name,
        food_item.name_ru,
        food_item.name_en,
        food_item.category.name,
        food_item.category.name_ru,
        food_item.category.name_en,
        *food_item.synonyms,
    ]
    return any(query in value.casefold() for value in searchable_values if isinstance(value, str))
