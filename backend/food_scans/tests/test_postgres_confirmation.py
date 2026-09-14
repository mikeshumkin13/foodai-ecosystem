from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from diary.models import Meal, MealItem
from food_scans.models import FoodScan
from food_scans.orchestration import add_manual_detected_item, confirm_food_scan
from food_scans.tests.test_background_jobs import _food_with_nutrients, _make_food_scan

pytestmark = pytest.mark.django_db


def test_first_confirmation_locks_scan_with_nullable_meal_and_is_idempotent() -> None:
    food = _food_with_nutrients(name="Rice", synonyms=["rice"], energy="130.0000")
    scan = _make_food_scan(status=FoodScan.Status.NEEDS_CONFIRMATION)
    assert scan.confirmed_meal_id is None
    add_manual_detected_item(
        food_scan=scan, matched_food=food, mass_g=Decimal("100"), label="rice",
    )

    with CaptureQueriesContext(connection) as queries:
        first = confirm_food_scan(
            food_scan=scan, meal_type=Meal.MealType.LUNCH, logged_at=timezone.now(), name="",
        )
        repeated = confirm_food_scan(
            food_scan=scan, meal_type=Meal.MealType.LUNCH, logged_at=timezone.now(), name="",
        )

    assert first.id == repeated.id
    assert Meal.objects.count() == MealItem.objects.count() == 1
    assert first.items.get().calories_kcal == Decimal("130.0000")
    if connection.vendor == "postgresql":
        locks = [query["sql"] for query in queries if "FOR UPDATE" in query["sql"]]
        assert len(locks) == 2
        assert all('FOR UPDATE OF "food_scans_foodscan"' in query for query in locks)
