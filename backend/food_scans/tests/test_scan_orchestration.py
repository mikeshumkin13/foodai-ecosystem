from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from accounts.tests.factories import make_user
from diary.models import Meal, MealItem
from food_scans.models import FoodScan
from food_scans.orchestration import add_manual_detected_item, start_scan_analysis
from integrations.vision.client import (
    VisionAnalyzeResult,
    VisionDetectedItem,
    VisionObjectReference,
    VisionUnavailableError,
)
from nutrition.models import FoodItem, FoodNutrient, Nutrient
from nutrition.tests.factories import make_food_category, make_food_data_source, make_food_item

pytestmark = pytest.mark.django_db


class _FakeVisionClient:
    def __init__(self, *items: VisionDetectedItem) -> None:
        self.items = items
        self.reference: VisionObjectReference | None = None

    def analyze_object(self, object_reference: VisionObjectReference) -> VisionAnalyzeResult:
        self.reference = object_reference
        return VisionAnalyzeResult(items=self.items)


class _UnavailableVisionClient:
    def analyze_object(self, object_reference: VisionObjectReference) -> VisionAnalyzeResult:
        raise VisionUnavailableError


def _results_url(food_scan_id: object) -> str:
    return reverse("food-scan-results", kwargs={"id": food_scan_id})


def _items_url(food_scan_id: object) -> str:
    return reverse("food-scan-items", kwargs={"id": food_scan_id})


def _item_url(food_scan_id: object, item_id: object) -> str:
    return reverse("food-scan-item", kwargs={"id": food_scan_id, "item_id": item_id})


def _confirm_url(food_scan_id: object) -> str:
    return reverse("food-scan-confirm", kwargs={"id": food_scan_id})


def test_scan_analysis_matches_catalog_and_does_not_create_meal() -> None:
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    food_scan = _make_food_scan()
    vision_client = _FakeVisionClient(VisionDetectedItem(label="rice", confidence=0.92))

    analyzed_scan = start_scan_analysis(food_scan, vision_client=vision_client)

    assert vision_client.reference is not None
    assert analyzed_scan.status == FoodScan.Status.NEEDS_CONFIRMATION
    assert Meal.objects.count() == 0
    detected_item = analyzed_scan.detected_items.get()
    assert detected_item.label == "rice"
    assert detected_item.confidence == Decimal("0.9200")
    assert detected_item.matched_food == rice
    assert detected_item.estimated_mass_g == Decimal("100.00")
    assert detected_item.calories_kcal == Decimal("130.0000")
    assert detected_item.nutrient_snapshot["energy_kcal"]["amount"] == "130.0000"


def test_scan_analysis_marks_scan_failed_when_vision_is_unavailable() -> None:
    food_scan = _make_food_scan()

    analyzed_scan = start_scan_analysis(
        food_scan,
        vision_client=_UnavailableVisionClient(),
    )

    assert analyzed_scan.status == FoodScan.Status.FAILED
    assert analyzed_scan.failure_code == "vision_unavailable"
    assert analyzed_scan.detected_items.count() == 0


