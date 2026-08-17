from __future__ import annotations

from decimal import Decimal
from typing import Any

from nutrition.calculation import build_food_nutrition_snapshot
from nutrition.models import FoodItem


def build_food_snapshot(food: FoodItem, mass_g: Decimal) -> dict[str, Any]:
    return build_food_nutrition_snapshot(food=food, mass_g=mass_g)
