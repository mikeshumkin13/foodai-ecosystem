from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import NutritionProfile
from accounts.rbac import (
    CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION,
    USE_AI_COACH_PERMISSION,
    VIEW_OWN_AI_COACH_SETTINGS_PERMISSION,
    Role,
    assign_role,
)
from accounts.tests.factories import make_nutrition_profile, make_user, make_user_profile
from ai_coach.models import AICoachMessage
from ai_coach.providers import (
    AICoachNutritionNote,
    AICoachProviderRequest,
    AICoachProviderResponse,
)
from ai_coach.services import ask_nutrition_coach, get_ai_coach_settings
from diary.tests.factories import make_meal, make_meal_item
from nutrition.models import FoodItem, Nutrient
from nutrition.tests.factories import make_food_item, make_food_nutrient, make_nutrient

pytestmark = pytest.mark.django_db


class CapturingProvider:
    name = "capturing"

    def __init__(self, response: AICoachProviderResponse | None = None) -> None:
        self.requests: list[AICoachProviderRequest] = []
        self.response = response or AICoachProviderResponse(
            answer="General nutrition balance response.",
            suggestions=("Add a protein-rich food if needed.",),
            nutrition_notes=(
                AICoachNutritionNote(
                    code="protein",
                    message="Protein can be spread across meals.",
                ),
            ),
        )

    def generate(self, request: AICoachProviderRequest) -> AICoachProviderResponse:
        self.requests.append(request)
        return self.response


class FailingProvider:
    name = "failing"

    def generate(self, request: AICoachProviderRequest) -> AICoachProviderResponse:
        raise AssertionError("provider_must_not_be_called")


def _ask_url() -> str:
    return reverse("ai-coach-ask")


def _settings_url() -> str:
    return reverse("ai-coach-settings")


def _food_with_nutrients() -> FoodItem:
    food_item = make_food_item(name="Greek yogurt", source_reference="Demo values per 100 g")
    make_food_nutrient(
        food_item=food_item,
        nutrient=make_nutrient(
            code="energy_kcal",
            name="Energy",
            name_ru="Энергия",
            name_en="Energy",
            unit="kcal",
            nutrient_type=Nutrient.NutrientType.ENERGY,
        ),
        amount_per_100g=Decimal("60.0000"),
    )
    make_food_nutrient(
        food_item=food_item,
        nutrient=make_nutrient(
            code="protein",
            name="Protein",
            name_ru="Белки",
            name_en="Protein",
            unit="g",
            nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
        ),
        amount_per_100g=Decimal("10.0000"),
    )
    make_food_nutrient(
        food_item=food_item,
        nutrient=make_nutrient(
            code="fat",
            name="Fat",
            name_ru="Жиры",
            name_en="Fat",
            unit="g",
            nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
        ),
        amount_per_100g=Decimal("0.4000"),
    )
    make_food_nutrient(
        food_item=food_item,
        nutrient=make_nutrient(
            code="carbohydrate",
            name="Carbohydrate",
            name_ru="Углеводы",
            name_en="Carbohydrate",
            unit="g",
            nutrient_type=Nutrient.NutrientType.MACRONUTRIENT,
        ),
        amount_per_100g=Decimal("3.6000"),
    )
    return food_item


def test_user_role_has_ai_coach_permissions() -> None:
    user = make_user()

    assert user.has_perm(USE_AI_COACH_PERMISSION) is True
    assert user.has_perm(VIEW_OWN_AI_COACH_SETTINGS_PERMISSION) is True
    assert user.has_perm(CHANGE_OWN_AI_COACH_SETTINGS_PERMISSION) is True


def test_ai_coach_context_contains_only_allowed_user_context() -> None:
    user = make_user(email="private@example.com")
    make_user_profile(user=user, display_name="Private Name", preferred_language="en")
    make_nutrition_profile(
        user=user,
        goal=NutritionProfile.Goal.GAIN_WEIGHT,
        dietary_preferences=["vegetarian", "high_protein", "unknown"],
    )
    meal = make_meal(
        user=user,
        logged_at=datetime(2026, 8, 19, 9, 30, tzinfo=UTC),
    )
    make_meal_item(meal=meal, food=_food_with_nutrients(), mass_g=Decimal("200.00"))
    provider = CapturingProvider()

    result = ask_nutrition_coach(
        user=user,
        message="How can I add more protein today?",
        context_date=date(2026, 8, 19),
        provider=provider,
    )

    assert result.code == "ai_coach_response"
    assert len(provider.requests) == 1
    provider_payload = provider.requests[0].context.to_provider_payload()
    serialized_payload = json.dumps(provider_payload, ensure_ascii=False)
    assert provider_payload == {
        "schema_version": "ai_coach_context_v1",
        "locale": "en",
        "date": "2026-08-19",
        "goal": NutritionProfile.Goal.GAIN_WEIGHT,
        "diary_aggregates": {
            "totals": {
                "calories": "120.0000",
                "protein": "20.0000",
                "fat": "0.8000",
                "carbs": "7.2000",
            },
            "micronutrient_totals": {},
        },
        "dietary_preferences": ["vegetarian", "high_protein"],
        "user_request": "How can I add more protein today?",
    }
    assert user.email not in serialized_payload
    assert str(user.id) not in serialized_payload
    assert "Private Name" not in serialized_payload
    assert "display_name" not in serialized_payload
    assert "photo" not in serialized_payload
    assert "food_scan" not in serialized_payload
    assert "ai_coach_messages" not in serialized_payload


