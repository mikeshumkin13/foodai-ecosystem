from __future__ import annotations

from decimal import Decimal

import pytest

from food_scans.portion_estimation import estimate_food_portion
from integrations.vision.client import VisionPortionReference
from nutrition.tests.factories import make_food_category, make_food_data_source, make_food_item

pytestmark = pytest.mark.django_db


def test_portion_estimation_uses_segment_area_plate_reference_and_food_density() -> None:
    food = make_food_item(
        category=make_food_category(slug="grains", name="Grains"),
        data_source=make_food_data_source(code="portion-source"),
        name="Rice, cooked",
        synonyms=["rice"],
        density_g_per_ml=Decimal("0.7500"),
    )

    estimate = estimate_food_portion(
        food=food,
        label="rice",
        recognition_confidence=Decimal("0.9200"),
        segment_area_px=Decimal("10000.00"),
        portion_reference=VisionPortionReference(
            reference_type="plate",
            diameter_cm=26.0,
            area_px=40000.0,
        ),
    )

    assert estimate.method == "segment_area_plate_reference_geometry_v1"
    assert estimate.estimated_volume_ml == Decimal("292.01")
    assert estimate.estimated_mass_g == Decimal("219.01")
    assert estimate.min_estimate_g == Decimal("142.36")
    assert estimate.max_estimate_g == Decimal("317.56")
    assert estimate.confidence == Decimal("0.5952")
    assert estimate.metadata["density_source"] == "food_item_density"
    assert estimate.metadata["assumed_depth_cm"] == "2.20"


def test_portion_estimation_uses_typical_volume_when_reference_is_missing() -> None:
    food = make_food_item(
        category=make_food_category(slug="protein-foods", name="Protein foods"),
        data_source=make_food_data_source(code="portion-source"),
        name="Chicken breast, cooked",
        synonyms=["chicken"],
    )

    estimate = estimate_food_portion(
        food=food,
        label="chicken",
        recognition_confidence=Decimal("0.8000"),
        segment_area_px=None,
        portion_reference=None,
    )

    assert estimate.method == "food_type_typical_volume_density_table_v1"
    assert estimate.estimated_volume_ml == Decimal("120.00")
    assert estimate.estimated_mass_g == Decimal("114.00")
    assert estimate.min_estimate_g == Decimal("57.00")
    assert estimate.max_estimate_g == Decimal("205.20")
    assert estimate.confidence == Decimal("0.3060")
    assert estimate.metadata["density_source"] == "density_table:protein_foods"
    assert estimate.metadata["geometric_assumption"] == "no reliable physical reference supplied"


def test_portion_estimation_can_use_density_metadata() -> None:
    food = make_food_item(
        category=make_food_category(slug="fruits", name="Fruits"),
        data_source=make_food_data_source(code="portion-source"),
        name="Apple, raw",
        synonyms=["apple"],
        density_g_per_ml=None,
        density_metadata={"density_g_per_ml": "0.6410", "basis": "demo"},
    )

    estimate = estimate_food_portion(
        food=food,
        label="apple",
        recognition_confidence=None,
        segment_area_px=None,
        portion_reference=None,
    )

    assert estimate.estimated_mass_g == Decimal("108.97")
    assert estimate.metadata["density_source"] == "food_density_metadata"


def test_portion_estimation_falls_back_to_label_type_when_food_is_unmatched() -> None:
    estimate = estimate_food_portion(
        food=None,
        label="rice bowl",
        recognition_confidence=Decimal("0.5000"),
        segment_area_px=None,
        portion_reference=None,
    )

    assert estimate.estimated_mass_g == Decimal("144.00")
    assert estimate.metadata["food_type"] == "grains"
    assert estimate.metadata["density_source"] == "density_table:grains"