def test_user_can_review_correct_delete_add_and_confirm_scan(
    api_client: APIClient,
) -> None:
    user = make_user()
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    chicken = _food_with_nutrients(
        name="Chicken breast, cooked",
        synonyms=["chicken"],
        energy="165.0000",
        protein="31.0000",
        fat="3.6000",
        carbs="0.0000",
    )
    food_scan = _make_food_scan(user=user)
    start_scan_analysis(
        food_scan,
        vision_client=_FakeVisionClient(VisionDetectedItem(label="rice", confidence=0.92)),
    )
    detected_item = food_scan.detected_items.get()
    api_client.force_authenticate(user=user)

    results_response = api_client.get(_results_url(food_scan.id))
    update_response = api_client.patch(
        _item_url(food_scan.id, detected_item.id),
        {"food_id": str(chicken.id), "mass_g": "125.50"},
        format="json",
    )
    delete_response = api_client.delete(_item_url(food_scan.id, detected_item.id))
    add_response = api_client.post(
        _items_url(food_scan.id),
        {"food_id": str(rice.id), "mass_g": "200.00", "label": "rice bowl"},
        format="json",
    )
    confirm_response = api_client.post(
        _confirm_url(food_scan.id),
        {
            "meal_type": Meal.MealType.LUNCH,
            "logged_at": "2026-08-14T12:30:00Z",
            "name": "Lunch scan",
        },
        format="json",
    )

    assert results_response.status_code == status.HTTP_200_OK
    assert results_response.json()["detected_items"][0]["food_id"] == str(rice.id)
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["food_id"] == str(chicken.id)
    assert update_response.json()["mass_g"] == "125.50"
    assert update_response.json()["manually_corrected"] is True
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert add_response.status_code == status.HTTP_201_CREATED
    assert add_response.json()["source"] == "manual"
    assert confirm_response.status_code == status.HTTP_201_CREATED

    payload = confirm_response.json()
    assert payload["food_scan"]["status"] == FoodScan.Status.CONFIRMED
    assert payload["meal"]["meal_type"] == Meal.MealType.LUNCH
    assert payload["meal"]["name"] == "Lunch scan"
    assert len(payload["meal"]["items"]) == 1
    item_payload = payload["meal"]["items"][0]
    assert item_payload["food_id"] == str(rice.id)
    assert item_payload["mass_g"] == "200.00"
    assert item_payload["calories"] == "260.0000"
    assert item_payload["source"] == MealItem.Source.MANUAL
    assert Meal.objects.count() == 1
    assert MealItem.objects.count() == 1


