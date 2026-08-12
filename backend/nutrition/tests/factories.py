from __future__ import annotations

from decimal import Decimal
from typing import Any

from nutrition.models import FoodCategory, FoodDataSource, FoodItem, FoodNutrient, Nutrient


def make_food_category(**extra_fields: Any) -> FoodCategory:
    extra_fields.setdefault("slug", "demo-category")
    extra_fields.setdefault("name", "Demo category")
    extra_fields.setdefault("name_ru", "Демо категория")
    extra_fields.setdefault("name_en", "Demo category")
    return FoodCategory.objects.create(**extra_fields)


def make_food_data_source(**extra_fields: Any) -> FoodDataSource:
    extra_fields.setdefault("code", "demo-source")
    extra_fields.setdefault("name", "Demo source")
    extra_fields.setdefault("source_type", FoodDataSource.SourceType.DEMO)
    extra_fields.setdefault("source_reference", "Demo source reference")
    return FoodDataSource.objects.create(**extra_fields)


def make_nutrient(**extra_fields: Any) -> Nutrient:
    extra_fields.setdefault("code", "energy_kcal")
    extra_fields.setdefault("name", "Energy")
    extra_fields.setdefault("name_ru", "Энергия")
    extra_fields.setdefault("name_en", "Energy")
    extra_fields.setdefault("unit", "kcal")
    extra_fields.setdefault("nutrient_type", Nutrient.NutrientType.ENERGY)
    return Nutrient.objects.create(**extra_fields)


def make_food_item(**extra_fields: Any) -> FoodItem:
    if "category" not in extra_fields:
        extra_fields["category"] = make_food_category()
    if "data_source" not in extra_fields:
        extra_fields["data_source"] = make_food_data_source()
    extra_fields.setdefault("name", "Apple, raw")
    extra_fields.setdefault("name_ru", "Яблоко сырое")
    extra_fields.setdefault("name_en", "Apple, raw")
    extra_fields.setdefault("synonyms", ["apple", "яблоко"])
    extra_fields.setdefault("density_metadata", {"basis": "demo"})
    extra_fields.setdefault("is_verified", True)
    extra_fields.setdefault("source_reference", "Demo values per 100 g")
    return FoodItem.objects.create(**extra_fields)


def make_food_nutrient(**extra_fields: Any) -> FoodNutrient:
    if "food_item" not in extra_fields:
        extra_fields["food_item"] = make_food_item()
    if "nutrient" not in extra_fields:
        extra_fields["nutrient"] = make_nutrient()
    extra_fields.setdefault("amount_per_100g", Decimal("52.0000"))
    extra_fields.setdefault("source_reference", "Demo values per 100 g")
    return FoodNutrient.objects.create(**extra_fields)
