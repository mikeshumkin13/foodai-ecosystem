from __future__ import annotations

from typing import Any

from rest_framework import serializers

from nutrition.models import FoodCategory, FoodDataSource, FoodItem, FoodNutrient, Nutrient


class FoodCategorySerializer(serializers.ModelSerializer[FoodCategory]):
    class Meta:
        model = FoodCategory
        fields = ("id", "slug", "name", "name_ru", "name_en")
        read_only_fields = fields


class FoodDataSourceSerializer(serializers.ModelSerializer[FoodDataSource]):
    class Meta:
        model = FoodDataSource
        fields = ("id", "code", "name", "source_type", "source_reference")
        read_only_fields = fields


class NutrientSerializer(serializers.ModelSerializer[Nutrient]):
    class Meta:
        model = Nutrient
        fields = ("id", "code", "name", "name_ru", "name_en", "unit", "nutrient_type")
        read_only_fields = fields


class FoodNutrientSerializer(serializers.ModelSerializer[FoodNutrient]):
    nutrient = NutrientSerializer(read_only=True)
    unit = serializers.CharField(source="nutrient.unit", read_only=True)

    class Meta:
        model = FoodNutrient
        fields = ("id", "nutrient", "amount_per_100g", "unit", "source_reference")
        read_only_fields = fields


class FoodItemReadSerializer(serializers.ModelSerializer[FoodItem]):
    category = FoodCategorySerializer(read_only=True)
    data_source = FoodDataSourceSerializer(read_only=True)
    nutrients = FoodNutrientSerializer(source="nutrient_values", many=True, read_only=True)
    canonical_food_id = serializers.UUIDField(read_only=True)
    is_canonical = serializers.BooleanField(read_only=True)

    class Meta:
        model = FoodItem
        fields = (
            "id",
            "canonical_food_id",
            "is_canonical",
            "name",
            "name_ru",
            "name_en",
            "synonyms",
            "category",
            "data_source",
            "density_g_per_ml",
            "density_metadata",
            "is_verified",
            "source_reference",
            "nutrients",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class FoodItemWriteSerializer(serializers.ModelSerializer[FoodItem]):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodCategory.objects.all(),
        source="category",
        write_only=True,
    )
    data_source_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodDataSource.objects.all(),
        source="data_source",
        write_only=True,
    )
    canonical_food_id = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=FoodItem.objects.all(),
        required=False,
        source="canonical_food",
        write_only=True,
    )

    class Meta:
        model = FoodItem
        fields = (
            "id",
            "canonical_food_id",
            "name",
            "name_ru",
            "name_en",
            "synonyms",
            "category_id",
            "data_source_id",
            "density_g_per_ml",
            "density_metadata",
            "is_verified",
            "source_reference",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_synonyms(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            raise serializers.ValidationError("synonyms_must_be_list")

        cleaned_synonyms: list[str] = []
        seen_synonyms: set[str] = set()
        for raw_synonym in value:
            if not isinstance(raw_synonym, str):
                raise serializers.ValidationError("synonyms_must_contain_strings")
            synonym = raw_synonym.strip()
            if not synonym:
                continue
            if len(synonym) > 120:
                raise serializers.ValidationError("synonym_too_long")
            normalized_synonym = synonym.casefold()
            if normalized_synonym not in seen_synonyms:
                cleaned_synonyms.append(synonym)
                seen_synonyms.add(normalized_synonym)

        return cleaned_synonyms

    def validate_density_metadata(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("density_metadata_must_be_object")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        canonical_food = attrs.get(
            "canonical_food",
            self.instance.canonical_food if self.instance is not None else None,
        )
        if self.instance is not None and canonical_food is not None:
            if canonical_food.id == self.instance.id:
                raise serializers.ValidationError(
                    {"canonical_food_id": ["canonical_food_cannot_reference_self"]},
                )
        return attrs