def test_confirm_uses_scan_item_snapshot_even_if_catalog_changes_before_confirm(
    api_client: APIClient,
) -> None:
    user = make_user()
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    food_scan = _make_food_scan(user=user, status=FoodScan.Status.NEEDS_CONFIRMATION)
    add_manual_detected_item(
        food_scan=food_scan,
        matched_food=rice,
        mass_g=Decimal("150.00"),
        label="rice",
    )
    energy_value = rice.nutrient_values.get(nutrient__code="energy_kcal")
    energy_value.amount_per_100g = Decimal("999.0000")
    energy_value.save(update_fields=["amount_per_100g", "updated_at"])
    rice.name = "Rice, changed"
    rice.save(update_fields=["name", "updated_at"])
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _confirm_url(food_scan.id),
        {
            "meal_type": Meal.MealType.DINNER,
            "logged_at": "2026-08-14T18:30:00Z",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    item_payload = response.json()["meal"]["items"][0]
    assert item_payload["food_name_snapshot"] == "Rice, cooked"
    assert item_payload["calories"] == "195.0000"
    assert item_payload["nutrient_snapshot"]["energy_kcal"]["amount_per_100g"] == "130.0000"


def test_confirm_requires_all_detected_items_to_have_food_match(api_client: APIClient) -> None:
    user = make_user()
    food_scan = _make_food_scan(user=user)
    start_scan_analysis(
        food_scan,
        vision_client=_FakeVisionClient(VisionDetectedItem(label="unknown food", confidence=0.91)),
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _confirm_url(food_scan.id),
        {
            "meal_type": Meal.MealType.SNACK,
            "logged_at": "2026-08-14T16:30:00Z",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == ["detected_items_require_food_match"]
    assert response.json()["item_ids"] == [str(food_scan.detected_items.get().id)]
    assert Meal.objects.count() == 0


def test_idor_user_cannot_access_or_confirm_another_users_scan(
    api_client: APIClient,
) -> None:
    user_a = make_user()
    user_b = make_user()
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    food_scan = _make_food_scan(user=user_b, status=FoodScan.Status.NEEDS_CONFIRMATION)
    detected_item = add_manual_detected_item(
        food_scan=food_scan,
        matched_food=rice,
        mass_g=Decimal("100.00"),
        label="rice",
    )
    api_client.force_authenticate(user=user_a)

    results_response = api_client.get(_results_url(food_scan.id))
    update_response = api_client.patch(
        _item_url(food_scan.id, detected_item.id),
        {"mass_g": "120.00"},
        format="json",
    )
    add_response = api_client.post(
        _items_url(food_scan.id),
        {"food_id": str(rice.id), "mass_g": "120.00"},
        format="json",
    )
    confirm_response = api_client.post(
        _confirm_url(food_scan.id),
        {
            "meal_type": Meal.MealType.LUNCH,
            "logged_at": "2026-08-14T12:30:00Z",
        },
        format="json",
    )

    assert results_response.status_code == status.HTTP_404_NOT_FOUND
    assert update_response.status_code == status.HTTP_404_NOT_FOUND
    assert add_response.status_code == status.HTTP_404_NOT_FOUND
    assert confirm_response.status_code == status.HTTP_404_NOT_FOUND
    assert Meal.objects.count() == 0


def _make_food_scan(
    *,
    user: User | None = None,
    status: str = FoodScan.Status.UPLOADED,
) -> FoodScan:
    scan_id = uuid.uuid4()
    return FoodScan.objects.create(
        id=scan_id,
        user=user or make_user(),
        status=status,
        storage_backend="local",
        object_key=f"food-scans/test/{scan_id.hex}.jpg",
        image_format=FoodScan.ImageFormat.JPEG,
        content_type="image/jpeg",
        uploaded_byte_size=128,
        stored_byte_size=120,
        width=12,
        height=10,
        checksum_sha256="b" * 64,
    )


def _food_with_nutrients(
    *,
    name: str,
    synonyms: list[str],
    energy: str,
    protein: str = "2.7000",
    fat: str = "0.3000",
    carbs: str = "28.0000",
) -> FoodItem:
    suffix = uuid.uuid4().hex[:8]
    category = make_food_category(slug=f"category-{suffix}", name=f"{name} category")
    data_source = make_food_data_source(code=f"source-{suffix}")
    food_item = make_food_item(
        category=category,
        data_source=data_source,
        name=name,
        name_ru="",
        name_en=name,
        synonyms=synonyms,
        source_reference=f"{name} demo values per 100 g",
    )
    _make_food_nutrient(food_item, code="energy_kcal", amount=energy)
    _make_food_nutrient(food_item, code="protein", amount=protein)
    _make_food_nutrient(food_item, code="fat", amount=fat)
    _make_food_nutrient(food_item, code="carbohydrate", amount=carbs)
    return food_item


def _make_food_nutrient(food_item: FoodItem, *, code: str, amount: str) -> None:
    nutrient = _get_or_create_nutrient(code)
    FoodNutrient.objects.create(
        food_item=food_item,
        nutrient=nutrient,
        amount_per_100g=Decimal(amount),
        source_reference="Demo values per 100 g",
    )


def _get_or_create_nutrient(code: str) -> Nutrient:
    nutrient_defaults = {
        "energy_kcal": {
            "name": "Energy",
            "name_ru": "Энергия",
            "name_en": "Energy",
            "unit": "kcal",
            "nutrient_type": Nutrient.NutrientType.ENERGY,
        },
        "protein": {
            "name": "Protein",
            "name_ru": "Белки",
            "name_en": "Protein",
            "unit": "g",
            "nutrient_type": Nutrient.NutrientType.MACRONUTRIENT,
        },
        "fat": {
            "name": "Fat",
            "name_ru": "Жиры",
            "name_en": "Fat",
            "unit": "g",
            "nutrient_type": Nutrient.NutrientType.MACRONUTRIENT,
        },
        "carbohydrate": {
            "name": "Carbohydrate",
            "name_ru": "Углеводы",
            "name_en": "Carbohydrate",
            "unit": "g",
            "nutrient_type": Nutrient.NutrientType.MACRONUTRIENT,
        },
    }
    return Nutrient.objects.get_or_create(code=code, defaults=nutrient_defaults[code])[0]
