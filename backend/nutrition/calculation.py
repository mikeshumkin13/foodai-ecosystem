from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from types import MappingProxyType
from typing import Any

from nutrition.models import FoodItem

INTERNAL_MASS_UNIT = "g"
CATALOG_NUTRIENT_BASIS_GRAMS = Decimal("100")
NUTRIENT_QUANT = Decimal("0.0001")

ENERGY_NUTRIENT_CODE = "energy_kcal"
PROTEIN_NUTRIENT_CODE = "protein"
FAT_NUTRIENT_CODE = "fat"
CARBOHYDRATE_NUTRIENT_CODE = "carbohydrate"


@dataclass(frozen=True)
class CalculatedNutrient:
    code: str
    name: str
    name_ru: str
    name_en: str
    unit: str
    nutrient_type: str
    amount: Decimal
    amount_per_100g: Decimal
    source_reference: str

    def to_snapshot_payload(self) -> dict[str, str]:
        return {
            "name": self.name,
            "name_ru": self.name_ru,
            "name_en": self.name_en,
            "unit": self.unit,
            "nutrient_type": self.nutrient_type,
            "amount": str(self.amount),
            "amount_per_100g": str(self.amount_per_100g),
            "source_reference": self.source_reference,
        }


@dataclass(frozen=True)
class NutritionCalculation:
    food: FoodItem
    mass_g: Decimal
    kcal: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbohydrates_g: Decimal
    nutrients: Mapping[str, CalculatedNutrient]
    micronutrients: Mapping[str, CalculatedNutrient]

    @property
    def calories_kcal(self) -> Decimal:
        return self.kcal

    @property
    def carbs_g(self) -> Decimal:
        return self.carbohydrates_g

    def to_snapshot(self) -> dict[str, Any]:
        nutrient_snapshot = {
            code: nutrient.to_snapshot_payload() for code, nutrient in self.nutrients.items()
        }
        micronutrient_snapshot = {
            code: nutrient.to_snapshot_payload() for code, nutrient in self.micronutrients.items()
        }
        return {
            "food_name_snapshot": self.food.name,
            "food_source_reference_snapshot": self.food.source_reference,
            "calories_kcal": self.kcal,
            "protein_g": self.protein_g,
            "fat_g": self.fat_g,
            "carbs_g": self.carbohydrates_g,
            "nutrient_snapshot": nutrient_snapshot,
            "micronutrient_snapshot": micronutrient_snapshot,
        }


def calculate_food_nutrition(*, food: FoodItem, mass_g: Decimal) -> NutritionCalculation:
    normalized_mass_g = _normalize_mass(mass_g)
    scale = normalized_mass_g / CATALOG_NUTRIENT_BASIS_GRAMS
    calculated_nutrients: dict[str, CalculatedNutrient] = {}
    calculated_micronutrients: dict[str, CalculatedNutrient] = {}

    kcal = Decimal("0.0000")
    protein_g = Decimal("0.0000")
    fat_g = Decimal("0.0000")
    carbohydrates_g = Decimal("0.0000")

    for food_nutrient in food.nutrient_values.select_related("nutrient"):
        nutrient = food_nutrient.nutrient
        amount_per_100g = _quantize(food_nutrient.amount_per_100g)
        amount = _quantize(amount_per_100g * scale)
        calculated_nutrient = CalculatedNutrient(
            code=nutrient.code,
            name=nutrient.name,
            name_ru=nutrient.name_ru,
            name_en=nutrient.name_en,
            unit=nutrient.unit,
            nutrient_type=nutrient.nutrient_type,
            amount=amount,
            amount_per_100g=amount_per_100g,
            source_reference=food_nutrient.source_reference,
        )
        calculated_nutrients[nutrient.code] = calculated_nutrient

        if nutrient.code == ENERGY_NUTRIENT_CODE:
            kcal = amount
        elif nutrient.code == PROTEIN_NUTRIENT_CODE:
            protein_g = amount
        elif nutrient.code == FAT_NUTRIENT_CODE:
            fat_g = amount
        elif nutrient.code == CARBOHYDRATE_NUTRIENT_CODE:
            carbohydrates_g = amount

        if nutrient.nutrient_type == "micronutrient":
            calculated_micronutrients[nutrient.code] = calculated_nutrient

    return NutritionCalculation(
        food=food,
        mass_g=normalized_mass_g,
        kcal=kcal,
        protein_g=protein_g,
        fat_g=fat_g,
        carbohydrates_g=carbohydrates_g,
        nutrients=MappingProxyType(calculated_nutrients),
        micronutrients=MappingProxyType(calculated_micronutrients),
    )


def build_food_nutrition_snapshot(*, food: FoodItem, mass_g: Decimal) -> dict[str, Any]:
    return calculate_food_nutrition(food=food, mass_g=mass_g).to_snapshot()


def _normalize_mass(mass_g: Decimal) -> Decimal:
    if mass_g < 0:
        raise ValueError("mass_g_must_be_non_negative")
    return mass_g


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(NUTRIENT_QUANT, rounding=ROUND_HALF_UP)
