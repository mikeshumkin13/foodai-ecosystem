from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from rest_framework import serializers

from diary.models import Meal
from food_scans.image_processing import FoodPhotoValidationError
from food_scans.models import FoodScan, FoodScanDetectedItem
from food_scans.services import create_food_scan
from nutrition.models import FoodItem


class FoodScanDetectedItemReadSerializer(serializers.ModelSerializer[FoodScanDetectedItem]):
    food_id = serializers.UUIDField(source="matched_food_id", read_only=True)
    food = serializers.SerializerMethodField()
    portion_estimate = serializers.SerializerMethodField()
    mass_g = serializers.DecimalField(
        source="estimated_mass_g",
        max_digits=9,
        decimal_places=2,
        read_only=True,
    )
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
        model = FoodScanDetectedItem
        fields = (
            "id",
            "label",
            "confidence",
            "food_id",
            "food",
            "mass_g",
            "manual_mass_g",
            "portion_estimate",
            "calories",
            "protein",
            "fat",
            "carbs",
            "nutrient_snapshot",
            "micronutrient_snapshot",
            "source",
            "is_removed",
            "manually_corrected",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_food(self, obj: FoodScanDetectedItem) -> dict[str, str] | None:
        if obj.matched_food is None:
            return None
        return {
            "id": str(obj.matched_food.id),
            "name": obj.matched_food.name,
            "name_ru": obj.matched_food.name_ru,
            "name_en": obj.matched_food.name_en,
        }

    def get_portion_estimate(self, obj: FoodScanDetectedItem) -> dict[str, str] | None:
        if not obj.portion_estimation_method:
            return None
        if (
            obj.portion_estimated_volume_ml is None
            or obj.portion_estimated_mass_g is None
            or obj.portion_min_mass_g is None
            or obj.portion_max_mass_g is None
            or obj.portion_confidence is None
        ):
            return None
        return {
            "estimated_volume": _format_decimal(obj.portion_estimated_volume_ml, places=2),
            "estimated_mass": _format_decimal(obj.portion_estimated_mass_g, places=2),
            "confidence": _format_decimal(obj.portion_confidence, places=4),
            "min_estimate": _format_decimal(obj.portion_min_mass_g, places=2),
            "max_estimate": _format_decimal(obj.portion_max_mass_g, places=2),
            "method": obj.portion_estimation_method,
        }


class FoodScanReadSerializer(serializers.ModelSerializer[FoodScan]):
    user_id = serializers.UUIDField(read_only=True)
    confirmed_meal_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = FoodScan
        fields = (
            "id",
            "user_id",
            "status",
            "failure_code",
            "confirmed_meal_id",
            "image_format",
            "content_type",
            "uploaded_byte_size",
            "stored_byte_size",
            "width",
            "height",
            "exif_stripped",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FoodScanBackgroundStatusSerializer(serializers.ModelSerializer[FoodScan]):
    scan_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = FoodScan
        fields = ("scan_id", "status")
        read_only_fields = fields


class FoodScanResultSerializer(FoodScanReadSerializer):
    detected_items = serializers.SerializerMethodField()

    class Meta:
        model = FoodScan
        fields = (
            "id",
            "user_id",
            "status",
            "failure_code",
            "confirmed_meal_id",
            "image_format",
            "content_type",
            "uploaded_byte_size",
            "stored_byte_size",
            "width",
            "height",
            "exif_stripped",
            "created_at",
            "updated_at",
            "detected_items",
        )
        read_only_fields = fields

    def get_detected_items(self, obj: FoodScan) -> list[dict[str, Any]]:
        if obj.status not in {FoodScan.Status.NEEDS_CONFIRMATION, FoodScan.Status.CONFIRMED}:
            return []

        detected_items = (
            obj.detected_items.select_related("matched_food")
            .filter(is_removed=False)
            .order_by("position", "created_at", "id")
        )
        return cast(
            list[dict[str, Any]],
            FoodScanDetectedItemReadSerializer(detected_items, many=True).data,
        )


class FoodScanUploadSerializer(serializers.Serializer[FoodScan]):
    photo = serializers.FileField(write_only=True)

    def create(self, validated_data: dict[str, UploadedFile]) -> FoodScan:
        request = self.context["request"]
        try:
            return create_food_scan(user=request.user, uploaded_file=validated_data["photo"])
        except FoodPhotoValidationError as exc:
            raise serializers.ValidationError({"photo": [exc.code]}) from exc

    def update(self, instance: FoodScan, validated_data: dict[str, UploadedFile]) -> FoodScan:
        raise NotImplementedError


class FoodScanDetectedItemUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    food_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodItem.objects.all(),
        source="matched_food",
        required=False,
    )
    mass_g = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal("0.01"),
        required=False,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if "matched_food" not in attrs and "mass_g" not in attrs:
            raise serializers.ValidationError({"detail": ["empty_detected_item_update"]})
        return attrs


class FoodScanDetectedItemAddSerializer(serializers.Serializer[dict[str, Any]]):
    food_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodItem.objects.all(),
        source="matched_food",
    )
    mass_g = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    label = serializers.CharField(  # type: ignore[assignment]
        max_length=160,
        allow_blank=True,
        required=False,
        default="",
    )

    def validate_label(self, value: str) -> str:
        return value.strip()


class FoodScanConfirmSerializer(serializers.Serializer[dict[str, Any]]):
    meal_type = serializers.ChoiceField(choices=Meal.MealType.choices, default=Meal.MealType.CUSTOM)
    logged_at = serializers.DateTimeField(default=timezone.now)
    name = serializers.CharField(max_length=120, allow_blank=True, required=False, default="")


def _format_decimal(value: Decimal, *, places: int) -> str:
    return f"{value:.{places}f}"
