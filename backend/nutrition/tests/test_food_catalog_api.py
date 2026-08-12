from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.rbac import Role, assign_role
from accounts.tests.factories import make_superuser, make_user
from nutrition.models import FoodCategory, FoodDataSource, FoodItem, FoodNutrient, Nutrient
from nutrition.tests.factories import (
    make_food_category,
    make_food_data_source,
    make_food_item,
    make_food_nutrient,
    make_nutrient,
)

pytestmark = pytest.mark.django_db


def _food_detail_url(food_id: object) -> str:
    return reverse("food-detail", kwargs={"id": food_id})


def test_food_search_denies_anonymous_user(api_client: APIClient) -> None:
    response = api_client.get(reverse("food-search"))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_regular_user_can_search_foods_by_name_and_synonym(api_client: APIClient) -> None:
    user = make_user()
    apple = make_food_item(name="Apple, raw", synonyms=["яблоко", "green apple"])
    make_food_item(
        category=make_food_category(slug="protein-foods", name="Protein foods"),
        data_source=make_food_data_source(code="demo-source-2"),
        name="Chicken breast, cooked",
        name_ru="Куриная грудка приготовленная",
        name_en="Chicken breast, cooked",
        synonyms=["куриная грудка"],
    )
    api_client.force_authenticate(user=user)

    name_response = api_client.get(reverse("food-search"), {"q": "apple"})
    synonym_response = api_client.get(reverse("food-search"), {"q": "яблоко"})

    assert name_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in name_response.json()] == [str(apple.id)]
    assert synonym_response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in synonym_response.json()] == [str(apple.id)]


def test_food_detail_returns_extensible_nutrients_per_100g(api_client: APIClient) -> None:
    user = make_user()
    food_item = make_food_item()
    make_food_nutrient(food_item=food_item)
    vitamin_c = make_nutrient(
        code="vitamin_c",
        name="Vitamin C",
        name_ru="Витамин C",
        name_en="Vitamin C",
        unit="mg",
        nutrient_type=Nutrient.NutrientType.MICRONUTRIENT,
    )
    FoodNutrient.objects.create(
        food_item=food_item,
        nutrient=vitamin_c,
        amount_per_100g=Decimal("4.6000"),
        source_reference="Demo micronutrient value",
    )
    api_client.force_authenticate(user=user)

    response = api_client.get(_food_detail_url(food_item.id))

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    nutrients = {item["nutrient"]["code"]: item for item in payload["nutrients"]}
    assert payload["id"] == str(food_item.id)
    assert payload["category"]["slug"] == food_item.category.slug
    assert payload["data_source"]["code"] == food_item.data_source.code
    assert nutrients["energy_kcal"]["amount_per_100g"] == "52.0000"
    assert nutrients["energy_kcal"]["unit"] == "kcal"
    assert nutrients["vitamin_c"]["amount_per_100g"] == "4.6000"
    assert nutrients["vitamin_c"]["unit"] == "mg"
    assert (
        nutrients["vitamin_c"]["nutrient"]["nutrient_type"] == Nutrient.NutrientType.MICRONUTRIENT
    )


def test_regular_user_cannot_create_or_update_food_catalog(api_client: APIClient) -> None:
    user = make_user()
    category = make_food_category()
    data_source = make_food_data_source()
    food_item = make_food_item(category=category, data_source=data_source)
    api_client.force_authenticate(user=user)

    create_response = api_client.post(
        reverse("food-list"),
        {
            "name": "Pear, raw",
            "category_id": str(category.id),
            "data_source_id": str(data_source.id),
            "synonyms": ["pear"],
        },
        format="json",
    )
    update_response = api_client.patch(
        _food_detail_url(food_item.id),
        {"name": "Updated"},
        format="json",
    )

    assert create_response.status_code == status.HTTP_403_FORBIDDEN
    assert update_response.status_code == status.HTTP_403_FORBIDDEN


