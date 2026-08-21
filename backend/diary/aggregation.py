from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from diary.models import Meal, MealItem


def aggregate_meals(meals: Iterable[Meal]) -> dict[str, Any]:
    totals = {
        "calories": Decimal("0.0000"),
        "protein": Decimal("0.0000"),
        "fat": Decimal("0.0000"),
        "carbs": Decimal("0.0000"),
    }
    micronutrient_totals: dict[str, dict[str, Any]] = {}

    for meal in meals:
        for item in meal.items.all():
            totals["calories"] += item.calories_kcal
            totals["protein"] += item.protein_g
            totals["fat"] += item.fat_g
            totals["carbs"] += item.carbs_g
            _add_micronutrients(micronutrient_totals, item)

    serialized_micronutrients = {
        code: {**payload, "amount": str(payload["amount"])}
        for code, payload in micronutrient_totals.items()
    }

    return {
        "totals": {key: str(value) for key, value in totals.items()},
        "micronutrient_totals": serialized_micronutrients,
    }


def _add_micronutrients(
    micronutrient_totals: dict[str, dict[str, Any]],
    item: MealItem,
) -> None:
    for code, payload in item.micronutrient_snapshot.items():
        if not isinstance(payload, dict):
            continue
        amount = Decimal(str(payload.get("amount", "0")))
        existing_payload = micronutrient_totals.setdefault(
            code,
            {
                "name": payload.get("name", ""),
                "name_ru": payload.get("name_ru", ""),
                "name_en": payload.get("name_en", ""),
                "unit": payload.get("unit", ""),
                "amount": Decimal("0.0000"),
            },
        )
        existing_payload["amount"] += amount
        existing_payload["amount"] = existing_payload["amount"].quantize(Decimal("0.0001"))
