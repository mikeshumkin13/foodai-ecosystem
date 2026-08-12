from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from rest_framework import serializers

from diary.models import Meal, MealItem
from diary.snapshots import build_food_snapshot
from nutrition.models import FoodItem


class MealItemReadSerializer(serializers.ModelSerializer[MealItem]):
    food_id = serializers.UUIDField(read_only=True)
    calories = serializers.DecimalField(
        source="calories_kcal",
        max_digits=12,
        decimal_places=4,
        read_only=True,
    )
    protein = serializers.DecimalField(
        source="protein_g",
        max_digits=12,
        decimal_places=4,
        read_only=True,
    )
    fat = serializers.DecimalField(
        source="fat_g",
        max_digits=12,
        decimal_places=4,
        read_only=True,
    )
    carbs = serializers.DecimalField(
        source="carbs_g",
        max_digits=12,
        decimal_places=4,
        read_only=True,
    )

    class Meta:
        model = MealItem
        fields = (
            "id",
            "food_id",
            "food_name_snapshot",
            "food_source_reference_snapshot",
            "mass_g",
            "calories",
            "protein",
            "fat",
            "carbs",
            "micronutrient_snapshot",
            "nutrient_snapshot",
            "source",
            "confidence",
            "manually_corrected",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MealItemWriteSerializer(serializers.Serializer[dict[str, Any]]):
    food_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodItem.objects.all(),
        source="food",
    )
    mass_g = serializers.DecimalField(max_digits=9, decimal_places=2, min_value=Decimal("0.01"))
    calories = serializers.DecimalField(
        source="calories_kcal",
        max_digits=12,
        decimal_places=4,
        min_value=Decimal("0"),
        required=False,
    )
    protein = serializers.DecimalField(
        source="protein_g",
        max_digits=12,
        decimal_places=4,
        min_value=Decimal("0"),
        required=False,
    )
    fat = serializers.DecimalField(
        source="fat_g",
        max_digits=12,
        decimal_places=4,
        min_value=Decimal("0"),
        required=False,
    )
    carbs = serializers.DecimalField(
        source="carbs_g",
        max_digits=12,
        decimal_places=4,
        min_value=Decimal("0"),
        required=False,
    )
    micronutrient_snapshot = serializers.JSONField(required=False)
    nutrient_snapshot = serializers.JSONField(required=False)
    source = serializers.ChoiceField(  # type: ignore[assignment]
        choices=MealItem.Source.choices, default=MealItem.Source.FOOD_CATALOG
    )
    confidence = serializers.DecimalField(
        max_digits=5,
        decimal_places=4,
        min_value=Decimal("0"),
        max_value=Decimal("1"),
        allow_null=True,
        required=False,
    )
    manually_corrected = serializers.BooleanField(default=False)

    def validate_micronutrient_snapshot(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("micronutrient_snapshot_must_be_object")
        return value

    def validate_nutrient_snapshot(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("nutrient_snapshot_must_be_object")
        return value


class MealReadSerializer(serializers.ModelSerializer[Meal]):
    user_id = serializers.UUIDField(read_only=True)
    items = MealItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Meal
        fields = (
            "id",
            "user_id",
            "meal_type",
            "logged_at",
            "name",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class MealWriteSerializer(serializers.ModelSerializer[Meal]):
    items = MealItemWriteSerializer(many=True, required=False)

    class Meta:
        model = Meal
        fields = (
            "id",
            "meal_type",
            "logged_at",
            "name",
            "items",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Meal:
        items_data = validated_data.pop("items", [])
        meal = Meal.objects.create(**validated_data)
        _create_meal_items(meal, items_data)
        return meal

    @transaction.atomic
    def update(self, instance: Meal, validated_data: dict[str, Any]) -> Meal:
        items_data = validated_data.pop("items", None)
        for field_name, value in validated_data.items():
            setattr(instance, field_name, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            _create_meal_items(instance, items_data)

        return instance


def _create_meal_items(meal: Meal, items_data: list[dict[str, Any]]) -> None:
    meal_items = [_build_meal_item(meal, item_data) for item_data in items_data]
    MealItem.objects.bulk_create(meal_items)


def _build_meal_item(meal: Meal, item_data: dict[str, Any]) -> MealItem:
    food = item_data["food"]
    mass_g = item_data["mass_g"]
    snapshot = build_food_snapshot(food, mass_g)

    return MealItem(
        meal=meal,
        food=food,
        food_name_snapshot=snapshot["food_name_snapshot"],
        food_source_reference_snapshot=snapshot["food_source_reference_snapshot"],
        mass_g=mass_g,
        calories_kcal=item_data.get("calories_kcal", snapshot["calories_kcal"]),
        protein_g=item_data.get("protein_g", snapshot["protein_g"]),
        fat_g=item_data.get("fat_g", snapshot["fat_g"]),
        carbs_g=item_data.get("carbs_g", snapshot["carbs_g"]),
        micronutrient_snapshot=item_data.get(
            "micronutrient_snapshot",
            snapshot["micronutrient_snapshot"],
        ),
        nutrient_snapshot=item_data.get("nutrient_snapshot", snapshot["nutrient_snapshot"]),
        source=item_data.get("source", MealItem.Source.FOOD_CATALOG),
        confidence=item_data.get("confidence"),
        manually_corrected=item_data.get("manually_corrected", False),
    )