def test_content_manager_can_create_and_update_food_item(api_client: APIClient) -> None:
    actor = make_user()
    assign_role(actor, Role.CONTENT_MANAGER)
    category = make_food_category()
    data_source = make_food_data_source()
    api_client.force_authenticate(user=actor)

    create_response = api_client.post(
        reverse("food-list"),
        {
            "name": "Pear, raw",
            "name_ru": "Груша сырая",
            "name_en": "Pear, raw",
            "synonyms": [" pear ", "груша", "pear"],
            "category_id": str(category.id),
            "data_source_id": str(data_source.id),
            "density_metadata": {"basis": "demo"},
            "is_verified": False,
            "source_reference": "Demo value",
        },
        format="json",
    )

    assert create_response.status_code == status.HTTP_201_CREATED
    created_payload = create_response.json()
    assert created_payload["name"] == "Pear, raw"
    assert created_payload["synonyms"] == ["pear", "груша"]

    update_response = api_client.patch(
        _food_detail_url(created_payload["id"]),
        {"is_verified": True, "source_reference": "Reviewed demo value"},
        format="json",
    )

    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["is_verified"] is True
    food_item = FoodItem.objects.get(id=created_payload["id"])
    assert food_item.is_verified is True
    assert food_item.source_reference == "Reviewed demo value"


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.ADMIN])
def test_non_catalog_roles_cannot_modify_food_catalog(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    category = make_food_category()
    data_source = make_food_data_source()
    api_client.force_authenticate(user=actor)

    response = api_client.post(
        reverse("food-list"),
        {
            "name": "Pear, raw",
            "category_id": str(category.id),
            "data_source_id": str(data_source.id),
        },
        format="json",
    )

    if role == Role.ADMIN:
        assert response.status_code == status.HTTP_201_CREATED
    else:
        assert response.status_code == status.HTTP_403_FORBIDDEN


def test_support_can_read_but_cannot_modify_food_catalog(api_client: APIClient) -> None:
    actor = make_user()
    assign_role(actor, Role.SUPPORT)
    food_item = make_food_item()
    api_client.force_authenticate(user=actor)

    detail_response = api_client.get(_food_detail_url(food_item.id))
    update_response = api_client.patch(
        _food_detail_url(food_item.id),
        {"name": "Updated"},
        format="json",
    )

    assert detail_response.status_code == status.HTTP_200_OK
    assert update_response.status_code == status.HTTP_403_FORBIDDEN


def test_superuser_can_modify_food_catalog_as_technical_override(api_client: APIClient) -> None:
    superuser = make_superuser()
    category = make_food_category()
    data_source = make_food_data_source()
    api_client.force_authenticate(user=superuser)

    response = api_client.post(
        reverse("food-list"),
        {
            "name": "Pear, raw",
            "category_id": str(category.id),
            "data_source_id": str(data_source.id),
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_food_item_cannot_reference_itself_as_canonical_food(api_client: APIClient) -> None:
    actor = make_user()
    assign_role(actor, Role.CONTENT_MANAGER)
    food_item = make_food_item()
    api_client.force_authenticate(user=actor)

    response = api_client.patch(
        _food_detail_url(food_item.id),
        {"canonical_food_id": str(food_item.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["canonical_food_id"] == ["canonical_food_cannot_reference_self"]


def test_demo_nutrition_catalog_fixture_loads() -> None:
    call_command("loaddata", "demo_nutrition_catalog", verbosity=0)

    assert FoodCategory.objects.filter(slug="fruits").exists()
    assert FoodDataSource.objects.filter(code="foodai-demo").exists()
    assert Nutrient.objects.filter(code="vitamin_c", nutrient_type="micronutrient").exists()
    apple = FoodItem.objects.get(name="Apple, raw")
    nutrient_codes = set(apple.nutrient_values.values_list("nutrient__code", flat=True))
    assert {"energy_kcal", "protein", "fat", "carbohydrate", "fiber", "vitamin_c"}.issubset(
        nutrient_codes,
    )
