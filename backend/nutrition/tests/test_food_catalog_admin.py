from __future__ import annotations

from typing import Any, cast

import pytest
from django.contrib import admin
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse

from accounts.models import User
from accounts.rbac import Role, assign_role
from accounts.tests.factories import make_user
from nutrition.models import FoodCategory, FoodDataSource, FoodItem, FoodNutrient, Nutrient

pytestmark = pytest.mark.django_db

NUTRITION_ADMIN_MODELS = {
    "nutrition.foodcategory",
    "nutrition.fooddatasource",
    "nutrition.nutrient",
    "nutrition.fooditem",
    "nutrition.foodnutrient",
}


def _staff_user_with_role(role: Role) -> User:
    user = make_user(is_staff=True)
    assign_role(user, role)
    return user


def _admin_request(user: User) -> HttpRequest:
    request = cast(HttpRequest, RequestFactory().get(reverse("admin:index")))
    request.user = user
    return request


def _visible_admin_model_labels(user: User) -> set[str]:
    app_list: list[dict[str, Any]] = admin.site.get_app_list(_admin_request(user))
    return {
        f"{app['app_label']}.{model['object_name'].lower()}"
        for app in app_list
        for model in app["models"]
    }


def test_content_manager_sees_nutrition_catalog_models_in_admin() -> None:
    content_manager = _staff_user_with_role(Role.CONTENT_MANAGER)

    visible_models = _visible_admin_model_labels(content_manager)

    assert NUTRITION_ADMIN_MODELS.issubset(visible_models)
    assert "accounts.user" not in visible_models
    assert "accounts.adminauditlog" not in visible_models


def test_support_does_not_see_nutrition_catalog_models_in_admin() -> None:
    support = _staff_user_with_role(Role.SUPPORT)

    visible_models = _visible_admin_model_labels(support)

    assert visible_models.isdisjoint(NUTRITION_ADMIN_MODELS)


def test_content_manager_can_open_nutrition_changelists(client: Client) -> None:
    content_manager = _staff_user_with_role(Role.CONTENT_MANAGER)
    client.force_login(content_manager)

    for url_name in (
        "admin:nutrition_foodcategory_changelist",
        "admin:nutrition_fooddatasource_changelist",
        "admin:nutrition_nutrient_changelist",
        "admin:nutrition_fooditem_changelist",
        "admin:nutrition_foodnutrient_changelist",
    ):
        response = client.get(reverse(url_name))

        assert response.status_code == 200, url_name


def test_nutrition_admin_models_have_safe_foundation_settings() -> None:
    for model in (FoodCategory, FoodDataSource, FoodItem, FoodNutrient, Nutrient):
        model_admin = admin.site._registry[model]

        assert model_admin.actions is None
        assert "id" in model_admin.readonly_fields
        assert "created_at" in model_admin.readonly_fields
        assert "updated_at" in model_admin.readonly_fields
        assert model_admin.search_fields
        assert model_admin.list_filter
