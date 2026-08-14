from __future__ import annotations

from nutrition.models import FoodItem


def match_food_label(label: str) -> FoodItem | None:
    normalized_label = _normalize(label)
    if not normalized_label:
        return None

    food_items = FoodItem.objects.select_related(
        "canonical_food",
        "category",
        "data_source",
    ).order_by("-is_verified", "name", "id")

    for food_item in food_items:
        if _has_exact_match(food_item, normalized_label):
            return _canonical_food(food_item)

    for food_item in food_items:
        if _has_contains_match(food_item, normalized_label):
            return _canonical_food(food_item)

    return None


def _canonical_food(food_item: FoodItem) -> FoodItem:
    return food_item.canonical_food or food_item


def _has_exact_match(food_item: FoodItem, normalized_label: str) -> bool:
    return any(_normalize(value) == normalized_label for value in _searchable_values(food_item))


def _has_contains_match(food_item: FoodItem, normalized_label: str) -> bool:
    return any(normalized_label in _normalize(value) for value in _searchable_values(food_item))


def _searchable_values(food_item: FoodItem) -> list[str]:
    values = [food_item.name, food_item.name_ru, food_item.name_en]
    values.extend(value for value in food_item.synonyms if isinstance(value, str))
    return values


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())
