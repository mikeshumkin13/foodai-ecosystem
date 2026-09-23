from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from nutrition.models import FoodCategory, FoodItem, FoodNutrient, Nutrient
from nutrition.tests.factories import make_nutrient

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True, SETTINGS_MODULE="config.settings.local")
def test_demo_seed_reuses_natural_keys_and_preserves_existing_values() -> None:
    existing = make_nutrient(name="Existing energy")
    call_command("seed_demo_catalog", stdout=StringIO())
    assert FoodItem.objects.count() == 3
    assert Nutrient.objects.filter(code="energy_kcal").count() == 1
    assert FoodNutrient.objects.filter(nutrient=existing).count() == 3
    existing.refresh_from_db()
    assert existing.name == "Existing energy"
    food = FoodItem.objects.first()
    assert food is not None
    food.name = "Edited by content manager"
    food.save()
    before = list(FoodNutrient.objects.order_by("id").values())

    call_command("seed_demo_catalog", stdout=StringIO())

    food.refresh_from_db()
    assert food.name == "Edited by content manager"
    assert FoodItem.objects.count() == 3
    assert list(FoodNutrient.objects.order_by("id").values()) == before


@override_settings(DEBUG=True, SETTINGS_MODULE="config.settings.local")
def test_demo_seed_rolls_back_on_incompatible_units() -> None:
    make_nutrient(unit="kJ")
    with pytest.raises(CommandError, match="unit differs"):
        call_command("seed_demo_catalog", stdout=StringIO())
    assert not FoodCategory.objects.exists()
    assert not FoodItem.objects.exists()
    assert Nutrient.objects.get(code="energy_kcal").unit == "kJ"


@pytest.mark.parametrize(
    ("debug", "module"), [(False, "config.settings.local"), (True, "config.settings.production")]
)
def test_demo_seed_is_refused_outside_local_debug(debug: bool, module: str) -> None:
    with override_settings(DEBUG=debug, SETTINGS_MODULE=module):
        with pytest.raises(CommandError, match="only with local"):
            call_command("seed_demo_catalog")
    assert not FoodItem.objects.exists()
