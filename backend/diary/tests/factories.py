from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone

from accounts.models import User
from accounts.tests.factories import make_user
from diary.models import Meal, MealItem
from diary.snapshots import build_food_snapshot
from nutrition.models import FoodItem
from nutrition.tests.factories import make_food_item


def make_meal(*, user: User | None = None, **extra_fields: Any) -> Meal:
    resolved_user = user or make_user()
    extra_fields.setdefault("meal_type", Meal.MealType.BREAKFAST)
    extra_fields.setdefault("logged_at", timezone.now())
    return Meal.objects.create(user=resolved_user, **extra_fields)


def make_meal_item(
    *,
    meal: Meal | None = None,
    food: FoodItem | None = None,
    **extra_fields: Any,
) -> MealItem:
    resolved_meal = meal or make_meal()
    resolved_food = food or make_food_item()
    mass_g = extra_fields.pop("mass_g", Decimal("100.00"))
    snapshot = build_food_snapshot(resolved_food, mass_g)
    extra_fields.setdefault("food_name_snapshot", snapshot["food_name_snapshot"])
    extra_fields.setdefault(
        "food_source_reference_snapshot",
        snapshot["food_source_reference_snapshot"],
    )
    extra_fields.setdefault("calories_kcal", snapshot["calories_kcal"])
    extra_fields.setdefault("protein_g", snapshot["protein_g"])
    extra_fields.setdefault("fat_g", snapshot["fat_g"])
    extra_fields.setdefault("carbs_g", snapshot["carbs_g"])
    extra_fields.setdefault("micronutrient_snapshot", snapshot["micronutrient_snapshot"])
    extra_fields.setdefault("nutrient_snapshot", snapshot["nutrient_snapshot"])
    extra_fields.setdefault("source", MealItem.Source.FOOD_CATALOG)
    return MealItem.objects.create(
        meal=resolved_meal,
        food=resolved_food,
        mass_g=mass_g,
        **extra_fields,
    )
