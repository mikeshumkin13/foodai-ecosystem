from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from nutrition.models import FoodItem

QUANT = Decimal("0.0001")
MASS_BASE_GRAMS = Decimal("100")

MACRO_NUTRIENT_FIELDS = {
    "energy_kcal": "calories_kcal",
    "protein": "protein_g",
    "fat": "fat_g",
    "carbohydrate": "carbs_g",
}


def build_food_snapshot(food: FoodItem, mass_g: Decimal) -> dict[str, Any]:
    scale = mass_g / MASS_BASE_GRAMS
    macros = {
        "calories_kcal": Decimal("0.0000"),
        "protein_g": Decimal("0.0000"),
        "fat_g": Decimal("0.0000"),
        "carbs_g": Decimal("0.0000"),
    }
    nutrient_snapshot: dict[str, dict[str, str]] = {}
    micronutrient_snapshot: dict[str, dict[str, str]] = {}

    for food_nutrient in food.nutrient_values.select_related("nutrient"):
        nutrient = food_nutrient.nutrient
        amount = _quantize(food_nutrient.amount_per_100g * scale)
        nutrient_payload = {
            "name": nutrient.name,
            "name_ru": nutrient.name_ru,
            "name_en": nutrient.name_en,
            "unit": nutrient.unit,
            "nutrient_type": nutrient.nutrient_type,
            "amount": str(amount),
            "amount_per_100g": str(_quantize(food_nutrient.amount_per_100g)),
            "source_reference": food_nutrient.source_reference,
        }
        nutrient_snapshot[nutrient.code] = nutrient_payload

        macro_field = MACRO_NUTRIENT_FIELDS.get(nutrient.code)
        if macro_field is not None:
            macros[macro_field] = amount
        if nutrient.nutrient_type == "micronutrient":
            micronutrient_snapshot[nutrient.code] = nutrient_payload

    return {
        **macros,
        "food_name_snapshot": food.name,
        "food_source_reference_snapshot": food.source_reference,
        "nutrient_snapshot": nutrient_snapshot,
        "micronutrient_snapshot": micronutrient_snapshot,
    }


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(QUANT, rounding=ROUND_HALF_UP)
