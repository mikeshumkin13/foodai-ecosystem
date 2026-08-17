from __future__ import annotations

from decimal import Decimal

import pytest

from nutrition.calculation import (
    CATALOG_NUTRIENT_BASIS_GRAMS,
    INTERNAL_MASS_UNIT,
    calculate_food_nutrition,
)
from nutrition.models import FoodItem, Nutrient
from nutrition.tests.factories import make_food_item, make_food_nutrient, make_nutrient

pytestmark = pytest.mark.django_db


def test_calculation_uses_grams_as_internal_mass_unit_and_100g_catalog_basis() -> None:
    assert INTERNAL_MASS_UNIT == "g"
    assert CATALOG_NUTRIENT_BASIS_GRAMS == Decimal("100")


def test_calculation_returns_zero_amounts_for_0g() -> None:
    food = _food_with_complete_nutrients()

    result = calculate_food_nutrition(food=food, mass_g=Decimal("0.00"))

    assert result.mass_g == Decimal("0.00")
    assert result.kcal == Decimal("0.0000")
    assert result.protein_g == Decimal("0.0000")
    assert result.fat_g == Decimal("0.0000")
    assert result.carbohydrates_g == Decimal("0.0000")
    assert result.micronutrients["vitamin_c"].amount == Decimal("0.0000")


def test_calculation_scales_nutrients_for_50g() -> None:
    food = _food_with_complete_nutrients()

    result = calculate_food_nutrition(food=food, mass_g=Decimal("50.00"))

    assert result.kcal == Decimal("65.0000")
    assert result.protein_g == Decimal("1.3500")
    assert result.fat_g == Decimal("0.1500")
    assert result.carbohydrates_g == Decimal("14.0000")
    assert result.micronutrients["vitamin_c"].amount == Decimal("2.3000")


def test_calculation_returns_per_100g_values_for_100g() -> None:
    food = _food_with_complete_nutrients()

    result = calculate_food_nutrition(food=food, mass_g=Decimal("100.00"))

    assert result.kcal == Decimal("130.0000")
    assert result.protein_g == Decimal("2.7000")
    assert result.fat_g == Decimal("0.3000")
    assert result.carbohydrates_g == Decimal("28.0000")
    assert result.micronutrients["vitamin_c"].amount == Decimal("4.6000")
    assert result.nutrients["energy_kcal"].amount_per_100g == Decimal("130.0000")


def test_calculation_scales_nutrients_for_250g() -> None:
    food = _food_with_complete_nutrients()

    result = calculate_food_nutrition(food=food, mass_g=Decimal("250.00"))

    assert result.kcal == Decimal("325.0000")
    assert result.protein_g == Decimal("6.7500")
    assert result.fat_g == Decimal("0.7500")
    assert result.carbohydrates_g == Decimal("70.0000")
    assert result.micronutrients["vitamin_c"].amount == Decimal("11.5000")


def test_calculation_returns_zero_for_missing_macro_nutrient() -> None:
    food = make_food_item()
    make_food_nutrient(
        food_item=food,
        nutrient=_nutrient(
            code="energy_kcal",
            unit="kcal",
            nutrient_type=Nutrient.NutrientType.ENERGY,
        ),
        amount_per_100g=Decimal("52.0000"),
    )

    result = calculate_food_nutrition(food=food, mass_g=Decimal("100.00"))

    assert result.kcal == Decimal("52.0000")
    assert result.protein_g == Decimal("0.0000")
    assert result.fat_g == Decimal("0.0000")
    assert result.carbohydrates_g == Decimal("0.0000")
    assert "protein" not in result.nutrients
    assert result.micronutrients == {}


def test_calculation_rejects_negative_mass() -> None:
    food = _food_with_complete_nutrients()

    with pytest.raises(ValueError, match="mass_g_must_be_non_negative"):
        calculate_food_nutrition(food=food, mass_g=Decimal("-0.01"))


def test_calculation_snapshot_payload_uses_stable_snapshot_shape() -> None:
    food = _food_with_complete_nutrients()

    snapshot = calculate_food_nutrition(food=food, mass_g=Decimal("50.00")).to_snapshot()

    assert snapshot["food_name_snapshot"] == food.name
    assert snapshot["food_source_reference_snapshot"] == food.source_reference
    assert snapshot["calories_kcal"] == Decimal("65.0000")
    assert snapshot["carbs_g"] == Decimal("14.0000")
    assert snapshot["nutrient_snapshot"]["energy_kcal"]["amount"] == "65.0000"
    assert snapshot["nutrient_snapshot"]["energy_kcal"]["amount_per_100g"] == "130.0000"
    assert snapshot["micronutrient_snapshot"]["vitamin_c"]["amount"] == "2.3000"


def _food_with_complete_nutrients() -> FoodItem:
    food = make_food_item(name="Rice, cooked", source_reference="Demo values per 100 g")
    make_food_nutrient(
        food_item=food,
        nutrient=_nutrient(
            code="energy_kcal",
            unit="kcal",
            nutrient_type=Nutrient.NutrientType.ENERGY,
        ),
        amount_per_100g=Decimal("130.0000"),
    )
    make_food_nutrient(
        food_item=food,
        nutrient=_nutrient(
            code="protein",
            unit="g",
            nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
        ),
        amount_per_100g=Decimal("2.7000"),
    )
    make_food_nutrient(
        food_item=food,
        nutrient=_nutrient(
            code="fat",
            unit="g",
            nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
        ),
        amount_per_100g=Decimal("0.3000"),
    )
    make_food_nutrient(
        food_item=food,
        nutrient=_nutrient(
            code="carbohydrate",
            unit="g",
            nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
        ),
        amount_per_100g=Decimal("28.0000"),
    )
    make_food_nutrient(
        food_item=food,
        nutrient=_nutrient(
            code="vitamin_c",
            unit="mg",
            nutrient_type=Nutrient.NutrientType.MICRONUTRIENT,
        ),
        amount_per_100g=Decimal("4.6000"),
    )
    return food


def _nutrient(*, code: str, unit: str, nutrient_type: str) -> Nutrient:
    return make_nutrient(
        code=code,
        name=code.replace("_", " ").title(),
        name_ru="",
        name_en=code.replace("_", " ").title(),
        unit=unit,
        nutrient_type=nutrient_type,
    )