def test_ai_coach_ask_denies_anonymous_user(api_client: APIClient) -> None:
    response = api_client.post(_ask_url(), {"message": "Как добрать белок?"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_ai_coach_ask_denies_user_without_role(api_client: APIClient) -> None:
    user = make_user()
    user.groups.clear()
    api_client.force_authenticate(user=user)

    response = api_client.post(_ask_url(), {"message": "Как добрать белок?"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("role", [Role.SUPPORT, Role.CONTENT_MANAGER, Role.ADMIN])
def test_business_roles_cannot_use_ai_coach_by_default(
    role: Role,
    api_client: APIClient,
) -> None:
    actor = make_user()
    assign_role(actor, role)
    api_client.force_authenticate(user=actor)

    response = api_client.post(_ask_url(), {"message": "Как добрать белок?"}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_user_can_ask_ai_coach_and_response_is_not_stored_by_default(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _ask_url(),
        {"message": "Как объяснить баланс за день?", "date": "2026-08-19"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["code"] == "ai_coach_response"
    assert payload["schema_version"] == "ai_nutrition_coach_response_v1"
    assert payload["context_date"] == "2026-08-19"
    assert payload["stored"] is False
    assert payload["provider"] == "mock"
    assert payload["safety"] == {
        "blocked": False,
        "code": "passed",
        "categories": [],
        "reason": "",
    }
    assert "answer" in payload
    assert "suggestions" in payload
    assert "nutrition_notes" in payload
    assert AICoachMessage.objects.count() == 0


def test_store_response_request_without_consent_does_not_persist_message(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _ask_url(),
        {
            "message": "Подскажи варианты завтрака",
            "date": "2026-08-19",
            "store_response": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["stored"] is False
    assert AICoachMessage.objects.count() == 0


def test_user_can_grant_and_revoke_ai_chat_history_consent(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    initial_response = api_client.get(_settings_url())
    grant_response = api_client.patch(
        _settings_url(),
        {"chat_history_consent_accepted": True},
        format="json",
    )
    revoke_response = api_client.patch(
        _settings_url(),
        {"chat_history_consent_revoked": True},
        format="json",
    )

    assert initial_response.status_code == status.HTTP_200_OK
    assert initial_response.json()["chat_history_enabled"] is False
    assert "user_id" not in initial_response.json()
    assert grant_response.status_code == status.HTTP_200_OK
    assert grant_response.json()["chat_history_enabled"] is True
    assert grant_response.json()["chat_history_consent_version"] == "ai_coach_history_mvp_v1"
    assert revoke_response.status_code == status.HTTP_200_OK
    assert revoke_response.json()["chat_history_enabled"] is False


def test_ai_response_is_stored_only_after_history_consent(api_client: APIClient) -> None:
    user = make_user(email="consented@example.com")
    ai_settings = get_ai_coach_settings(user=user)
    ai_settings.grant_chat_history_consent()
    ai_settings.save()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        _ask_url(),
        {
            "message": "Помоги оценить белок за день",
            "date": "2026-08-19",
            "store_response": True,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["stored"] is True
    message = AICoachMessage.objects.get()
    serialized_context = json.dumps(message.context_snapshot, ensure_ascii=False)
    assert message.request_text == "Помоги оценить белок за день"
    assert message.response_payload["stored"] is True
    assert message.provider_name == "mock"
    assert message.safety_status == AICoachMessage.SafetyStatus.PASSED
    assert "consented@example.com" not in serialized_context
    assert str(user.id) not in serialized_context


def test_unsafe_user_request_is_blocked_before_provider_call() -> None:
    user = make_user()

    result = ask_nutrition_coach(
        user=user,
        message="Назначь лекарство и диету на 300 калорий",
        context_date=date(2026, 8, 19),
        store_response=True,
        provider=FailingProvider(),
    )

    assert result.code == "ai_coach_safety_blocked"
    assert result.safety.blocked is True
    assert set(result.safety.categories) == {"medical_decision", "extreme_diet"}
    assert result.provider_name == "safety_layer"
    assert result.stored is False
    assert AICoachMessage.objects.count() == 0


def test_unsafe_provider_output_is_blocked_and_not_stored() -> None:
    user = make_user()
    ai_settings = get_ai_coach_settings(user=user)
    ai_settings.grant_chat_history_consent()
    ai_settings.save()
    provider = CapturingProvider(
        response=AICoachProviderResponse(
            answer="Stop taking insulin and eat 300 kcal daily.",
            suggestions=(),
            nutrition_notes=(),
        )
    )

    result = ask_nutrition_coach(
        user=user,
        message="Give me nutrition feedback",
        context_date=date(2026, 8, 19),
        store_response=True,
        provider=provider,
    )

    assert len(provider.requests) == 1
    assert result.code == "ai_coach_safety_blocked"
    assert result.safety.blocked is True
    assert set(result.safety.categories) == {"medical_decision", "extreme_diet"}
    assert result.stored is False
    assert AICoachMessage.objects.count() == 0
