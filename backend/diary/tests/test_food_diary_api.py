from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.rbac import (
    CHANGE_OWN_MEAL_PERMISSION,
    VIEW_OWN_MEAL_PERMISSION,
    Role,
    assign_role,
)
from accounts.tests.factories import make_superuser, make_user
from diary.models import Meal, MealItem
from diary.tests.factories import make_meal, make_meal_item
from nutrition.models import FoodItem, FoodNutrient, Nutrient
from nutrition.tests.factories import make_food_item, make_food_nutrient, make_nutrient

pytestmark = pytest.mark.django_db


def _meal_detail_url(meal_id: object) -> str:
    return reverse("meal-detail", kwargs={"id": meal_id})


def _logged_at(day: int, hour: int = 9) -> str:
    return datetime(2026, 8, day, hour, 30, tzinfo=timezone.get_current_timezone()).isoformat()


def _food_with_nutrients() -> FoodItem:
    food_item = make_food_item(name="Apple, raw", source_reference="FoodAI demo values per 100 g")
    make_food_nutrient(food_item=food_item)
    protein = make_nutrient(
        code="protein",
        name="Protein",
        name_ru="Белки",
        name_en="Protein",
        unit="g",
        nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
    )
    fat = make_nutrient(
        code="fat",
        name="Fat",
        name_ru="Жиры",
        name_en="Fat",
        unit="g",
        nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
    )
    carbs = make_nutrient(
        code="carbohydrate",
        name="Carbohydrate",
        name_ru="Углеводы",
        name_en="Carbohydrate",
        unit="g",
        nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
    )
    vitamin_c = make_nutrient(
        code="vitamin_c",
        name="Vitamin C",
        name_ru="Витамин C",
        name_en="Vitamin C",
        unit="mg",
        nutrient_type=Nutrient.NutrientType.MICRONUTRIENT,
    )
    FoodNutrient.objects.bulk_create(
        [
            FoodNutrient(food_item=food_item, nutrient=protein, amount_per_100g=Decimal("0.2600")),
            FoodNutrient(food_item=food_item, nutrient=fat, amount_per_100g=Decimal("0.1700")),
            FoodNutrient(
                food_item=food_item,
                nutrient=carbs,
                amount_per_100g=Decimal("13.8100"),
            ),
            FoodNutrient(
                food_item=food_item,
                nutrient=vitamin_c,
                amount_per_100g=Decimal("4.6000"),
            ),
        ],
    )
    return food_item


def test_user_role_has_own_meal_permissions() -> None:
    user = make_user()

    assert user.has_perm(VIEW_OWN_MEAL_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_MEAL_PERMISSION) is True


def test_meals_endpoint_denies_anonymous_user(api_client: APIClient) -> None:
    response = api_client.get(reverse("meal-list"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_can_create_meal_with_snapshot_items(api_client: APIClient) -> None:
    user = make_user()
    food_item = _food_with_nutrients()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("meal-list"),
        {
            "meal_type": Meal.MealType.BREAKFAST,
            "logged_at": _logged_at(12),
            "items": [
                {
                    "food_id": str(food_item.id),
                    "mass_g": "150.00",
                    "source": MealItem.Source.FOOD_CATALOG,
                    "confidence": "0.8750",
                },
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["user_id"] == str(user.id)
    assert payload["meal_type"] == Meal.MealType.BREAKFAST
    item_payload = payload["items"][0]
    assert item_payload["food_id"] == str(food_item.id)
    assert item_payload["food_name_snapshot"] == "Apple, raw"
    assert item_payload["mass_g"] == "150.00"
    assert item_payload["calories"] == "78.0000"
    assert item_payload["protein"] == "0.3900"
    assert item_payload["fat"] == "0.2550"
    assert item_payload["carbs"] == "20.7150"
    assert item_payload["micronutrient_snapshot"]["vitamin_c"]["amount"] == "6.9000"


def test_meal_item_snapshot_does_not_change_when_food_catalog_changes(
    api_client: APIClient,
) -> None:
    user = make_user()
    food_item = _food_with_nutrients()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("meal-list"),
        {
            "meal_type": Meal.MealType.SNACK,
            "logged_at": _logged_at(12, 16),
            "items": [{"food_id": str(food_item.id), "mass_g": "100.00"}],
        },
        format="json",
    )
    meal_id = response.json()["id"]
    item = Meal.objects.get(id=meal_id).items.get()
    assert item.calories_kcal == Decimal("52.0000")

    food_item.name = "Apple, updated"
    food_item.source_reference = "Changed source"
    food_item.save()
    energy = food_item.nutrient_values.get(nutrient__code="energy_kcal")
    energy.amount_per_100g = Decimal("999.0000")
    energy.save()

    detail_response = api_client.get(_meal_detail_url(meal_id))

    assert detail_response.status_code == status.HTTP_200_OK
    item_payload = detail_response.json()["items"][0]
    assert item_payload["food_name_snapshot"] == "Apple, raw"
    assert item_payload["food_source_reference_snapshot"] == "FoodAI demo values per 100 g"
    assert item_payload["calories"] == "52.0000"
    assert item_payload["nutrient_snapshot"]["energy_kcal"]["amount_per_100g"] == "52.0000"


def test_user_lists_only_own_meals_and_can_filter_by_dates(api_client: APIClient) -> None:
    user = make_user()
    own_meal = make_meal(
        user=user,
        logged_at=datetime(2026, 8, 12, 9, tzinfo=UTC),
    )
    make_meal(
        user=user,
        logged_at=datetime(2026, 8, 13, 9, tzinfo=UTC),
    )
    make_meal(logged_at=datetime(2026, 8, 12, 10, tzinfo=UTC))
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("meal-list"), {"date": "2026-08-12"})

    assert response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in response.json()] == [str(own_meal.id)]


def test_idor_user_cannot_read_or_update_another_user_meal(api_client: APIClient) -> None:
    user_a = make_user()
    user_b = make_user()
    meal_b = make_meal(user=user_b)
    api_client.force_authenticate(user=user_a)

    read_response = api_client.get(_meal_detail_url(meal_b.id))
    update_response = api_client.patch(
        _meal_detail_url(meal_b.id),
        {"name": "Updated"},
        format="json",
    )

    assert read_response.status_code == status.HTTP_404_NOT_FOUND
    assert update_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_roles_cannot_access_private_meals_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    meal = make_meal()
    api_client.force_authenticate(user=actor)

    list_response = api_client.get(reverse("meal-list"))
    detail_response = api_client.get(_meal_detail_url(meal.id))

    assert list_response.status_code == status.HTTP_403_FORBIDDEN
    assert detail_response.status_code == status.HTTP_403_FORBIDDEN


def test_superuser_can_read_meal_as_technical_override(api_client: APIClient) -> None:
    superuser = make_superuser()
    meal = make_meal()
    api_client.force_authenticate(user=superuser)

    response = api_client.get(_meal_detail_url(meal.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(meal.id)


def test_user_can_patch_own_meal_and_replace_items(api_client: APIClient) -> None:
    user = make_user()
    meal = make_meal(user=user, meal_type=Meal.MealType.LUNCH)
    food_item = _food_with_nutrients()
    old_item = make_meal_item(meal=meal, food=food_item)
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        _meal_detail_url(meal.id),
        {
            "meal_type": Meal.MealType.DINNER,
            "name": "Dinner after training",
            "items": [
                {
                    "food_id": str(food_item.id),
                    "mass_g": "200.00",
                    "calories": "120.0000",
                    "protein": "10.0000",
                    "fat": "2.0000",
                    "carbs": "20.0000",
                    "manually_corrected": True,
                },
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    meal.refresh_from_db()
    assert meal.meal_type == Meal.MealType.DINNER
    assert meal.name == "Dinner after training"
    assert MealItem.objects.filter(id=old_item.id).exists() is False
    item_payload = response.json()["items"][0]
    assert item_payload["calories"] == "120.0000"
    assert item_payload["protein"] == "10.0000"
    assert item_payload["manually_corrected"] is True


def test_user_can_delete_own_meal(api_client: APIClient) -> None:
    user = make_user()
    meal = make_meal(user=user)
    api_client.force_authenticate(user=user)

    response = api_client.delete(_meal_detail_url(meal.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert Meal.objects.filter(id=meal.id).exists() is False


def test_diary_day_aggregates_totals_and_micronutrients(api_client: APIClient) -> None:
    user = make_user()
    food_item = _food_with_nutrients()
    meal = make_meal(
        user=user,
        meal_type=Meal.MealType.BREAKFAST,
        logged_at=datetime(2026, 8, 12, 9, tzinfo=UTC),
    )
    make_meal_item(meal=meal, food=food_item, mass_g=Decimal("100.00"))
    other_day_meal = make_meal(
        user=user,
        meal_type=Meal.MealType.DINNER,
        logged_at=datetime(2026, 8, 13, 18, tzinfo=UTC),
    )
    make_meal_item(meal=other_day_meal, food=food_item, mass_g=Decimal("100.00"))
    make_meal_item(food=food_item, mass_g=Decimal("100.00"))
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("diary-day"), {"date": "2026-08-12"})

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["date"] == "2026-08-12"
    assert payload["totals"]["calories"] == "52.0000"
    assert payload["totals"]["protein"] == "0.2600"
    assert payload["totals"]["fat"] == "0.1700"
    assert payload["totals"]["carbs"] == "13.8100"
    assert payload["micronutrient_totals"]["vitamin_c"]["amount"] == "4.6000"
    assert [meal_payload["id"] for meal_payload in payload["meals"]] == [str(meal.id)]


def test_diary_day_requires_valid_date(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    missing_response = api_client.get(reverse("diary-day"))
    invalid_response = api_client.get(reverse("diary-day"), {"date": "not-a-date"})

    assert missing_response.status_code == status.HTTP_400_BAD_REQUEST
    assert missing_response.json()["date"] == ["date_required"]
    assert invalid_response.status_code == status.HTTP_400_BAD_REQUEST
    assert invalid_response.json()["date"] == ["invalid_date"]
